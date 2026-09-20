#!/usr/bin/env python3
"""
Retrieval eval: compare retrieval modes and candidate-pool depths.

Metrics, defined precisely because "Recall@k" is ambiguous when a gold set has
68 members and k is 3:

  hit@k     1 if at least one gold SKU is in the top k, else 0. For a shopping
            assistant this is the metric that matters most: the agent needs one
            correct product to talk about, not all of them.

  recall@k  |gold and top-k| / min(k, |gold|). Capped by k, so a perfect
            retriever scores 1.0 even when the gold set is larger than k.
            Uncapped recall would put a ceiling of 3/68 on a category-browse
            query and make the average meaningless.

  MRR       Mean reciprocal rank of the first gold SKU, 0 if none in the top k.

Results are reported per query category as well as in aggregate. This is not
presentational: a single aggregate averages away the effect the eval exists to
find. Lexical and semantic queries want opposite retrievers, so a mode that
wins overall can still lose badly on half the traffic.

Out-of-catalog queries are scored differently. Their gold set is empty, so
ranking metrics are undefined; what is measured instead is abstain_rate, the
fraction where the retriever returned nothing at all. Returning a plausible
wrong product for "do you have a washing machine" is how a sales agent makes a
promise it cannot keep.

    python evals/run_retrieval.py
    python evals/run_retrieval.py --modes bm25 dense hybrid routed --retrieve-k 20 50 100
    python evals/run_retrieval.py --json evals/results/retrieval.json
"""
import argparse
import json
import os
import statistics
import sys
import time
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from catalog import (  # noqa: E402
    DEFAULT_EMBEDDING_MODEL, HybridRetriever, ProductStore, QueryRouter,
    SentenceTransformerEmbedder, open_catalog,
)
from conversation_memory import DEFAULT_DB_PATH  # noqa: E402
from stats import bootstrap_ci, format_ci, mcnemar  # noqa: E402

DATASET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "datasets", "retrieval.jsonl")

RANKING_CATEGORIES = ["exact_model", "spec_constrained",
                      "semantic_intent", "category_browse"]

# exact_model and category_browse are saturated: the random baseline already
# scores 0.467 on category_browse, and every real mode reaches ~1.0 on
# exact_model. Averaging them into the overall column dilutes it with
# categories that cannot separate one retriever from another, so a
# discriminating-subset overall is reported alongside the full one.
DISCRIMINATING_CATEGORIES = ["spec_constrained", "semantic_intent"]


def load_dataset(path: str = DATASET) -> List[dict]:
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def score_query(gold: List[str], retrieved: List[str], ks=(1, 3, 5)) -> Dict:
    """Metrics for one query. See module docstring for definitions."""
    gold_set = set(gold)
    result = {}

    for k in ks:
        top_k = retrieved[:k]
        overlap = len(gold_set & set(top_k))
        result[f"hit@{k}"] = 1.0 if overlap else 0.0
        result[f"recall@{k}"] = overlap / min(k, len(gold_set)) if gold_set else 0.0

    reciprocal = 0.0
    for position, sku in enumerate(retrieved, start=1):
        if sku in gold_set:
            reciprocal = 1.0 / position
            break
    result["mrr"] = reciprocal
    return result


def mean(values: List[float]) -> float:
    return statistics.mean(values) if values else 0.0


