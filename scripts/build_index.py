#!/usr/bin/env python3
"""
Load the product catalog into SQLite and build its vector index.

Idempotent and re-runnable. Each stored embedding carries a hash of the text
it was built from, so a re-run embeds only SKUs that are new or whose text has
changed, and re-running with no changes does no model work at all. Embeddings
for SKUs that have left the catalog are removed.

    python scripts/build_index.py
    python scripts/build_index.py --model sentence-transformers/LaBSE
    python scripts/build_index.py --force          # re-embed everything
    python scripts/build_index.py --skip-embeddings  # catalog rows only

Several models can be indexed side by side: embeddings are keyed on
(sku, model), so the cross-lingual benchmark can build one index per model and
compare them against the same catalog rows.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from catalog import (  # noqa: E402
    DEFAULT_CATALOG_PATH, DEFAULT_EMBEDDING_MODEL, ProductStore,
    SentenceTransformerEmbedder, load_catalog, open_catalog, text_hash,
)
from conversation_memory import DEFAULT_DB_PATH  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=os.getenv("AGENT_DB_PATH", DEFAULT_DB_PATH))
    parser.add_argument("--catalog", default=DEFAULT_CATALOG_PATH)
    parser.add_argument("--model", default=os.getenv("EMBEDDING_MODEL",
                                                     DEFAULT_EMBEDDING_MODEL))
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--force", action="store_true",
                        help="re-embed every SKU even if unchanged")
    parser.add_argument("--skip-embeddings", action="store_true",
                        help="load catalog rows without building vectors")
    args = parser.parse_args()

    conn = open_catalog(args.db)
    try:
        count = load_catalog(conn, args.catalog)
        store = ProductStore(conn)
        print(f"Catalog: {count} SKUs loaded into {args.db}")

        if args.skip_embeddings:
            print("Skipping embeddings (--skip-embeddings).")
            return 0

        texts = dict(store.search_texts())
        current = {sku: text_hash(text) for sku, text in texts.items()}
        stored = {} if args.force else store.stored_text_hashes(args.model)

        stale = [sku for sku, h in current.items() if stored.get(sku) != h]
        removed = [sku for sku in stored if sku not in current]

        if removed:
            store.delete_embeddings(args.model, removed)
            print(f"Removed {len(removed)} embedding(s) for SKUs no longer in the catalog")

        if not stale:
            print(f"Index up to date for {args.model}: "
                  f"{len(stored)} embedding(s), nothing to do.")
            return 0

        print(f"Embedding {len(stale)} SKU(s) with {args.model} "
              f"({len(current) - len(stale)} already current)...")

        try:
            embedder = SentenceTransformerEmbedder(args.model)
        except Exception as exc:  # pragma: no cover - import-time failure
            print(f"Could not create embedder: {exc}", file=sys.stderr)
            return 1

        started = time.perf_counter()
        for start in range(0, len(stale), args.batch_size):
            batch = stale[start:start + args.batch_size]
            try:
                vectors = embedder.encode([texts[sku] for sku in batch])
            except ImportError as exc:
                print(f"\nsentence-transformers is not installed: {exc}\n"
                      f"Install it, or re-run with --skip-embeddings to load "
                      f"catalog rows only. Lexical (BM25) retrieval works "
                      f"without embeddings.", file=sys.stderr)
                return 1
            store.store_embeddings(
                args.model, batch, vectors, [current[sku] for sku in batch])
            print(f"  {min(start + len(batch), len(stale))}/{len(stale)}")

        elapsed = time.perf_counter() - started
        total = len(store.load_embeddings(args.model)[0])
        print(f"Indexed {len(stale)} SKU(s) in {elapsed:.1f}s "
              f"({len(stale) / elapsed:.0f}/s). "
              f"{total} embedding(s) stored for {args.model}.")
        print(f"Models indexed in this database: {', '.join(store.embedding_models())}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
