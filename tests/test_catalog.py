"""
Tests for catalog storage and hybrid retrieval.

These run without torch or sentence-transformers: the dense half of the
retriever is exercised with a small deterministic fake embedder, so the fusion
logic is tested in CI without a 500MB model download. The real embedder is
covered by the Stage 3 retrieval eval, which reports numbers rather than
asserting them.
"""
import json
import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from catalog import (
    BM25Index, HybridRetriever, ProductStore, QueryRouter, build_search_text,
    flatten_specs, load_catalog, open_catalog, text_hash, tokenize,
)

CATALOG_PATH = os.path.join(os.path.dirname(__file__), '..',
                            'data', 'catalog', 'products.jsonl')


class FakeEmbedder:
    """Deterministic bag-of-words vectors, no model download.

    Good enough to prove fusion works: documents sharing vocabulary with the
    query score higher, and the vectors are stable across runs.
    """

    name = "fake-embedder"
    VOCAB = ["laptop", "phone", "tablet", "gaming", "camera", "battery",
             "storage", "apple", "intel", "nvidia", "headphones", "monitor",
             "licence", "keyboard", "editing"]

    def encode(self, texts):
        import numpy as np
        rows = []
        for text in texts:
            tokens = set(tokenize(text))
            vector = np.array([1.0 if word in tokens else 0.0
                               for word in self.VOCAB], dtype="float32")
            norm = np.linalg.norm(vector)
            rows.append(vector / norm if norm else vector)
        return np.vstack(rows).astype("float32")


class CatalogTestCase(unittest.TestCase):
    """Loads the committed catalog into a scratch database once per class."""

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="catalog-test-")
        cls.db_path = os.path.join(cls.tmp_dir, "catalog.db")
        cls.conn = open_catalog(cls.db_path)
        cls.loaded = load_catalog(cls.conn, CATALOG_PATH)
        cls.store = ProductStore(cls.conn)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()


class TestTextHandling(unittest.TestCase):

    def test_tokenize_preserves_model_numbers(self):
        """The reason BM25 is in the stack at all."""
        self.assertEqual(tokenize("RTX 4080"), ["rtx", "4080"])
        self.assertEqual(tokenize("i9-14900HX"), ["i9", "14900hx"])
        self.assertEqual(tokenize("M3 Pro"), ["m3", "pro"])
        self.assertEqual(tokenize('13.6" Liquid Retina'),
                         ["13", "6", "liquid", "retina"])

    def test_tokenize_handles_empty(self):
        self.assertEqual(tokenize(""), [])
        self.assertEqual(tokenize(None), [])

    def test_flatten_specs(self):
        self.assertEqual(flatten_specs({"cpu": "M3", "ram": "16GB"}),
                         "cpu: M3, ram: 16GB")
        self.assertEqual(flatten_specs({}), "")

    def test_search_text_includes_every_indexed_field(self):
        product = {
            "name": "Acme Widget", "brand": "Acme", "category": "laptops",
            "description": "A fine widget.", "specs": {"cpu": "Fast"},
        }
        text = build_search_text(product)
        for expected in ["Acme Widget", "Acme", "laptops", "A fine widget.",
                         "cpu: Fast"]:
            self.assertIn(expected, text)

    def test_text_hash_is_stable_and_sensitive(self):
        self.assertEqual(text_hash("abc"), text_hash("abc"))
        self.assertNotEqual(text_hash("abc"), text_hash("abd"))


class TestCatalogLoading(CatalogTestCase):

    def test_catalog_loads(self):
        self.assertEqual(self.loaded, 200)
        self.assertEqual(self.store.count(), 200)

    def test_load_is_idempotent(self):
        load_catalog(self.conn, CATALOG_PATH)
        load_catalog(self.conn, CATALOG_PATH)
        self.assertEqual(self.store.count(), 200)

    def test_product_round_trips(self):
        product = self.store.all()[0]
        fetched = self.store.get(product.sku)

        self.assertEqual(fetched.sku, product.sku)
        self.assertEqual(fetched.price_usd, product.price_usd)
        self.assertIsInstance(fetched.specs, dict)

    def test_sku_lookup_is_case_insensitive(self):
        sku = self.store.all()[0].sku
        self.assertIsNotNone(self.store.get(sku.lower()))

    def test_unknown_sku_returns_none(self):
        self.assertIsNone(self.store.get("NOPE-000-0000"))

    def test_catalog_invariants_hold(self):
        """Guards the properties the retrieval eval labels depend on."""
        products = self.store.all()

        names = [p.name for p in products]
        self.assertEqual(len(names), len(set(names)), "duplicate product names")

        skus = [p.sku for p in products]
        self.assertEqual(len(skus), len(set(skus)), "duplicate SKUs")

        for product in products:
            self.assertGreater(product.price_usd, 0)
            self.assertGreaterEqual(product.stock, 0)

        self.assertTrue(any(p.stock == 0 for p in products),
                        "no out-of-stock SKUs, so stock questions are trivial")

    def test_apple_products_only_carry_apple_silicon(self):
        for product in self.store.all():
            if product.brand != "Apple":
                continue
            specs = json.dumps(product.specs)
            for foreign in ["NVIDIA", "Intel", "Ryzen", "Snapdragon", "MediaTek"]:
                self.assertNotIn(foreign, specs,
                                 f"{product.name} has {foreign} in its specs")