def evaluate(retriever: HybridRetriever, dataset: List[dict],
             k: int = 5, retrieve_k: Optional[int] = None) -> Dict:
    per_query = []
    for row in dataset:
        started = time.perf_counter()
        hits = retriever.search(row["query"], k=k, retrieve_k=retrieve_k)
        elapsed_ms = (time.perf_counter() - started) * 1000
        retrieved = [hit.sku for hit in hits]

        entry = {
            "id": row["id"],
            "query": row["query"],
            "category": row["category"],
            "n_gold": len(row["gold_skus"]),
            "n_retrieved": len(retrieved),
            "retrieved": retrieved,
            "latency_ms": round(elapsed_ms, 3),
        }
        if row["category"] == "out_of_catalog":
            entry["abstained"] = len(retrieved) == 0
        else:
            entry.update(score_query(row["gold_skus"], retrieved))
        per_query.append(entry)

    ranked = [e for e in per_query if e["category"] != "out_of_catalog"]
    out_of_catalog = [e for e in per_query if e["category"] == "out_of_catalog"]

    def aggregate(entries):
        if not entries:
            return {}
        out = {"n": len(entries)}
        for metric in ("hit@1", "hit@3", "hit@5",
                       "recall@1", "recall@3", "recall@5", "mrr"):
            values = [e[metric] for e in entries]
            point, low, high = bootstrap_ci(values)
            out[metric] = round(point, 4)
            out[f"{metric}_ci"] = [round(low, 4), round(high, 4)]
        return out

    summary = {
        "overall": aggregate(ranked),
        "overall_discriminating": aggregate(
            [e for e in ranked if e["category"] in DISCRIMINATING_CATEGORIES]),
        "by_category": {
            category: aggregate([e for e in ranked if e["category"] == category])
            for category in RANKING_CATEGORIES
        },
        "out_of_catalog": {
            "n": len(out_of_catalog),
            "abstain_rate": round(
                mean([1.0 if e["abstained"] else 0.0 for e in out_of_catalog]), 4),
        },
        "latency_ms_median": round(
            statistics.median([e["latency_ms"] for e in per_query]), 3),
    }
    return {"summary": summary, "per_query": per_query}


class OracleRouter:
    """Routes on the dataset's ground-truth category instead of a classifier.

    The real router agrees with those labels 83.5% of the time, so its errors
    put a ceiling on what routing can deliver. Running the same weighting with
    a perfect router separates two questions that otherwise stay tangled: is
    routing the wrong lever, or is this router simply not good enough yet?
    """

    def __init__(self, dataset):
        lexical = {"exact_model", "spec_constrained"}
        self.labels = {row["query"]: ("lexical" if row["category"] in lexical
                                      else "semantic") for row in dataset}

    def classify(self, query: str) -> str:
        return self.labels.get(query, "mixed")

    def weights(self, query: str):
        return {"lexical": (0.3, 1.0), "mixed": (1.0, 1.0),
                "semantic": (1.0, 0.3)}[self.classify(query)]


class RandomRetriever:
    """Seeded random SKUs: the floor any real retriever must clear.

    This is not decoration. A category-browse gold set here can hold 68 of 200
    products, so drawing 3 at random hits one about 70% of the time. Without
    this row, a reported hit@3 of 1.0 on that category looks like a result
    rather than the near-freebie it is, and the reader cannot tell which
    categories actually discriminate between retrievers.
    """

    mode = "random"

    def __init__(self, store, seed: int = 20260918):
        import random
        self.skus = [p.sku for p in store.all()]
        self.rng = random.Random(seed)

    def search(self, query: str, k: int = 5, retrieve_k=None):
        from catalog import Hit
        picks = self.rng.sample(self.skus, min(k, len(self.skus)))
        return [Hit(sku=sku, score=0.0) for sku in picks]


def build_retriever(store, embedder, mode: str, retrieve_k: Optional[int],
                    router: Optional[QueryRouter]) -> HybridRetriever:
    return HybridRetriever(store, embedder=embedder, mode=mode,
                           retrieve_k=retrieve_k, router=router)


