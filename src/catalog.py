"""
Product catalog storage and retrieval.

Two retrievers over the same catalog, fused:

  BM25 (lexical) catches exact identifiers - "RTX 4080", "M3 Pro", "XPS 13".
  Dense vectors miss these routinely, because an embedding of "4080" sits
  close to "4070" and "4090" in a space that was trained to capture meaning,
  not part numbers.

  Dense (semantic) catches intent with no shared vocabulary - "something for
  video editing" should reach a workstation laptop whose description never
  uses the word "editing".

Neither alone is enough for a shopping assistant, so results are combined with
reciprocal rank fusion. The weighting is configurable, and the retriever can be
run in dense-only or bm25-only mode, so Stage 3 can report the three side by
side rather than asserting that hybrid is better.

The embedder is pluggable. Swapping all-MiniLM-L6-v2 for a multilingual model
is a constructor argument, which is what the cross-lingual benchmark needs.

Vector search is exact brute force over a (n_products x dim) matrix. At 200
SKUs that is microseconds and involves no index to build or keep in sync; a
vector store such as sqlite-vec or Chroma is the swap once the catalog is large
enough for an approximate index to pay for itself.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)

DEFAULT_CATALOG_PATH = os.path.join("data", "catalog", "products.jsonl")
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

CATALOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    sku         TEXT PRIMARY KEY,
    name        TEXT    NOT NULL,
    brand       TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    price_usd   REAL    NOT NULL,
    stock       INTEGER NOT NULL DEFAULT 0,
    specs       TEXT    NOT NULL DEFAULT '{}',
    description TEXT    NOT NULL DEFAULT '',
    search_text TEXT    NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);

CREATE TABLE IF NOT EXISTS product_embeddings (
    sku        TEXT NOT NULL,
    model      TEXT NOT NULL,
    dim        INTEGER NOT NULL,
    vector     BLOB NOT NULL,
    -- Hash of the text that produced this vector, so a re-run can tell a
    -- stale embedding from an up-to-date one and re-embed only what changed.
    text_hash  TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (sku, model),
    FOREIGN KEY (sku) REFERENCES products(sku) ON DELETE CASCADE
);
"""


# ---------------------------------------------------------------------------
# text handling
# ---------------------------------------------------------------------------

def flatten_specs(specs: Dict[str, Any]) -> str:
    """"cpu: Intel Core i9, ram: 32GB DDR5, ..." for indexing."""
    if not specs:
        return ""
    return ", ".join(f"{key}: {value}" for key, value in specs.items())


def text_hash(text: str) -> str:
    """Stable fingerprint of indexed text, for detecting stale embeddings."""
    import hashlib
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def build_search_text(product: Dict[str, Any]) -> str:
    """The text that gets embedded and BM25-indexed."""
    return " | ".join(filter(None, [
        product.get("name", ""),
        product.get("brand", ""),
        product.get("category", ""),
        product.get("description", ""),
        flatten_specs(product.get("specs") or {}),
    ]))


# Keeps alphanumeric runs together, so "RTX 4080" -> ["rtx", "4080"] and
# "i9-14900HX" -> ["i9", "14900hx"]. Model numbers survive as their own tokens,
# which is the whole reason BM25 is here.
_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    return _TOKEN.findall((text or "").lower())


# ---------------------------------------------------------------------------
# query routing
# ---------------------------------------------------------------------------

# Signals that a query names a *thing* rather than describing a need. These are
# what BM25 is good at and dense vectors are bad at: an embedding of "4080"
# sits next to "4070" and "4090", but the token "4080" is exact.
_LEXICAL_PATTERNS = [
    re.compile(r"\b[a-z]{0,4}\d{3,5}\b"),            # 4080, 14900, 840, x1
    re.compile(r"\b(rtx|gtx|ryzen|snapdragon|tensor|dimensity|exynos)\b"),
    re.compile(r"\bi[3579]\b"),                       # i5, i7, i9
    re.compile(r"\bm[1-4]\s?(pro|max|ultra)?\b"),     # m3, m3 pro
    re.compile(r"\b\d+\s?(gb|tb|mb)\b"),              # 16GB, 1TB
    re.compile(r"\b\d+\s?(hz|mah|wh)\b"),             # 120Hz, 5000mAh
    re.compile(r"\b[a-z]{3}-[a-z]{3}-\d{4}\b"),       # SKU
    re.compile(r"\b\d+(\.\d+)?\s?(inch|\")"),         # 14 inch, 13.6"
]


