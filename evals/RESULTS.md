# Evaluation results

Every number here is produced by a script in this repository and can be
re-run. Nothing is estimated, and no figure describes real usage — this
project has no users and no production traffic.

| | |
|---|---|
| Date | 2026-09-18 |
| Commit | `c362577` |
| Catalog | `data/catalog/products.jsonl`, 200 synthetic SKUs, seed 20260918 |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (384-dim) |
| Machine | Apple Silicon, CPU only, Python 3.12.12 |

**Reproduce:**

```bash
pip install -r config/requirements.txt -r config/requirements-ml.txt
python scripts/generate_catalog.py
python scripts/build_index.py
python evals/datasets/build_retrieval_dataset.py
python evals/run_retrieval.py       # section 1
python evals/run_abstention.py      # section 2
```

---

## Reading these numbers

Intervals are percentile bootstrap 95% CIs over queries (10,000 resamples,
seeded). Comparisons between modes use **McNemar's exact test**, because every
mode runs over the same queries — that is a paired design, and a
two-proportion z-test would discard the pairing that carries most of the
information.

This matters more than usual here. The per-category slices are 15–25 queries,
so a difference of two queries looks like a difference of 0.08. **Several
differences that look meaningful in the point estimates do not survive a
significance test, and are labelled as such below.**

---

## 1. Retrieval

### Metric definitions

"Recall@k" is ambiguous when a gold set holds 68 members and k is 3, so three
metrics are reported separately:

| Metric | Definition |
|---|---|
| `hit@k` | 1 if at least one gold SKU is in the top k. What matters most for a sales agent: it needs one correct product to talk about, not all of them. |
| `recall@k` | `|gold ∩ top-k| / min(k, |gold|)`. Capped by k, so a perfect retriever scores 1.0 even when the gold set exceeds k. Uncapped recall would cap a category-browse query at 3/68. |
| `MRR` | Mean reciprocal rank of the first gold SKU; 0 if none in the top k. |
| `abstain` | Out-of-catalog queries only: fraction where the retriever returned **nothing**. Ranking metrics are undefined on an empty gold set. |

### Dataset

100 queries, `evals/datasets/retrieval.jsonl`, built by
`evals/datasets/build_retrieval_dataset.py`.

Queries were written from the customer's side first and matched to products
afterwards. None is a paraphrase of a product description — that is the usual
route to a benchmark that reports ~1.0 and means nothing. The set deliberately
contains misspellings (`thinkpaid x1`, `macbok air`), colloquial model names
(`sony xm5`), dropped brand words (`samsung s24 ultra` for a Galaxy),
run-together tokens (`dell xps13`), wrong brand attribution (`lenovo xps 13`),
vague budget language (`a laptop, nothing over a grand`), symptom statements
that never name a product (`my eyes hurt after a day at the screen`), and
competitor brands that are not stocked — including `do you sell vivo phones`,
where "vivo" is a substring of the ASUS **Vivo**book line that *is* stocked.

Gold sets come from explicit predicates over the catalog, never from a
retriever's own output. Every query carries a `gold_rule` in plain words so any
label can be audited without rerunning anything.

| Category | n | Gold set size (min / median / max) |
|---|---|---|
| exact_model | 20 | 1 / 2 / 6 |
| spec_constrained | 25 | 1 / 8 / 36 |
| semantic_intent | 25 | 1 / 5 / 33 |
| category_browse | 15 | 2 / 16 / 68 |
| out_of_catalog | 15 | empty by design |

### Overall

`discriminating` covers only `spec_constrained` + `semantic_intent` (n=50).
The other two categories are saturated — see finding 6 — so the full overall
column is partly diluted by categories that cannot separate one retriever from
another.

| config | hit@3 [95% CI] | discriminating hit@3 [95% CI] | MRR | abstain |
|---|---|---|---|---|
| random baseline | 0.165 [0.094, 0.247] | 0.140 [0.060, 0.240] | 0.110 | 0.000 |
| bm25 | 0.565 [0.459, 0.671] | 0.440 [0.300, 0.580] | 0.521 | **0.333** |
| dense | 0.788 [0.694, 0.871] | 0.640 [0.500, 0.780] | 0.725 | 0.000 |
| hybrid (pool=20) | 0.824 [0.741, 0.906] | 0.700 [0.580, 0.820] | 0.723 | 0.000 |
| hybrid (pool=50) | 0.824 [0.741, 0.906] | 0.700 [0.580, 0.820] | 0.729 | 0.000 |
| hybrid (pool=100) | 0.812 [0.729, 0.894] | 0.680 [0.540, 0.800] | 0.723 | 0.000 |
| routed (pool=20) | 0.847 [0.765, 0.918] | 0.760 [0.640, 0.880] | 0.748 | 0.000 |
| routed (pool=50) | 0.812 [0.729, 0.894] | 0.700 [0.560, 0.820] | 0.734 | 0.000 |
| routed (pool=100) | 0.812 [0.729, 0.894] | 0.700 [0.560, 0.820] | 0.734 | 0.000 |
| routed-ORACLE (pool=20) | 0.847 [0.765, 0.918] | 0.760 [0.640, 0.880] | 0.748 | 0.000 |

