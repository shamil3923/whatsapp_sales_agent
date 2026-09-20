# Changelog

All notable changes to this project, one entry per stage of the upgrade from a
working demo to a measured system. Each entry says what changed and what — if
anything — it lets us measure.

## Unreleased

### Added — Stage 2: real retrieval

- `scripts/generate_catalog.py` builds `data/catalog/products.jsonl`: 200 SKUs
  across laptops, phones, tablets, accessories and software, seeded so the
  catalog is identical on every run and eval numbers stay comparable.
  Internally coherent by design — model lines are bound to the tiers they
  actually ship in, Apple lines only get Apple silicon, names are unique, and
  price is composed from a tier base plus component premiums so it tracks the
  specs. An early draft failed all four and would have made spec-constrained
  retrieval labels meaningless.
- `src/catalog.py`: SQLite catalog storage plus hybrid BM25 + dense retrieval
  fused with reciprocal rank fusion. Mode and weights are configurable so
  Stage 3 can report dense-only against hybrid rather than assume.
- `scripts/build_index.py`: idempotent indexing. Each embedding stores a hash
  of its source text, so a re-run embeds only what changed and does no model
  work when nothing has.
- `src/catalog_tools.py`: `search_products`, `get_product`, `check_stock`,
  returning JSON so prices and stock stay exact.
- `PRODUCT_CATALOG` is gone from the system prompt, which now carries
  grounding rules instead: state only what appears in a tool result, say we do
  not stock something when retrieval is empty, never invent a SKU.

**What this measures:** nothing yet — Stage 3 is what turns this into numbers.
What it makes measurable is grounding: with no product data in the prompt, any
product claim that is not in a tool result is invented by construction.

Verified end to end: "gaming laptop with an RTX 4080 under $2500" returns four
RTX 4080 machines at $2109.99–$2480.00; "washing machine" returns zero results.

### Security — webhook signature verification

- `POST /webhook` now verifies Meta's `X-Hub-Signature-256` header: HMAC-SHA256
  over the **raw** request body, keyed on `WHATSAPP_APP_SECRET`, compared with
  `hmac.compare_digest`. Previously only the `GET` verify-token handshake
  existed, so anyone who learned the deployment URL could post fabricated
  messages and spend model budget.
- Rejection happens before any parsing or model call, so a forged request costs
  nothing. `tests/test_webhook_security.py` asserts exactly that: on a bad
  signature, `process_message` and `send_message` are never called.
- Covered: valid signature, tampered body, wrong secret, missing header,
  malformed header, and a replayed signature from a different payload.
- Verification is enforced only while `WHATSAPP_APP_SECRET` is set. Unset, the
  endpoint warns on every request and accepts — existing deployments keep
  working, but insecurely, and the warning says so.

## Stage 1 — Truth and foundation

### Fixed — documentation that did not match the code

- Removed two features the README advertised but the code does not have:
  "Product Catalog: Comprehensive product database" (there is no database and no
  retrieval; product knowledge is four lines inside the system prompt) and
  "Multi-Language Support" (not implemented anywhere).
- Reworded "Secure Webhook" to "Webhook Verification": only Meta's
  `hub.verify_token` handshake on `GET /webhook` is implemented. There is no
  `X-Hub-Signature-256` check on `POST /webhook`.
- Added a "Not implemented" section to the README listing these gaps explicitly.
- Fixed Quick Start, which told the reader to clone
  `shamil3923/ERP_Recommendation_Widget-` and `cd Task_02`. The same wrong repo
  and directory appeared in `docs/SETUP_GUIDE.md`, `docs/DEPLOYMENT.md` and the
  URLs in `setup.py`; all were corrected to this repository.
- Stated the real supported Python versions (3.11 / 3.12) instead of 3.8+.

### Fixed — a test suite that was not green to begin with

The plan assumed the 36 existing tests passed. Measured on the unmodified
`HEAD` (`6bd9f8b`), they did not: **4 failed, 32 passed**. Each was test/code
drift from the "Memory Integration" commit, not a real defect, except the
first:

- `/send-message` returned `{"status": "..."}`, but both `docs/API_REFERENCE.md`
  and the test expect `{"success": true, "message": "..."}`. Two independent
  sources agreed against the code, so the **endpoint** was fixed, not the test.
- `test_bot_initialization` asserted `bot.user_sessions == {}`; that attribute
  was replaced by `bot.memory`. Test updated.