class QueryRouter:
    """Decides whether a query is lexical, semantic, or a mix of both.

    The motivation is a measured failure of fixed-weight fusion. On "I need to
    carry my laptop on my commute", BM25 has no useful opinion - it matches the
    token "laptop" in product descriptions and returns an SSD - yet under equal
    weights its opinion still decides the outcome, because reciprocal rank
    fusion rewards cross-retriever consensus. Consensus is evidence when both
    retrievers have signal and noise when one of them has none.

    So: weight the retrievers by what the query looks like, rather than
    assuming parity. Brand and product-line vocabulary is taken from the
    catalog itself rather than hardcoded, so the router stays correct as the
    catalog changes.

    This is a hypothesis to be measured against fixed-weight hybrid, not an
    improvement to be assumed.
    """

    def __init__(self, vocabulary: Optional[Iterable[str]] = None):
        # Brand names and distinctive line tokens ("thinkpad", "zephyrus").
        self.vocabulary = {v.lower() for v in (vocabulary or [])}

    @classmethod
    def from_store(cls, store: "ProductStore") -> "QueryRouter":
        """Brand and product-line tokens, with generic category words removed.

        "Laptop" appears in the name "Targus CityGear Laptop Sleeve" and
        "Phone" in "Nothing Phone (2a)", but a customer writing "carry my
        laptop" is describing a need, not naming a product. Category names and
        accessory type values come from the catalog itself, so this stays
        correct as the catalog changes instead of relying on a fixed stoplist.
        """
        products = store.all()

        generic = set()
        for product in products:
            for token in tokenize(product.category):
                generic.add(token)
                generic.add(token.rstrip("s"))
            for token in tokenize(str(product.specs.get("type", ""))):
                generic.add(token)
                generic.add(token.rstrip("s"))

        vocabulary = set()
        for product in products:
            vocabulary.add(product.brand.lower())
            for token in tokenize(product.name):
                # Short and purely numeric tokens are covered by the regex
                # signals; generic category words are not identifiers.
                if len(token) > 3 and not token.isdigit() and token not in generic:
                    vocabulary.add(token)

        return cls(vocabulary - generic)

    def signals(self, query: str) -> Dict[str, Any]:
        text = (query or "").lower()
        pattern_hits = [p.pattern for p in _LEXICAL_PATTERNS if p.search(text)]
        # Match plurals too: "do you have thinkpads" names a product line.
        vocabulary_hits = [
            t for t in tokenize(text)
            if t in self.vocabulary or t.rstrip("s") in self.vocabulary
        ]
        return {"patterns": pattern_hits, "vocabulary": vocabulary_hits}

    def classify(self, query: str) -> str:
        """Return "lexical", "semantic" or "mixed"."""
        found = self.signals(query)
        identifier_like = len(found["patterns"])
        names = len(found["vocabulary"])

        if not identifier_like and not names:
            return "semantic"

        # A short query that is essentially just an identifier is lexical.
        # A longer one that is mostly prose but mentions a brand ("a cheap
        # Samsung phone for my mum") still needs the dense retriever to carry
        # the intent, so it is mixed.
        word_count = len(tokenize(query))
        if identifier_like + names >= 1 and word_count <= 6:
            return "lexical"
        if identifier_like >= 2:
            return "lexical"
        return "mixed"

    def weights(self, query: str) -> tuple:
        """(dense_weight, bm25_weight) for this query."""
        return {
            "lexical": (0.3, 1.0),
            "mixed": (1.0, 1.0),
            "semantic": (1.0, 0.3),
        }[self.classify(query)]


# ---------------------------------------------------------------------------
# embedding
# ---------------------------------------------------------------------------