def format_table(results: Dict) -> str:
    """Markdown table of every configuration, per category."""
    lines = []
    header = (f"| {'config':<22} | {'hit@1':>6} | {'hit@3':>6} | {'hit@5':>6} | "
              f"{'rec@3':>6} | {'MRR':>6} | {'abstain':>7} |")
    divider = ("|" + "-" * 24 + "|" + ("-" * 8 + "|") * 5 + "-" * 9 + "|")

    lines.append("**Overall** (85 in-catalog queries; abstain over 15 out-of-catalog)\n")
    lines.append(f"| {'config':<24} | {'hit@3 [95% CI]':<24} | "
                 f"{'discriminating hit@3':<24} | {'MRR':>6} | {'abstain':>7} |")
    lines.append("|" + "-" * 26 + "|" + "-" * 26 + "|" + "-" * 26 + "|"
                 + "-" * 8 + "|" + "-" * 9 + "|")
    for name, result in results.items():
        s = result["summary"]
        o, d = s["overall"], s["overall_discriminating"]
        lines.append(
            f"| {name:<24} | "
            f"{format_ci(o['hit@3'], *o['hit@3_ci']):<24} | "
            f"{format_ci(d['hit@3'], *d['hit@3_ci']):<24} | "
            f"{o['mrr']:>6.3f} | {s['out_of_catalog']['abstain_rate']:>7.3f} |")

    for category in RANKING_CATEGORIES:
        first = next(iter(results.values()))
        n = first["summary"]["by_category"].get(category, {}).get("n", 0)
        lines.append(f"\n**{category}** (n={n})\n")
        lines.append(f"| {'config':<24} | {'hit@3 [95% CI]':<24} | "
                     f"{'rec@3':>6} | {'MRR':>6} |")
        lines.append("|" + "-" * 26 + "|" + "-" * 26 + "|" + "-" * 8 + "|"
                     + "-" * 8 + "|")
        for name, result in results.items():
            c = result["summary"]["by_category"].get(category) or {}
            if not c:
                continue
            lines.append(
                f"| {name:<24} | {format_ci(c['hit@3'], *c['hit@3_ci']):<24} | "
                f"{c['recall@3']:>6.3f} | {c['mrr']:>6.3f} |")
    return "\n".join(lines)


