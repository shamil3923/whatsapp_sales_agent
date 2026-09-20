"""
Catalog retrieval exposed to the agent as tools.

These three tools are the agent's only source of product facts. The system
prompt no longer contains any product data, so anything the agent says about a
name, spec, price or stock level has to have come through here. That is what
makes the Stage 3 grounding eval meaningful: a claim that does not appear in a
tool result is, by construction, invented.

Every tool returns JSON rather than prose. Prose invites the model to
paraphrase numbers; JSON keeps prices and stock counts exact and gives the
grounding checker something it can match against catalog rows mechanically.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Dict, List, Optional

from phi.tools import Toolkit

from catalog import (
    DEFAULT_EMBEDDING_MODEL, HybridRetriever, ProductStore,
    SentenceTransformerEmbedder, open_catalog,
)

logger = logging.getLogger(__name__)

# Trimmed to what a sales answer actually needs. The full description is long
# and pushes the useful fields out of the model's attention.
MAX_DESCRIPTION_CHARS = 220


def _row(product, include_description: bool = True) -> Dict[str, Any]:
    data = {
        "sku": product.sku,
        "name": product.name,
        "brand": product.brand,
        "category": product.category,
        "price_usd": round(product.price_usd, 2),
        "stock": product.stock,
        "in_stock": product.stock > 0,
        "specs": product.specs,
    }
    if include_description:
        description = product.description or ""
        if len(description) > MAX_DESCRIPTION_CHARS:
            description = description[:MAX_DESCRIPTION_CHARS].rsplit(" ", 1)[0] + "..."
        data["description"] = description
    return data


def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=None)


class ProductCatalog(Toolkit):
    """Search and look up products in the catalog."""

    def __init__(self, db_path: Optional[str] = None,
                 embedding_model: Optional[str] = None,
                 mode: Optional[str] = None,
                 dense_weight: float = 1.0, bm25_weight: float = 1.0):
        super().__init__(name="product_catalog")

        self.db_path = db_path or os.getenv("AGENT_DB_PATH",
                                            os.path.join("data", "agent.db"))
        self.embedding_model = embedding_model or os.getenv(
            "EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        # Default to hybrid, but fall back to lexical-only when no embeddings
        # have been built, so the agent still works on a fresh checkout.
        self.mode = mode or os.getenv("RETRIEVAL_MODE", "hybrid")
        self.dense_weight = float(os.getenv("RETRIEVAL_DENSE_WEIGHT", dense_weight))
        self.bm25_weight = float(os.getenv("RETRIEVAL_BM25_WEIGHT", bm25_weight))

        # SQLite connections are not shareable across threads, and the webhook
        # serves turns from a pool.
        self._local = threading.local()

        self.register(self.search_products)
        self.register(self.get_product)
        self.register(self.check_stock)

    # ------------------------------------------------------------------
    def _retriever(self) -> Optional[HybridRetriever]:
        retriever = getattr(self._local, "retriever", None)
        if retriever is not None:
            return retriever

        try:
            conn = open_catalog(self.db_path)
            store = ProductStore(conn)
            if store.count() == 0:
                logger.error(
                    "Catalog is empty at %s - run scripts/build_index.py", self.db_path)
                return None

            embedder = None
            if self.mode in ("hybrid", "dense"):
                candidate = SentenceTransformerEmbedder(self.embedding_model)
                # Only attach the embedder if vectors actually exist; otherwise
                # HybridRetriever would try to load a model for nothing.
                if store.load_embeddings(self.embedding_model)[1] is not None:
                    embedder = candidate

            mode = self.mode
            if embedder is None and mode in ("hybrid", "dense"):
                logger.warning(
                    "No embeddings for %s - serving lexical results only. "
                    "Run scripts/build_index.py for semantic search.",
                    self.embedding_model)
                mode = "bm25"

            retriever = HybridRetriever(
                store, embedder=embedder, mode=mode,
                dense_weight=self.dense_weight, bm25_weight=self.bm25_weight)
            self._local.retriever = retriever
            self._local.store = store
            return retriever
        except Exception as exc:
            logger.error("Could not open catalog at %s: %s", self.db_path, exc)
            return None

    def _store(self) -> Optional[ProductStore]:
        if self._retriever() is None:
            return None
        return getattr(self._local, "store", None)

    # ------------------------------------------------------------------
    # tools
    # ------------------------------------------------------------------
    def search_products(self, query: str, k: int = 5) -> str:
        """
        Search the product catalog for items matching a shopping query.

        Use this for any question about what is available, including vague ones
        ("something for video editing"), spec-constrained ones ("16GB RAM under
        $1200") and model lookups ("ThinkPad X1 Carbon").

        Args:
            query: What the customer is looking for, in their own words.
            k: How many products to return (default 5, maximum 20).

        Returns:
            JSON with a "results" list of matching products, each carrying sku,
            name, brand, category, price_usd, stock and specs. An empty list
            means nothing in the catalog matches, and you must tell the
            customer the item is not stocked rather than suggesting something
            you have not retrieved.
        """
        retriever = self._retriever()
        if retriever is None:
            return _dump({"error": "Catalog unavailable", "results": []})

        try:
            k = max(1, min(int(k), 20))
        except (TypeError, ValueError):
            k = 5

        store = self._store()
        hits = retriever.search(query or "", k=k)
        results = []
        for hit in hits:
            product = store.get(hit.sku)
            if product:
                results.append(_row(product))

        return _dump({
            "query": query,
            "retrieval_mode": retriever.mode,
            "count": len(results),
            "results": results,
        })

    def get_product(self, sku: str) -> str:
        """
        Get the full record for one product by its SKU.

        Use this after search_products when the customer asks for detail on a
        specific item, so that specs and price come from the catalog rather
        than from memory.

        Args:
            sku: The product's SKU, for example "LAP-DEL-9564".

        Returns:
            JSON with the product's name, brand, category, price_usd, stock,
            full specs and description, or {"found": false} if the SKU is not
            in the catalog.
        """
        store = self._store()
        if store is None:
            return _dump({"error": "Catalog unavailable", "found": False})

        product = store.get(sku or "")
        if not product:
            return _dump({"found": False, "sku": sku,
                          "message": "No product with that SKU is in the catalog."})

        payload = _row(product)
        payload["found"] = True
        payload["description"] = product.description  # full text for detail views
        return _dump(payload)

    def check_stock(self, sku: str) -> str:
        """
        Check how many units of one product are in stock.

        Args:
            sku: The product's SKU, for example "LAP-DEL-9564".

        Returns:
            JSON with stock count and availability. Never promise availability
            for a SKU this reports as out of stock.
        """
        store = self._store()
        if store is None:
            return _dump({"error": "Catalog unavailable", "found": False})

        product = store.get(sku or "")
        if not product:
            return _dump({"found": False, "sku": sku,
                          "message": "No product with that SKU is in the catalog."})

        if product.stock == 0:
            availability = "out_of_stock"
        elif product.stock < 5:
            availability = "low_stock"
        else:
            availability = "in_stock"

        return _dump({
            "found": True,
            "sku": product.sku,
            "name": product.name,
            "stock": product.stock,
            "availability": availability,
            "in_stock": product.stock > 0,
        })