class SentenceTransformerEmbedder:
    """Wraps a sentence-transformers model.

    Imported lazily: the catalog, BM25 retrieval and the agent tools all work
    without torch installed, which keeps the test suite and CI light.
    """

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL,
                 device: Optional[str] = None):
        self.model_name = model_name
        self._device = device
        self._model = None

    @property
    def name(self) -> str:
        return self.model_name

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model %s", self.model_name)
            self._model = SentenceTransformer(self.model_name, device=self._device)
        return self._model

    def encode(self, texts: Sequence[str]):
        import numpy as np
        vectors = self.model.encode(
            list(texts), convert_to_numpy=True, normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype="float32")


# ---------------------------------------------------------------------------
# storage
# ---------------------------------------------------------------------------

@dataclass
class Product:
    sku: str
    name: str
    brand: str
    category: str
    price_usd: float
    stock: int
    specs: Dict[str, Any]
    description: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Product":
        try:
            specs = json.loads(row["specs"]) or {}
        except (json.JSONDecodeError, TypeError):
            specs = {}
        return cls(
            sku=row["sku"], name=row["name"], brand=row["brand"],
            category=row["category"], price_usd=row["price_usd"],
            stock=row["stock"], specs=specs, description=row["description"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sku": self.sku, "name": self.name, "brand": self.brand,
            "category": self.category, "price_usd": self.price_usd,
            "stock": self.stock, "specs": self.specs,
            "description": self.description,
            "in_stock": self.stock > 0,
        }


def read_catalog_file(path: str = DEFAULT_CATALOG_PATH) -> List[Dict[str, Any]]:
    products = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                products.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number} is not valid JSON") from exc
    return products


def init_catalog_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(CATALOG_SCHEMA)
    conn.commit()


def load_catalog(conn: sqlite3.Connection,
                 path: str = DEFAULT_CATALOG_PATH) -> int:
    """Load the JSONL catalog into SQLite. Idempotent: rows are replaced."""
    init_catalog_schema(conn)
    products = read_catalog_file(path)

    with conn:
        for product in products:
            conn.execute(
                "INSERT OR REPLACE INTO products "
                "(sku, name, brand, category, price_usd, stock, specs, "
                " description, search_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    product["sku"], product["name"], product["brand"],
                    product["category"], float(product["price_usd"]),
                    int(product.get("stock", 0)),
                    json.dumps(product.get("specs") or {}, ensure_ascii=False),
                    product.get("description", ""),
                    build_search_text(product),
                ),
            )
    return len(products)


