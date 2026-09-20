#!/usr/bin/env python3
"""
Can dense retrieval learn to say "we don't stock that"?

The retrieval eval found that every configuration containing a dense retriever
abstains on 0% of out-of-catalog queries. Cosine similarity over the whole
catalog always returns k results, so "do you have a washing machine" comes back
with confident products. Pure *ranking* cannot fix that — but abstention is a
decision layered on top of ranking, and it is testable.

Three rules are measured here, all on the same 100 queries:

  absolute   abstain when the top-1 cosine similarity falls below tau.
             The obvious rule; the question is whether in-catalog and
             out-of-catalog queries separate at all on that axis.

  gap        abstain when top-1 minus the mean of ranks 2..k is below tau,
             i.e. nothing stands out from the pack. This can fire even when
             absolute similarity is high, which happens when a query matches a
             whole category equally well.

  combined   abstain when either rule fires.

Each is reported as a tradeoff curve, not a single number: the operating point
is a product decision about how often you would rather say "we don't stock
that" wrongly than promise something you cannot sell. AUC is reported first,
because if the two populations do not separate, no threshold rescues them.

    python evals/run_abstention.py
"""
import argparse
import json
import os
import sys
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from catalog import (  # noqa: E402
    DEFAULT_EMBEDDING_MODEL, HybridRetriever, ProductStore,
    SentenceTransformerEmbedder, open_catalog,
)
from conversation_memory import DEFAULT_DB_PATH  # noqa: E402
from stats import roc_auc  # noqa: E402
from run_retrieval import DATASET, load_dataset  # noqa: E402


def collect_scores(retriever, dataset, k=5) -> List[Dict]:
    """Per-query dense signals plus whether the gold answer was retrieved."""
    rows = []
    for row in dataset:
        hits = retriever.dense_search(row["query"], k=max(k, 5))
        bm25_hits = retriever.bm25.search(row["query"], k)
        scores = [h.score for h in hits]
        top1 = scores[0] if scores else 0.0
        rest = scores[1:k] or [0.0]
        gold = set(row["gold_skus"])

        rows.append({
            "id": row["id"],
            "query": row["query"],
            "category": row["category"],
            "in_catalog": row["category"] != "out_of_catalog",
            "top1": top1,
            "gap": top1 - (sum(rest) / len(rest)),
            "hit@3": 1.0 if gold & {h.sku for h in hits[:3]} else 0.0,
            # BM25 abstains for free when no query token matches anything.
            "bm25_empty": len(bm25_hits) == 0,
        })
    return rows


def rule_scores(rows, predicate) -> Dict:
    """Evaluate an arbitrary abstain predicate over the same queries."""
    in_catalog = [r for r in rows if r["in_catalog"]]
    out_catalog = [r for r in rows if not r["in_catalog"]]
    correct = sum(1 for r in out_catalog if predicate(r))
    false = sum(1 for r in in_catalog if predicate(r))
    retained = sum(r["hit@3"] for r in in_catalog if not predicate(r))
    return {
        "abstain_rate_ooc": round(correct / len(out_catalog), 4),
        "false_abstain_rate": round(false / len(in_catalog), 4),
        "hit@3_after": round(retained / len(in_catalog), 4),
        "youden_j": round(correct / len(out_catalog) - false / len(in_catalog), 4),
    }


def sweep(rows: List[Dict], field: str, thresholds: List[float]) -> List[Dict]:
    """Abstain when `field` < tau. Report both error directions."""
    in_catalog = [r for r in rows if r["in_catalog"]]
    out_catalog = [r for r in rows if not r["in_catalog"]]

    curve = []
    for tau in thresholds:
        correct_abstain = sum(1 for r in out_catalog if r[field] < tau)
        false_abstain = sum(1 for r in in_catalog if r[field] < tau)
        # An abstained in-catalog query is a miss: the customer is told we do
        # not stock something we do stock.
        retained_hits = sum(r["hit@3"] for r in in_catalog if r[field] >= tau)

        curve.append({
            "tau": round(tau, 4),
            "abstain_rate_ooc": round(correct_abstain / len(out_catalog), 4),
            "false_abstain_rate": round(false_abstain / len(in_catalog), 4),
            "hit@3_after": round(retained_hits / len(in_catalog), 4),
            "youden_j": round(correct_abstain / len(out_catalog)
                              - false_abstain / len(in_catalog), 4),
        })
    return curve


