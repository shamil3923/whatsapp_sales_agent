"""
Per-turn, per-stage telemetry for the WhatsApp Sales Agent.

One conversation turn produces exactly one JSON line containing a latency
breakdown per stage, token counts, and an estimated cost. Phone numbers are
never written out: only a salted hash is recorded.

Usage:

    ctx = new_turn(phone_number)
    with timed("classify", ctx):
        message_type, metadata = classify(message)
    ctx.message_type = message_type
    with timed("llm", ctx):
        response = call_model(prompt)
    record_usage(ctx, response)
    log_turn(ctx)

The module is deliberately dependency-free and never raises: telemetry must
not be able to break a user-facing turn.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Stages instrumented in WhatsAppBot.process_message, in execution order.
STAGES = ("classify", "retrieve", "llm", "tools", "send")

DEFAULT_LOG_PATH = os.path.join("data", "telemetry", "turns.jsonl")

# Published list prices in USD per 1M tokens. These are configuration inputs,
# not measurements: cost is *estimated* from token counts, never observed from
# a bill. Override per deployment with MODEL_PRICE_IN_PER_MTOK /
# MODEL_PRICE_OUT_PER_MTOK so the numbers stay honest as prices change.
# Source: Google Gemini API pricing for gemini-2.0-flash (text), checked
# 2026-09-17: $0.10 / 1M input tokens, $0.40 / 1M output tokens.
DEFAULT_PRICE_IN_PER_MTOK = 0.10
DEFAULT_PRICE_OUT_PER_MTOK = 0.40

_write_lock = threading.Lock()

# The turn currently being measured on this thread. Held here rather than on
# the bot so that instrumentation never changes a call signature: helpers deep
# in the call stack (send_message, tool wrappers) can find the open turn
# without it being threaded through every caller.
_current = threading.local()


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        logger.warning("Ignoring non-numeric %s=%r", name, raw)
        return default


def price_in_per_mtok() -> float:
    return _env_float("MODEL_PRICE_IN_PER_MTOK", DEFAULT_PRICE_IN_PER_MTOK)


def price_out_per_mtok() -> float:
    return _env_float("MODEL_PRICE_OUT_PER_MTOK", DEFAULT_PRICE_OUT_PER_MTOK)


def estimate_cost_usd(tokens_in: int, tokens_out: int) -> float:
    """Estimated USD cost of one turn from its token counts."""
    return (
        tokens_in * price_in_per_mtok() + tokens_out * price_out_per_mtok()
    ) / 1_000_000


def hash_phone(phone_number: str) -> str:
    """Return a stable, non-reversible id for a phone number.

    Salted with TELEMETRY_PHONE_SALT so that logs from different deployments
    cannot be correlated, and so a raw number cannot be recovered by hashing
    the (small) space of possible numbers.
    """
    salt = os.getenv("TELEMETRY_PHONE_SALT", "whatsapp-sales-agent")
    digest = hashlib.sha256(f"{salt}:{phone_number}".encode("utf-8")).hexdigest()
    return digest[:16]


@dataclass
class TurnContext:
    """Everything measured about a single conversation turn."""

    turn_id: str
    phone_hash: str
    message_type: str = "unknown"
    stages_ms: Dict[str, float] = field(default_factory=dict)
    total_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    model: Optional[str] = None
    ok: bool = True
    error: Optional[str] = None
    started_at: float = field(default_factory=time.perf_counter)
    started_iso: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def cost_usd(self) -> float:
        return estimate_cost_usd(self.tokens_in, self.tokens_out)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": self.started_iso,
            "turn_id": self.turn_id,
            "phone_hash": self.phone_hash,
            "message_type": self.message_type,
            "model": self.model,
            "stages_ms": {k: round(v, 2) for k, v in self.stages_ms.items()},
            "total_ms": round(self.total_ms, 2),
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": round(self.cost_usd, 8),
            "ok": self.ok,
            "error": self.error,
            **self.extra,
        }


def new_turn(phone_number: str, message_type: str = "unknown") -> TurnContext:
    """Start measuring a turn. Call once per inbound message."""
    return TurnContext(
        turn_id=uuid.uuid4().hex,
        phone_hash=hash_phone(phone_number),
        message_type=message_type,
    )


def begin_turn(phone_number: str, message_type: str = "unknown") -> TurnContext:
    """Start a turn and make it the current one for this thread."""
    ctx = new_turn(phone_number, message_type)
    _current.ctx = ctx
    return ctx


def current_turn() -> Optional[TurnContext]:
    """The turn open on this thread, or None if no turn is being measured."""
    return getattr(_current, "ctx", None)


def clear_current_turn() -> None:
    _current.ctx = None


@contextmanager
def timed(stage: str, ctx: Optional[TurnContext]):
    """Measure one stage and accumulate its duration onto ``ctx``.

    Time is recorded even when the body raises, so a failed turn still shows
    where it spent its time. ``ctx`` may be None, which makes instrumentation
    safe to leave in code paths that have no turn context.
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if ctx is not None:
            ctx.stages_ms[stage] = ctx.stages_ms.get(stage, 0.0) + elapsed_ms