class ProductStore:
    """Read access to the catalog tables."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    def get(self, sku: str) -> Optional[Product]:
        row = self.conn.execute(
            "SELECT * FROM products WHERE sku = ?", (sku.strip().upper(),)
        ).fetchone()
        return Product.from_row(row) if row else None

    def all(self) -> List[Product]:
        rows = self.conn.execute("SELECT * FROM products ORDER BY sku").fetchall()
        return [Product.from_row(row) for row in rows]

    def search_texts(self) -> List[tuple]:
        rows = self.conn.execute(
            "SELECT sku, search_text FROM products ORDER BY sku"
        ).fetchall()
        return [(row["sku"], row["search_text"]) for row in rows]

    # -- embeddings --------------------------------------------------------
    def store_embeddings(self, model: str, skus: Sequence[str], vectors,
                         text_hashes: Optional[Sequence[str]] = None) -> None:
        hashes = list(text_hashes) if text_hashes is not None else [""] * len(skus)
        with self.conn:
            for sku, vector, text_hash in zip(skus, vectors, hashes):
                self.conn.execute(
                    "INSERT OR REPLACE INTO product_embeddings "
                    "(sku, model, dim, vector, text_hash) VALUES (?, ?, ?, ?, ?)",
                    (sku, model, len(vector), vector.astype("float32").tobytes(),
                     text_hash),
                )

    def stored_text_hashes(self, model: str) -> Dict[str, str]:
        rows = self.conn.execute(
            "SELECT sku, text_hash FROM product_embeddings WHERE model = ?",
            (model,)
        ).fetchall()
        return {row["sku"]: row["text_hash"] for row in rows}

    def delete_embeddings(self, model: str, skus: Optional[Sequence[str]] = None) -> int:
        with self.conn:
            if skus is None:
                cur = self.conn.execute(
                    "DELETE FROM product_embeddings WHERE model = ?", (model,))
            else:
                cur = self.conn.executemany(
                    "DELETE FROM product_embeddings WHERE model = ? AND sku = ?",
                    [(model, sku) for sku in skus])
        return cur.rowcount or 0

    def load_embeddings(self, model: str):
        import numpy as np
        rows = self.conn.execute(
            "SELECT sku, dim, vector FROM product_embeddings "
            "WHERE model = ? ORDER BY sku", (model,)
        ).fetchall()
        if not rows:
            return [], None
        skus = [row["sku"] for row in rows]
        matrix = np.vstack([
            np.frombuffer(row["vector"], dtype="float32").reshape(row["dim"])
            for row in rows
        ])
        return skus, matrix

    def embedding_models(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT model FROM product_embeddings ORDER BY model"
        ).fetchall()
        return [row["model"] for row in rows]


# ---------------------------------------------------------------------------
# retrieval
# ---------------------------------------------------------------------------

@dataclass
class Hit:
    sku: str
    score: float
    dense_rank: Optional[int] = None
    bm25_rank: Optional[int] = None


class BM25Index:
    """BM25 over the catalog search text.

    Implemented here rather than via rank_bm25 so that retrieval needs nothing
    beyond the standard library: the agent tools and their tests must work in
    environments where the ML stack is not installed.

    IDF uses the Lucene variant, log(1 + (N - df + 0.5) / (df + 0.5)), which is
    always positive. rank_bm25's BM25Okapi uses the raw Okapi form without the
    +1, which goes negative for terms appearing in most documents and then
    floors them to epsilon * average_idf. That matters here: "ram" appears in
    almost every product's flattened specs, so under raw Okapi it would carry a
    floored, essentially arbitrary weight. The two implementations therefore
    rank differently on queries containing very common terms, and identically
    on discriminative ones; the tests assert both of those facts.
    """

    def __init__(self, documents: Dict[str, str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.skus = list(documents)
        self.doc_tokens = {sku: tokenize(text) for sku, text in documents.items()}
        self.doc_len = {sku: len(tokens) for sku, tokens in self.doc_tokens.items()}
        self.avg_len = (sum(self.doc_len.values()) / len(self.doc_len)) if self.doc_len else 0.0

        self.term_freq: Dict[str, Dict[str, int]] = {}
        doc_freq: Dict[str, int] = {}
        for sku, tokens in self.doc_tokens.items():
            counts: Dict[str, int] = {}
            for token in tokens:
                counts[token] = counts.get(token, 0) + 1
            self.term_freq[sku] = counts
            for token in counts:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        n = len(self.skus)
        self.idf = {
            term: math.log(1 + (n - df + 0.5) / (df + 0.5))
            for term, df in doc_freq.items()
        }

    def search(self, query: str, k: int = 10) -> List[Hit]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores: Dict[str, float] = {}
        for sku in self.skus:
            counts = self.term_freq[sku]
            length = self.doc_len[sku]
            score = 0.0
            for token in query_tokens:
                freq = counts.get(token)
                if not freq:
                    continue
                denom = freq + self.k1 * (
                    1 - self.b + self.b * (length / self.avg_len if self.avg_len else 1)
                )
                score += self.idf.get(token, 0.0) * (freq * (self.k1 + 1)) / denom
            if score > 0:
                scores[sku] = score

        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return [Hit(sku=sku, score=score) for sku, score in ranked[:k]]


class HybridRetriever:
    """BM25 + dense vectors combined with reciprocal rank fusion.

    RRF is used rather than a weighted sum of raw scores because BM25 scores
    and cosine similarities are not on a comparable scale, and normalising them
    per query makes the fusion sensitive to how many results each retriever
    happened to return. RRF only needs the ranks.

        score(d) = sum_r  weight_r / (rrf_k + rank_r(d))

    `mode` selects "hybrid", "dense" or "bm25" so the three can be measured
    against each other.
    """

    def __init__(self, store: ProductStore, embedder=None,
                 dense_weight: float = 1.0, bm25_weight: float = 1.0,
                 rrf_k: int = 60, mode: str = "hybrid",
                 retrieve_k: Optional[int] = None,
                 router: Optional["QueryRouter"] = None):
        self.store = store
        self.embedder = embedder
        self.dense_weight = dense_weight
        self.bm25_weight = bm25_weight
        self.rrf_k = rrf_k
        self.mode = mode
        # Depth of each retriever's candidate pool before fusion. A shallow
        # pool penalises a document that one retriever ranks highly but the
        # other never returns, because absence from the pool costs it an entire
        # RRF contribution. Exposed so the eval can sweep it rather than
        # inherit a hardcoded guess.
        self.retrieve_k = retrieve_k
        self.router = router

        self.bm25 = BM25Index(dict(store.search_texts()))

        self._dense_skus: List[str] = []
        self._dense_matrix = None
        if embedder is not None:
            self._dense_skus, self._dense_matrix = store.load_embeddings(embedder.name)
            if self._dense_matrix is None:
                logger.warning(
                    "No embeddings stored for %s - run scripts/build_index.py. "
                    "Falling back to lexical retrieval only.", embedder.name
                )

    @property
    def has_dense(self) -> bool:
        return self._dense_matrix is not None and len(self._dense_skus) > 0

    def dense_search(self, query: str, k: int = 10) -> List[Hit]:
        if not self.has_dense:
            return []
        import numpy as np
        vector = self.embedder.encode([query])[0]
        # Vectors are L2-normalised at encode time, so a dot product is cosine.
        similarities = self._dense_matrix @ vector
        top = np.argsort(-similarities)[:k]
        return [Hit(sku=self._dense_skus[i], score=float(similarities[i])) for i in top]

    def search(self, query: str, k: int = 5,
               retrieve_k: Optional[int] = None) -> List[Hit]:
        # Fuse over a deeper candidate pool than we return, so a document
        # ranked 8th by one retriever can still reach the final top 5.
        pool = retrieve_k or self.retrieve_k or max(k * 4, 20)

        fuses = self.mode in ("hybrid", "routed")
        bm25_hits = self.bm25.search(query, pool) if fuses or self.mode == "bm25" else []
        dense_hits = self.dense_search(query, pool) if fuses or self.mode == "dense" else []

        if self.mode == "bm25":
            return bm25_hits[:k]
        if self.mode == "dense":
            return dense_hits[:k]

        dense_weight, bm25_weight = self.dense_weight, self.bm25_weight
        if self.mode == "routed":
            if self.router is None:
                raise ValueError("routed mode needs a QueryRouter")
            dense_weight, bm25_weight = self.router.weights(query)

        fused: Dict[str, float] = {}
        dense_rank: Dict[str, int] = {}
        bm25_rank: Dict[str, int] = {}

        for rank, hit in enumerate(dense_hits, start=1):
            dense_rank[hit.sku] = rank
            fused[hit.sku] = fused.get(hit.sku, 0.0) + dense_weight / (self.rrf_k + rank)
        for rank, hit in enumerate(bm25_hits, start=1):
            bm25_rank[hit.sku] = rank
            fused[hit.sku] = fused.get(hit.sku, 0.0) + bm25_weight / (self.rrf_k + rank)

        # When the two candidate pools are disjoint every document scores
        # exactly 1/(rrf_k + rank), so ties decide the whole ordering. Break
        # them on evidence rather than on SKU spelling: prefer documents both
        # retrievers found, then the better single rank. SKU is the last
        # resort, purely so results are deterministic.
        def sort_key(item):
            sku, score = item
            ranks = [r for r in (dense_rank.get(sku), bm25_rank.get(sku)) if r]
            return (-score, -len(ranks), min(ranks) if ranks else 10**6, sku)

        ranked = sorted(fused.items(), key=sort_key)
        return [
            Hit(sku=sku, score=score,
                dense_rank=dense_rank.get(sku), bm25_rank=bm25_rank.get(sku))
            for sku, score in ranked[:k]
        ]


def open_catalog(db_path: str) -> sqlite3.Connection:
    directory = os.path.dirname(db_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