def paired_tests(results: Dict, dataset: List[dict]) -> str:
    """McNemar on the comparisons the conclusions actually rest on."""
    def outcomes(name, metric="hit@3", category=None):
        rows = results[name]["per_query"]
        return [e[metric] for e in rows
                if e["category"] != "out_of_catalog"
                and (category is None or e["category"] == category)]

    comparisons = []
    names = list(results)

    def add(label, a, b, category=None):
        if a not in names or b not in names:
            return
        result = mcnemar(outcomes(a, category=category),
                         outcomes(b, category=category))
        comparisons.append((label, a, b, result))

    add("semantic_intent (the headline claim)", "dense", "hybrid (pool=20)",
        "semantic_intent")
    add("spec_constrained", "hybrid (pool=20)", "dense", "spec_constrained")
    add("overall: routed vs hybrid", "routed (pool=20)", "hybrid (pool=20)")
    add("overall: routed vs dense", "routed (pool=20)", "dense")
    add("overall: dense vs bm25", "dense", "bm25")
    add("semantic: routed vs hybrid", "routed (pool=20)", "hybrid (pool=20)",
        "semantic_intent")
    add("semantic: dense vs routed", "dense", "routed (pool=20)",
        "semantic_intent")

    lines = ["\n### Paired significance (McNemar exact, hit@3)\n",
             "| comparison | A | B | A only | B only | discordant | p |",
             "|---|---|---|---|---|---|---|"]
    for label, a, b, r in comparisons:
        lines.append(f"| {label} | {a} | {b} | {r['a_only']} | {r['b_only']} | "
                     f"{r['n_discordant']} | {r['p_value']:.3f} |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=os.getenv("AGENT_DB_PATH", DEFAULT_DB_PATH))
    parser.add_argument("--dataset", default=DATASET)
    parser.add_argument("--model", default=os.getenv("EMBEDDING_MODEL",
                                                     DEFAULT_EMBEDDING_MODEL))
    parser.add_argument("--modes", nargs="+",
                        default=["random", "bm25", "dense", "hybrid", "routed",
                                 "oracle"])
    parser.add_argument("--retrieve-k", nargs="+", type=int, default=[20, 50, 100],
                        help="candidate pool depth per retriever before fusion")
    parser.add_argument("--k", type=int, default=5, help="results returned per query")
    parser.add_argument("--json", dest="json_out",
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "results", "retrieval.json"))
    args = parser.parse_args()

    dataset = load_dataset(args.dataset)
    conn = open_catalog(args.db)
    store = ProductStore(conn)
    if store.count() == 0:
        print(f"No catalog in {args.db}. Run scripts/build_index.py first.",
              file=sys.stderr)
        return 1

    embedder = None
    has_dense = store.load_embeddings(args.model)[1] is not None
    if has_dense:
        embedder = SentenceTransformerEmbedder(args.model)
    else:
        print(f"No embeddings for {args.model}; dense/hybrid/routed will be "
              f"skipped. Run scripts/build_index.py.", file=sys.stderr)

    router = QueryRouter.from_store(store)

    results = {}
    if "oracle" in args.modes and has_dense:
        oracle = OracleRouter(dataset)
        depth = args.retrieve_k[0]
        results[f"routed-ORACLE (pool={depth})"] = evaluate(
            build_retriever(store, embedder, "routed", depth, oracle),
            dataset, k=args.k, retrieve_k=depth)
        print("  ran routed-ORACLE", file=sys.stderr)

    if "random" in args.modes:
        results["random baseline"] = evaluate(
            RandomRetriever(store), dataset, k=args.k)
        print("  ran random baseline", file=sys.stderr)

    for mode in args.modes:
        if mode in ("random", "oracle"):
            continue
        if mode in ("dense", "hybrid", "routed") and not has_dense:
            continue
        # Pool depth only changes fusion; single-retriever modes ignore it.
        depths = args.retrieve_k if mode in ("hybrid", "routed") else [args.retrieve_k[0]]
        for depth in depths:
            name = mode if mode not in ("hybrid", "routed") else f"{mode} (pool={depth})"
            retriever = build_retriever(store, embedder, mode, depth, router)
            results[name] = evaluate(retriever, dataset, k=args.k, retrieve_k=depth)
            print(f"  ran {name}", file=sys.stderr)

    conn.close()

    print(format_table(results))
    print(paired_tests(results, dataset))

    # Router decisions, checked against the dataset's own category labels.
    # exact_model and spec_constrained name things; semantic_intent and
    # category_browse describe needs. That is the distinction the router is
    # trying to make, so it is a fair, independent check on it.
    expected = {"exact_model": "lexical", "spec_constrained": "lexical",
                "semantic_intent": "semantic", "category_browse": "semantic"}
    counts, confusion = {}, {}
    for row in dataset:
        decision = router.classify(row["query"])
        counts[decision] = counts.get(decision, 0) + 1
        want = expected.get(row["category"])
        if want:
            confusion[(row["category"], decision)] = confusion.get(
                (row["category"], decision), 0) + 1

    print(f"\nRouter classified {len(dataset)} queries: "
          + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    agree = sum(n for (cat, dec), n in confusion.items() if dec == expected[cat])
    total = sum(confusion.values())
    print(f"Router vs dataset category (lexical<-exact_model/spec_constrained, "
          f"semantic<-semantic_intent/category_browse): "
          f"{agree}/{total} = {agree / total:.3f}")
    for (cat, dec), n in sorted(confusion.items()):
        mark = " " if dec == expected[cat] else "*"
        print(f"  {mark} {cat:<18} -> {dec:<9} {n:>3}")

    if args.json_out:
        os.makedirs(os.path.dirname(args.json_out), exist_ok=True)
        payload = {
            "dataset": os.path.basename(args.dataset),
            "n_queries": len(dataset),
            "embedding_model": args.model if has_dense else None,
            "k": args.k,
            "configs": {name: r["summary"] for name, r in results.items()},
            "per_query": {name: r["per_query"] for name, r in results.items()},
        }
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        print(f"\nWrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