- `test_complete_whatsapp_workflow` asserted the prompt contains
  `"WhatsApp Message"`; the prompt header is
  `[WhatsApp Sales Agent - Context-Aware Response]`. Test updated.
- `test_currency_api_timeout_handling` asserted `'Error' in result`, but a
  timeout is reported as `"Network error"`. Test now matches case-insensitively.

Three further defects surfaced while making the suite reliable:

- `test_concurrent_message_processing` called `mock.patch` **inside** each of
  five threads. `patch` swaps a module global, so one thread stopping its patch
  un-mocked the others mid-flight and they called the real model: the test hit
  the network, spent ~6s in tenacity backoff, and populated Streamlit's
  `@st.cache_resource`, which then made `test_get_sales_agent_creation` fail
  depending on ordering. The patch is now installed once around all threads.
  Suite runtime dropped from 7.4s to 0.9s.
- `test_environment_variables_loaded` reloaded the module inside a
  `patch.dict` and never reloaded it back, so `VERIFY_TOKEN` stayed
  `'test_verify'` and broke `test_webhook_verification` whenever that class ran
  first. It now restores the module on cleanup.
- `tests/run_tests.py` discovered tests by bare module name while `src/` was on
  `sys.path`. `src/` contains stale dev scripts named `test_*.py` that shadowed
  the real modules — and `src/test_whatsapp_integration.py` imports a
  `twilio_whatsapp_integration` module that does not exist in this repository,
  so the documented `python tests/run_tests.py` command aborted. Discovery now
  passes `top_level_dir` so modules import as `tests.test_*`.

**After:** 65 passed, 0 failed (36 existing + 29 new), under both
`python -m pytest tests/` and `python tests/run_tests.py`.

### Added — CI

- `.github/workflows/ci.yml` runs `python -m pytest tests/` on every push and
  pull request, against Python 3.11 and 3.12. Status badge added to the README.
- `tests/conftest.py` points each run at a temporary SQLite database and
  telemetry log, so the suite neither reads nor writes the repository's `data/`
  directory.

### Added — per-turn telemetry

- `src/telemetry.py`: a `timed(stage, ctx)` context manager and `log_turn(ctx)`
  that emits exactly one JSON line per conversation turn.
- `WhatsAppBot.process_message` is instrumented with the stages `classify`,
  `retrieve`, `llm` and `tools`; `send` is measured in `send_message` and lands
  on the same line, because the webhook opens one turn spanning both.
- Each line carries: turn id, salted phone hash (never the raw number), message
  type, per-stage milliseconds, total milliseconds, input/output token counts,
  and an estimated cost.

**What this measures:** where a turn spends its time, and what it costs. Cost is
an estimate — reported token counts multiplied by the list prices in
`MODEL_PRICE_IN_PER_MTOK` / `MODEL_PRICE_OUT_PER_MTOK` — not a billed amount.
`tools` time is nested inside `llm`, not additional to it, and is omitted
entirely when phidata does not report it rather than being guessed at.

### Changed — conversation storage moved to SQLite

- `ConversationMemory` now stores users and messages in SQLite (`data/agent.db`,
  overridable with `AGENT_DB_PATH`) instead of one JSON file per user under
  `data/conversations/`. The public interface is unchanged.
- This fixes a real data-loss bug. The old `_save_session` rewrote the whole
  file from an in-process cache on every message, so two messages arriving
  concurrently for the same user each wrote the state they had read and one was
  lost. Writes are now single SQL statements in one transaction, and
  `total_interactions` is incremented in SQL rather than in Python.

  **Measured**, 20 concurrent writers × 10 messages to one user:

  | Store | Messages recorded | Lost |
  |-------|-------------------|------|
  | JSON files (before) | 10 / 200 | 95% |
  | SQLite (after) | 200 / 200 | 0% |

  The JSON store additionally left behind truncated, unparseable files — its
  own loader raised `JSONDecodeError` on sessions caught mid-write. This is a
  synthetic worst case, not observed production traffic; it is reproduced by
  `tests/test_conversation_memory.py::test_concurrent_writes_are_not_lost`.
- `add_user_interest` appends and de-duplicates in a single `UPDATE`, for the
  same reason.
- `scripts/migrate_json_to_sqlite.py` imports the existing
  `data/conversations/*.json` files. It is idempotent: user rows are merged and
  messages already present are skipped, so re-running it neither duplicates nor
  loses history.