Every interval in that column overlaps every other except the random baseline
and bm25. **No mode is distinguishable from the next-best on the overall
number alone.**

### By category

**exact_model** (n=20) — misspellings, partial names, wrong brand attribution

| config | hit@3 [95% CI] | rec@3 | MRR |
|---|---|---|---|
| random baseline | 0.000 [0.000, 0.000] | 0.000 | 0.000 |
| bm25 | 0.950 [0.850, 1.000] | 0.917 | 0.892 |
| dense | **1.000 [1.000, 1.000]** | 0.967 | 0.975 |
| hybrid (pool=20) | 1.000 [1.000, 1.000] | 0.967 | 0.950 |
| routed (pool=20) | 0.950 [0.850, 1.000] | 0.950 | 0.935 |

**spec_constrained** (n=25) — "16GB RAM under $1200", "rtx 4080 under $2500"

| config | hit@3 [95% CI] | rec@3 | MRR |
|---|---|---|---|
| random baseline | 0.120 [0.000, 0.240] | 0.053 | 0.108 |
| bm25 | 0.640 [0.440, 0.840] | 0.553 | 0.608 |
| dense | 0.600 [0.400, 0.800] | 0.447 | 0.565 |
| **hybrid (pool=20)** | **0.920 [0.800, 1.000]** | 0.700 | 0.793 |
| routed (pool=20) | 0.920 [0.800, 1.000] | 0.687 | 0.773 |

**semantic_intent** (n=25) — need statements that never name a product

| config | hit@3 [95% CI] | rec@3 | MRR |
|---|---|---|---|
| random baseline | 0.160 [0.040, 0.320] | 0.067 | 0.123 |
| bm25 | 0.240 [0.080, 0.400] | 0.147 | 0.218 |
| **dense** | **0.680 [0.480, 0.840]** | 0.360 | 0.541 |
| hybrid (pool=20) | 0.480 [0.280, 0.680] | 0.287 | 0.391 |
| routed (pool=20) | 0.600 [0.400, 0.800] | 0.347 | 0.460 |

**category_browse** (n=15) — "show me laptops", "any thinkpads"

| config | hit@3 [95% CI] | rec@3 | MRR |
|---|---|---|---|
| random baseline | 0.467 [0.200, 0.733] | 0.156 | 0.238 |
| bm25 | 0.467 [0.200, 0.733] | 0.400 | 0.389 |
| dense | 1.000 [1.000, 1.000] | 0.978 | 0.967 |
| hybrid (pool=20) | 1.000 [1.000, 1.000] | 0.867 | 0.856 |
| routed (pool=20) | 1.000 [1.000, 1.000] | 0.956 | 0.933 |

### Paired significance (McNemar exact, hit@3)

| comparison | A | B | A only | B only | discordant | p |
|---|---|---|---|---|---|---|
| semantic_intent | dense | hybrid (pool=20) | 6 | 1 | 7 | **0.125** |
| spec_constrained | hybrid (pool=20) | dense | 8 | 0 | 8 | **0.008** |
| overall | routed (pool=20) | hybrid (pool=20) | 3 | 1 | 4 | 0.625 |
| overall | routed (pool=20) | dense | 9 | 4 | 13 | 0.267 |
| overall | dense | bm25 | 25 | 6 | 31 | **0.001** |
| semantic_intent | routed (pool=20) | hybrid (pool=20) | 3 | 0 | 3 | 0.250 |
| semantic_intent | dense | routed (pool=20) | 3 | 1 | 4 | 0.625 |

---

## What the numbers say

### 1. Hybrid beats dense on spec-constrained queries. This is the one solid result.

hit@3 **0.920 [0.800, 1.000]** against dense **0.600 [0.400, 0.800]**, and
hybrid won on 8 queries that dense lost while losing none that dense won —
**p = 0.008**. Neither retriever alone is close. Exact tokens ("4080", "16GB",
"i9") and semantic framing both matter here, and fusion is the only thing that
gets both.

### 2. Dense beats hybrid on semantic queries — suggestive, not significant.

This was the headline claim, and it does **not** clear the bar. hit@3 0.680 vs
0.480 looks decisive, but on n=25 that is 17 queries versus 12, and the paired
test gives **6 discordant in dense's favour, 1 against, p = 0.125**.