def thresholds_for(rows, field, steps=40):
    values = sorted(r[field] for r in rows)
    low, high = values[0], values[-1]
    span = high - low or 1.0
    return [low + span * i / steps for i in range(steps + 1)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=os.getenv("AGENT_DB_PATH", DEFAULT_DB_PATH))
    parser.add_argument("--dataset", default=DATASET)
    parser.add_argument("--model", default=os.getenv("EMBEDDING_MODEL",
                                                     DEFAULT_EMBEDDING_MODEL))
    parser.add_argument("--json", dest="json_out",
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "results", "abstention.json"))
    args = parser.parse_args()

    dataset = load_dataset(args.dataset)
    conn = open_catalog(args.db)
    store = ProductStore(conn)
    if store.load_embeddings(args.model)[1] is None:
        print("No embeddings; run scripts/build_index.py first.", file=sys.stderr)
        return 1

    retriever = HybridRetriever(store, embedder=SentenceTransformerEmbedder(args.model),
                                mode="dense")
    rows = collect_scores(retriever, dataset)
    conn.close()

    in_catalog = [r for r in rows if r["in_catalog"]]
    out_catalog = [r for r in rows if not r["in_catalog"]]

    print(f"In-catalog queries: {len(in_catalog)}   "
          f"Out-of-catalog: {len(out_catalog)}\n")

    print("### Separability (AUC, 0.5 = no information)\n")
    print("| signal | AUC | in-catalog median | out-of-catalog median |")
    print("|---|---|---|---|")
    results = {}
    for field in ("top1", "gap"):
        auc = roc_auc([r[field] for r in in_catalog],
                      [r[field] for r in out_catalog])
        in_med = sorted(r[field] for r in in_catalog)[len(in_catalog) // 2]
        out_med = sorted(r[field] for r in out_catalog)[len(out_catalog) // 2]
        results[field] = {"auc": round(auc, 4)}
        print(f"| {field} | {auc:.3f} | {in_med:.4f} | {out_med:.4f} |")

    # Combined rule: abstain if either signal is below its own threshold.
    for field in ("top1", "gap"):
        curve = sweep(rows, field, thresholds_for(rows, field))
        results[field]["curve"] = curve
        best = max(curve, key=lambda c: c["youden_j"])
        results[field]["best_youden"] = best

        print(f"\n### {field} threshold sweep\n")
        print("| tau | abstain on out-of-catalog | false-abstain on in-catalog "
              "| hit@3 after | Youden J |")
        print("|---|---|---|---|---|")
        # Print a readable subset plus the optimum.
        shown = curve[::max(1, len(curve) // 8)]
        if best not in shown:
            shown.append(best)
        for point in sorted(shown, key=lambda c: c["tau"]):
            mark = " **<- best J**" if point is best else ""
            print(f"| {point['tau']:.3f} | {point['abstain_rate_ooc']:.3f} | "
                  f"{point['false_abstain_rate']:.3f} | {point['hit@3_after']:.3f} "
                  f"| {point['youden_j']:.3f}{mark} |")

    # The comparison that matters: BM25 already abstains for free by returning
    # nothing when no token matches. What does a dense threshold add on top?
    print("\n### Rule comparison\n")
    print("| rule | abstain on out-of-catalog | false-abstain on in-catalog "
          "| hit@3 after | Youden J |")
    print("|---|---|---|---|---|")

    best_tau = results["top1"]["best_youden"]["tau"]
    conservative = min(
        (c for c in results["top1"]["curve"] if c["false_abstain_rate"] <= 0.05),
        key=lambda c: -c["abstain_rate_ooc"], default=None)

    rules = [
        ("no abstention (current behaviour)", lambda r: False),
        ("bm25 returns nothing", lambda r: r["bm25_empty"]),
        (f"dense top1 < {best_tau:.3f} (best J)",
         lambda r: r["top1"] < best_tau),
    ]
    if conservative:
        rules.append((f"dense top1 < {conservative['tau']:.3f} (<=5% false)",
                      lambda r, t=conservative["tau"]: r["top1"] < t))
    rules.append((f"bm25 empty OR dense top1 < {best_tau:.3f}",
                  lambda r: r["bm25_empty"] or r["top1"] < best_tau))
    if conservative:
        rules.append((f"bm25 empty OR dense top1 < {conservative['tau']:.3f}",
                      lambda r, t=conservative["tau"]:
                      r["bm25_empty"] or r["top1"] < t))

    results["rules"] = {}
    for label, predicate in rules:
        scored = rule_scores(rows, predicate)
        results["rules"][label] = scored
        print(f"| {label} | {scored['abstain_rate_ooc']:.3f} | "
              f"{scored['false_abstain_rate']:.3f} | {scored['hit@3_after']:.3f} "
              f"| {scored['youden_j']:.3f} |")

    if args.json_out:
        os.makedirs(os.path.dirname(args.json_out), exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump({"model": args.model, "n_in_catalog": len(in_catalog),
                       "n_out_of_catalog": len(out_catalog),
                       "signals": results, "per_query": rows},
                      handle, indent=2, ensure_ascii=False)
        print(f"\nWrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