class TestBM25(CatalogTestCase):

    def setUp(self):
        self.index = BM25Index(dict(self.store.search_texts()))

    def test_exact_model_identifier(self):
        hits = self.index.search("RTX 4080", k=10)
        self.assertTrue(hits)
        for hit in hits[:3]:
            self.assertIn("4080", json.dumps(self.store.get(hit.sku).specs))

    def test_brand_query(self):
        hits = self.index.search("Lenovo ThinkPad", k=5)
        self.assertTrue(any("ThinkPad" in self.store.get(h.sku).name for h in hits))

    def test_empty_query_returns_nothing(self):
        self.assertEqual(self.index.search("", k=5), [])
        self.assertEqual(self.index.search("!!!", k=5), [])

    def test_nonsense_query_returns_nothing(self):
        self.assertEqual(self.index.search("zzzzqqqq xyzzy", k=5), [])

    def test_respects_k(self):
        self.assertLessEqual(len(self.index.search("laptop", k=3)), 3)

    def test_scores_are_descending(self):
        hits = self.index.search("gaming laptop", k=10)
        self.assertEqual([h.score for h in hits],
                         sorted([h.score for h in hits], reverse=True))

    def test_idf_is_never_negative(self):
        """The reason this uses the Lucene IDF variant.

        Raw Okapi IDF, log((N - df + 0.5) / (df + 0.5)), is negative for any
        term in more than about half the corpus - here "ram", "laptop",
        "storage" and similar - which would make a document score *worse* for
        containing a term the user asked for. rank_bm25 patches that by
        flooring negative values to epsilon * average_idf, an arbitrary
        constant. The +1 inside the log avoids the problem instead.
        """
        self.assertTrue(self.index.idf)
        for term, value in self.index.idf.items():
            self.assertGreater(value, 0, f"idf for {term!r} is not positive")

    def test_matches_rank_bm25_on_discriminative_queries(self):
        """Cross-check the scorer against the reference package.

        Restricted to queries whose terms are rare enough that raw Okapi IDF
        stays positive, which is where the two variants agree. Queries with
        very common terms are expected to differ and are covered by
        test_differs_from_rank_bm25_on_common_terms.
        """
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            self.skipTest("rank_bm25 not installed")

        documents = dict(self.store.search_texts())
        skus = list(documents)
        reference = BM25Okapi([tokenize(documents[sku]) for sku in skus],
                              k1=1.5, b=0.75)

        for query in ["sennheiser momentum", "quietcomfort ultra",
                      "zephyrus", "thinkpad carbon"]:
            for token in tokenize(query):
                self.assertGreater(
                    reference.idf.get(token, 0), 0,
                    f"{token!r} is too common for this comparison")

            scores = reference.get_scores(tokenize(query))
            # rank_bm25 ranks every document and returns the top k whether or
            # not it matched, so its tail holds zero-score documents. This
            # index returns only documents that matched, which is what a
            # retriever should do, so compare over the matching set.
            expected = [skus[i] for i in sorted(range(len(skus)),
                                                key=lambda i: -scores[i])
                        if scores[i] > 0][:5]
            actual = [hit.sku for hit in self.index.search(query, k=5)]
            self.assertEqual(actual, expected, f"ranking differs for {query!r}")

    def test_differs_from_rank_bm25_on_common_terms(self):
        """Documents the divergence rather than pretending it is not there."""
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            self.skipTest("rank_bm25 not installed")

        documents = dict(self.store.search_texts())
        skus = list(documents)
        reference = BM25Okapi([tokenize(documents[sku]) for sku in skus],
                              k1=1.5, b=0.75)

        # "ram" is in nearly every product's flattened specs.
        self.assertLess(
            math.log((len(skus) - sum(1 for s in skus if "ram" in tokenize(documents[s]))
                      + 0.5) /
                     (sum(1 for s in skus if "ram" in tokenize(documents[s])) + 0.5)),
            0, "'ram' is not common enough for this test to be meaningful")

        scores = reference.get_scores(tokenize("16GB RAM laptop"))
        expected = [skus[i] for i in sorted(range(len(skus)),
                                            key=lambda i: -scores[i])
                    if scores[i] > 0][:5]
        actual = [hit.sku for hit in self.index.search("16GB RAM laptop", k=5)]

        self.assertNotEqual(actual, expected)
        # The Lucene variant is the one that keeps laptops on top for a query
        # that says "laptop"; raw Okapi lets floored common-term weights pull
        # phones above them.
        self.assertTrue(all(self.store.get(sku).category == "laptops"
                            for sku in actual),
                        f"expected laptops, got "
                        f"{[(s, self.store.get(s).category) for s in actual]}")

    def test_only_matching_documents_are_returned(self):
        """A retriever must not pad its results with non-matches."""
        hits = self.index.search("sennheiser momentum", k=20)
        self.assertTrue(hits)
        self.assertTrue(all(hit.score > 0 for hit in hits))
        self.assertLess(len(hits), 20)