Stated honestly: **the direction is consistent and the mechanism is
understood, but 25 queries cannot establish it at p < 0.05.** The correct
next step is more semantic queries, not a stronger claim.

The mechanism is worth recording regardless, because it is concrete. Taking "I
need to carry my laptop on my commute" and printing actual ranks at pool=20:

| product | dense rank | bm25 rank | RRF score |
|---|---|---|---|
| WD My Passport SSD | 5 | **1** | **0.0318** |
| Apple MacBook Air 15 | 10 | 2 | 0.0304 |
| Apple MacBook Air 13 | 9 | 3 | 0.0304 |
| Targus CityGear Laptop Sleeve | **1** | 15 | 0.0297 |
| Peak Design Everyday Backpack 20L | 2 | — | 0.0161 |
| Incase Compass Backpack | 3 | — | 0.0159 |

The correct answers are the bottom three. The sleeve is dense rank 1, but BM25
ranks it 15th, so 1/61 + 1/75 = 0.0297 loses to an SSD that BM25 puts first
because its description contains the token "laptop". The two backpacks are
dense ranks 2 and 3 but absent from BM25's pool, so they earn one contribution
of ~0.016 each.

RRF rewards cross-retriever consensus. Consensus is evidence when both
retrievers have signal and noise when one has none — and on semantic queries
BM25 scores **0.240 against a random baseline of 0.160**, barely above chance,
yet still holds equal fusion weight.

### 3. "Routed is the best overall config" — retracted. Not supported.