def record_usage(ctx: Optional[TurnContext], response: Any) -> None:
    """Pull token counts off a model response, tolerating unknown shapes.

    phidata's RunResponse exposes ``metrics`` as a dict of lists (one entry per
    model call in the run). Anything we cannot read is left at zero rather than
    guessed at.
    """
    if ctx is None or response is None:
        return
    try:
        metrics = getattr(response, "metrics", None)
        if isinstance(metrics, dict):
            ctx.tokens_in += _sum_metric(metrics, ("input_tokens", "prompt_tokens"))
            ctx.tokens_out += _sum_metric(
                metrics, ("output_tokens", "completion_tokens")
            )
        model = getattr(response, "model", None)
        if isinstance(model, str) and model:
            ctx.model = model
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Could not read usage from response: %s", exc)


def record_tool_time(ctx: Optional[TurnContext], response: Any) -> None:
    """Attribute time spent in agent tool calls to the ``tools`` stage.

    Tool calls happen inside the agent's run loop, so this time is *nested
    inside* the ``llm`` stage rather than additional to it. phidata reports it
    per call on ``RunResponse.tools``; when that is unavailable the stage is
    left out entirely rather than being guessed at.
    """
    if ctx is None or response is None:
        return
    try:
        tools = getattr(response, "tools", None) or []
        total_ms = 0.0
        calls = 0
        for tool in tools:
            metrics = tool.get("metrics") if isinstance(tool, dict) else None
            seconds = (metrics or {}).get("time") if isinstance(metrics, dict) else None
            if isinstance(seconds, (int, float)):
                total_ms += seconds * 1000.0
                calls += 1
        if calls:
            ctx.stages_ms["tools"] = ctx.stages_ms.get("tools", 0.0) + total_ms
            ctx.extra["tool_calls"] = ctx.extra.get("tool_calls", 0) + calls
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Could not read tool metrics from response: %s", exc)


def _sum_metric(metrics: Dict[str, Any], keys: tuple) -> int:
    for key in keys:
        value = metrics.get(key)
        if isinstance(value, (list, tuple)):
            return int(sum(v for v in value if isinstance(v, (int, float))))
        if isinstance(value, (int, float)):
            return int(value)
    return 0


def log_path() -> str:
    return os.getenv("TELEMETRY_LOG_PATH", DEFAULT_LOG_PATH)


def log_turn(ctx: TurnContext) -> Dict[str, Any]:
    """Finalise and emit one JSON line for the turn. Returns the payload."""
    if not ctx.total_ms:
        ctx.total_ms = (time.perf_counter() - ctx.started_at) * 1000.0
    payload = ctx.to_dict()
    line = json.dumps(payload, ensure_ascii=False)

    if os.getenv("TELEMETRY_ENABLED", "1") not in ("0", "false", "False"):
        try:
            path = log_path()
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with _write_lock:
                with open(path, "a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Could not write telemetry line: %s", exc)

    logger.info("turn %s", line)
    return payload


def read_turns(path: Optional[str] = None) -> list:
    """Read back emitted turns. Used by the latency eval and /analytics."""
    target = path or log_path()
    turns = []
    if not os.path.exists(target):
        return turns
    with open(target, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                turns.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed telemetry line")
    return turns