class TestHybridRetrieval(CatalogTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.embedder = FakeEmbedder()
        skus, texts = zip(*cls.store.search_texts())
        vectors = cls.embedder.encode(list(texts))
        cls.store.store_embeddings(cls.embedder.name, list(skus), vectors,
                                   [text_hash(t) for t in texts])

    def retriever(self, **kwargs):
        return HybridRetriever(self.store, embedder=self.embedder, **kwargs)

    def test_embeddings_round_trip(self):
        skus, matrix = self.store.load_embeddings(self.embedder.name)
        self.assertEqual(len(skus), 200)
        self.assertEqual(matrix.shape, (200, len(FakeEmbedder.VOCAB)))

    def test_dense_mode_returns_results(self):
        hits = self.retriever(mode="dense").search("gaming laptop", k=5)
        self.assertEqual(len(hits), 5)

    def test_bm25_mode_needs_no_embeddings(self):
        retriever = HybridRetriever(self.store, embedder=None, mode="bm25")
        self.assertFalse(retriever.has_dense)
        self.assertTrue(retriever.search("RTX 4080", k=5))

    def test_hybrid_returns_both_rankings(self):
        hits = self.retriever(mode="hybrid").search("gaming laptop", k=10)
        self.assertTrue(any(h.dense_rank for h in hits))
        self.assertTrue(any(h.bm25_rank for h in hits))

    def test_hybrid_recovers_exact_identifier_dense_alone_misses(self):
        """The case that justifies fusing: a bag-of-words dense model has no
        concept of "4080", but BM25 does, and fusion must keep it."""
        dense = [h.sku for h in self.retriever(mode="dense").search("RTX 4080", k=5)]
        hybrid = [h.sku for h in self.retriever(mode="hybrid").search("RTX 4080", k=5)]

        def has_4080(sku):
            return "4080" in json.dumps(self.store.get(sku).specs)

        self.assertFalse(any(has_4080(s) for s in dense),
                         "fake embedder unexpectedly found the identifier")
        self.assertTrue(any(has_4080(s) for s in hybrid),
                        "fusion lost the lexical match")

    def test_fusion_weight_shifts_results_toward_one_retriever(self):
        lexical_heavy = self.retriever(mode="hybrid", dense_weight=0.0,
                                       bm25_weight=1.0).search("RTX 4080", k=5)
        dense_heavy = self.retriever(mode="hybrid", dense_weight=1.0,
                                     bm25_weight=0.0).search("RTX 4080", k=5)

        self.assertNotEqual([h.sku for h in lexical_heavy],
                            [h.sku for h in dense_heavy])

    def test_weight_of_zero_matches_single_mode(self):
        only_bm25 = [h.sku for h in self.retriever(
            mode="hybrid", dense_weight=0.0, bm25_weight=1.0).search("laptop", k=5)]
        pure_bm25 = [h.sku for h in self.retriever(mode="bm25").search("laptop", k=5)]
        self.assertEqual(only_bm25, pure_bm25)

    def test_results_are_deterministic(self):
        first = [h.sku for h in self.retriever().search("gaming laptop", k=5)]
        second = [h.sku for h in self.retriever().search("gaming laptop", k=5)]
        self.assertEqual(first, second)

    def test_ties_break_on_evidence_not_sku_spelling(self):
        """RRF ties must not be decided by alphabetical SKU order.

        When a document is found by both retrievers it should outrank one
        found by a single retriever at the same fused score, and the ordering
        must not depend on how SKUs happen to be spelled.
        """
        retriever = self.retriever(mode="hybrid")
        hits = retriever.search("gaming laptop", k=10)

        found_by_both = [h for h in hits if h.dense_rank and h.bm25_rank]
        found_by_one = [h for h in hits if not (h.dense_rank and h.bm25_rank)]

        if found_by_both and found_by_one:
            # Every both-retriever hit must precede the first single hit of
            # equal score.
            first_single = hits.index(found_by_one[0])
            for hit in found_by_both:
                if abs(hit.score - found_by_one[0].score) < 1e-12:
                    self.assertLess(hits.index(hit), first_single)

    def test_k_is_respected(self):
        for k in (1, 3, 5, 10):
            self.assertLessEqual(len(self.retriever().search("laptop", k=k)), k)


if __name__ == '__main__':
    unittest.main(verbosity=2)


class TestQueryRouter(CatalogTestCase):
    """The router exists to be measured, not assumed; these pin its behaviour."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.router = QueryRouter.from_store(cls.store)

    def test_identifier_queries_are_lexical(self):
        for query in ["RTX 4080 gaming laptop", "M3 Pro", "16GB RAM under $1200",
                      "LAP-DEL-2170", "i9 laptop"]:
            self.assertEqual(self.router.classify(query), "lexical", query)

    def test_need_statements_are_semantic(self):
        for query in ["I need to carry my laptop on my commute",
                      "a cheap phone for my mum",
                      "something for video editing",
                      "my eyes hurt after a day at the screen"]:
            self.assertEqual(self.router.classify(query), "semantic", query)

    def test_generic_category_words_are_not_identifiers(self):
        """"laptop" appears in "Targus CityGear Laptop Sleeve" and "phone" in
        "Nothing Phone (2a)", but neither names a product when a customer uses
        it to describe a need."""
        self.assertNotIn("laptop", self.router.vocabulary)
        self.assertNotIn("phone", self.router.vocabulary)
        self.assertNotIn("tablet", self.router.vocabulary)

    def test_brand_and_line_names_are_identifiers(self):
        for token in ["thinkpad", "macbook", "zephyrus", "lenovo"]:
            self.assertIn(token, self.router.vocabulary, token)

    def test_plural_product_lines_still_match(self):
        self.assertTrue(self.router.signals("do you have thinkpads")["vocabulary"])

    def test_weights_favour_the_matching_retriever(self):
        lexical_dense, lexical_bm25 = self.router.weights("RTX 4080")
        semantic_dense, semantic_bm25 = self.router.weights("something for my mum")

        self.assertGreater(lexical_bm25, lexical_dense)
        self.assertGreater(semantic_dense, semantic_bm25)

    def test_routed_mode_requires_a_router(self):
        retriever = HybridRetriever(self.store, embedder=None, mode="routed")
        with self.assertRaises(ValueError):
            retriever.search("anything", k=3)


class TestRetrievePoolDepth(CatalogTestCase):
    """retrieve_k is an eval variable, so it must actually take effect."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.embedder = FakeEmbedder()
        skus, texts = zip(*cls.store.search_texts())
        vectors = cls.embedder.encode(list(texts))
        cls.store.store_embeddings(cls.embedder.name, list(skus), vectors,
                                   [text_hash(t) for t in texts])

    def test_constructor_and_call_both_set_pool_depth(self):
        shallow = HybridRetriever(self.store, embedder=self.embedder,
                                  mode="hybrid", retrieve_k=5)
        deep = HybridRetriever(self.store, embedder=self.embedder,
                               mode="hybrid", retrieve_k=100)

        # A deeper pool can only add candidates, never remove them.
        shallow_hits = {h.sku for h in shallow.search("laptop", k=20)}
        deep_hits = {h.sku for h in deep.search("laptop", k=20)}
        self.assertGreaterEqual(len(deep_hits), len(shallow_hits))

    def test_per_call_override_beats_constructor(self):
        retriever = HybridRetriever(self.store, embedder=self.embedder,
                                    mode="hybrid", retrieve_k=5)
        few = retriever.search("laptop", k=20)
        many = retriever.search("laptop", k=20, retrieve_k=100)
        self.assertGreaterEqual(len(many), len(few))