The point estimate (0.847 vs hybrid's 0.824) is **three queries won, one lost,
p = 0.625**. That is not a difference. Routed vs dense overall is 9–4,
**p = 0.267** — better, still not significant.

On the discriminating subset routed is 0.760 [0.640, 0.880] against hybrid's
0.700 [0.580, 0.820]. Overlapping intervals, same conclusion.

What can be said: routing does not *hurt*, and it moves semantic queries in the
right direction (0.480 → 0.600, 3–0 discordant, p = 0.250). What cannot be said
is that it is the best configuration.

### 4. A perfect router changes nothing. Routing is not router-limited.

The heuristic router agrees with the dataset's own labels 71/85 = 0.835, which
raised the obvious question: is routing held back by classifier error?

No. Running the identical weighting with an oracle that routes on ground-truth
labels:

| | overall hit@3 | discriminating | semantic_intent |
|---|---|---|---|
| routed (heuristic) | 0.847 | 0.760 | 0.600 |
| routed (**oracle**) | 0.847 | 0.760 | 0.600 |

The oracle changes the ranking on **13 of 100 queries** and changes hit@3 on
**zero of them**. Its only effect anywhere is a 0.017 drop in exact_model
recall@3.

So a better classifier is not worth building. The ceiling is the weighting
scheme itself: a 0.3 down-weight still consults a near-random retriever on
semantic queries. The next experiment is a hard switch — weight 0.0, which this
harness already expresses — not a smarter router.

(The 0.835 figure also understates the router: 6 of its 14 disagreements are
`category_browse` queries like "any thinkpads" and "show me macbooks", which
name a product line and which the router calls lexical. That is defensible, and
arguably the expected-label mapping is what is wrong there.)

### 5. Candidate-pool depth does essentially nothing. Hypothesis not supported.

The theory was that a shallow top-20 pool penalises documents strong in one
retriever but absent from the other's pool, and that a deeper pool would
dissolve the effect.

| pool | overall hit@3 | semantic_intent hit@3 |
|---|---|---|
| 20 | 0.824 | 0.480 |
| 50 | 0.824 | 0.480 |
| 100 | 0.812 | **0.440** |

Flat overall, slightly *worse* on semantic queries. The likely reason is
catalog size: at 200 products a pool of 100 is half the catalog, so nearly
everything lands in both pools and the consensus signal RRF depends on degrades
into noise. **This is a finding about small corpora and may not hold at 200k
SKUs.**

### 6. Was the benchmark too easy? Mostly no, with two saturated categories.

Best overall hit@3 is **0.847**, under the ~0.95 that would suggest the dataset
is trivial, and the random baseline is 0.165.

Two categories should not be read as results:

- `exact_model` — dense reaches 1.000. Random scores 0.000, so it discriminates
  against chance but not between good retrievers.
- `category_browse` — dense reaches 1.000, but **random scores 0.467**, because
  a gold set can hold 68 of 200 products. Nothing above ~0.5 here is
  impressive, and **bm25 scores exactly 0.467 — precisely the random
  baseline**, so BM25 is no better than chance at category browsing.

Discriminating power is concentrated in `semantic_intent` and
`spec_constrained`, which is why the discriminating-subset column exists.

---

## 2. Abstention: can dense retrieval say "we don't stock that"?

**Reproduce:** `python evals/run_abstention.py`

Section 1 found every dense-containing mode abstains on 0% of out-of-catalog
queries. An earlier draft of this document concluded "retrieval cannot fix
this". That was too strong: pure *ranking* cannot, but abstention is a decision
layered on ranking, and it is measurable.

### Separability

| signal | AUC | in-catalog median | out-of-catalog median |
|---|---|---|---|
| top-1 cosine | **0.725** | 0.4941 | 0.3266 |
| score gap (top1 − mean of ranks 2–5) | 0.588 | 0.0440 | 0.0368 |

Top-1 cosine carries real but modest signal. **The gap heuristic barely beats
chance (0.588) and is not worth pursuing** — a query that matches a whole
category equally well looks much like one that matches nothing.

### Rule comparison

`hit@3 after` counts a wrongly-abstained in-catalog query as a miss: telling a
customer you do not stock something you do stock is a failure, not a neutral
outcome.

| rule | abstain on out-of-catalog | false-abstain on in-catalog | hit@3 after | Youden J |
|---|---|---|---|---|
| no abstention (current) | 0.000 | 0.000 | 0.788 | 0.000 |
| **bm25 returns nothing** | 0.333 | **0.059** | 0.729 | 0.275 |
| dense top-1 < 0.385 (best J) | **0.733** | 0.247 | 0.600 | **0.486** |
| dense top-1 < 0.247 (≤5% false) | 0.200 | 0.047 | 0.765 | 0.153 |
| bm25 empty OR dense < 0.385 | 0.733 | 0.306 | 0.541 | 0.427 |
| bm25 empty OR dense < 0.247 | 0.400 | 0.106 | 0.706 | 0.294 |

### What this says

**Dense retrieval can abstain, at a price that has to be chosen deliberately.**
Reaching 73% abstention costs 25% false-abstention and drops hit@3 from 0.788
to 0.600 — nearly 19 points of retrieval quality to avoid 11 of 15 bad answers.

**The cheapest useful rule is already free.** BM25 returning nothing catches a
third of out-of-catalog queries at a 5.9% false-abstain cost, and beats a
dense threshold tuned to the same false-abstain budget (0.333 vs 0.200). A
lexical retriever's silence is a better "we don't stock that" signal than a
dense retriever's low confidence.

**The operating point is a product decision, not a tuning exercise**, which is
why this is reported as a curve. For a sales agent the asymmetry is steep: a
false abstention loses a sale, a false promise loses a customer. That argues
for the conservative combined rule (0.400 / 0.106) over the Youden optimum.

**This is a retrieval-layer mitigation, not a fix.** Even at best-J, 27% of
out-of-catalog queries still return confident products. The Stage 3 grounding
eval — does the agent actually say it does not stock something when retrieval
comes back weak — remains the load-bearing measurement.

### Cross-project note

This diagnosis may apply elsewhere. A sibling project (Enterprise AI Support
platform) reports `abstention_rate: 0.0` alongside a README claiming the system
abstains. If that system retrieves with dense vectors and no similarity floor,
the mechanism measured here is the likely cause: cosine similarity over a fixed
corpus always returns k results, so an abstention rate of exactly zero is the
expected outcome rather than an anomaly.

**Not verified** — that repository was not inspected while writing this. It is
a hypothesis worth checking there, not a finding of this eval.

---

## Not yet measured

- Intent classification (keyword baseline vs embedding classifier)
- Latency (p50/p95/p99, per stage, by message type)
- Grounding (refusal rate, hallucinated-spec rate, false-refusal rate)
- Cross-lingual retrieval (Sinhala / Tamil, native script and romanised)
- Permission-tiered actions (unauthorised-action rate under adversarial input)
- Image → SKU retrieval

No figures for these exist anywhere in this repository.

## Known limitations

- **Sample size.** 85 in-catalog queries, 15–25 per category. This is enough to
  separate dense from bm25 (p = 0.001) and hybrid from dense on spec-constrained
  queries (p = 0.008), and not enough for the semantic finding (p = 0.125).
- **One catalog, one seed.** All numbers are against a single 200-SKU synthetic
  catalog. Nothing here has been tested for sensitivity to catalog size, and
  finding 5 is explicitly a small-corpus result.
- **One embedding model.** `all-MiniLM-L6-v2` only. A stronger model could
  change the dense/hybrid balance in either direction.
- **Single annotator.** Gold sets were defined by one person via predicates.
  They are auditable (each query carries its `gold_rule`) but not
  independently validated.
