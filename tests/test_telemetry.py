"""
Tests for per-turn telemetry.

The properties that matter: exactly one line per turn, a full stage breakdown,
and no raw phone number anywhere in the output.
"""
import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import telemetry


class TelemetryTestCase(unittest.TestCase):
    """Sends telemetry to a scratch file for the duration of each test."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="telemetry-test-")
        self.log_file = os.path.join(self.tmp_dir, "turns.jsonl")
        self._env = patch.dict(os.environ, {
            "TELEMETRY_LOG_PATH": self.log_file,
            "TELEMETRY_ENABLED": "1",
            "TELEMETRY_PHONE_SALT": "test-salt",
        })
        self._env.start()
        telemetry.clear_current_turn()

    def tearDown(self):
        self._env.stop()
        telemetry.clear_current_turn()

    def read_lines(self):
        if not os.path.exists(self.log_file):
            return []
        with open(self.log_file, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]


class TestPhoneHashing(TelemetryTestCase):

    def test_hash_is_stable_and_opaque(self):
        first = telemetry.hash_phone("+15551234567")
        second = telemetry.hash_phone("+15551234567")

        self.assertEqual(first, second)
        self.assertEqual(len(first), 16)
        self.assertNotIn("15551234567", first)

    def test_different_numbers_hash_differently(self):
        self.assertNotEqual(
            telemetry.hash_phone("+15551234567"),
            telemetry.hash_phone("+15551234568"),
        )

    def test_salt_changes_the_hash(self):
        unsalted = telemetry.hash_phone("+15551234567")
        with patch.dict(os.environ, {"TELEMETRY_PHONE_SALT": "another-salt"}):
            self.assertNotEqual(unsalted, telemetry.hash_phone("+15551234567"))


class TestTimedStages(TelemetryTestCase):

    def test_stage_durations_are_recorded(self):
        ctx = telemetry.new_turn("+15551234567")

        with telemetry.timed("classify", ctx):
            pass
        with telemetry.timed("llm", ctx):
            pass

        self.assertIn("classify", ctx.stages_ms)
        self.assertIn("llm", ctx.stages_ms)
        self.assertGreaterEqual(ctx.stages_ms["classify"], 0.0)

    def test_repeated_stage_accumulates(self):
        ctx = telemetry.new_turn("+15551234567")

        with telemetry.timed("send", ctx):
            pass
        first = ctx.stages_ms["send"]
        with telemetry.timed("send", ctx):
            pass

        self.assertGreaterEqual(ctx.stages_ms["send"], first)

    def test_stage_is_recorded_even_when_the_body_raises(self):
        ctx = telemetry.new_turn("+15551234567")

        with self.assertRaises(ValueError):
            with telemetry.timed("llm", ctx):
                raise ValueError("boom")

        self.assertIn("llm", ctx.stages_ms)

    def test_timed_tolerates_no_context(self):
        with telemetry.timed("llm", None):
            pass  # must not raise


class TestLogTurn(TelemetryTestCase):

    def test_one_line_per_turn_with_required_fields(self):
        ctx = telemetry.new_turn("+15551234567", "currency_conversion")
        with telemetry.timed("classify", ctx):
            time.sleep(0.005)
        ctx.tokens_in, ctx.tokens_out = 1000, 500

        telemetry.log_turn(ctx)

        lines = self.read_lines()
        self.assertEqual(len(lines), 1)
        line = lines[0]
        for field in ("ts", "turn_id", "phone_hash", "message_type",
                      "stages_ms", "total_ms", "tokens_in", "tokens_out",
                      "cost_usd", "ok"):
            self.assertIn(field, line)
        self.assertEqual(line["message_type"], "currency_conversion")
        self.assertGreater(line["total_ms"], 0)

    def test_raw_phone_number_is_never_written(self):
        ctx = telemetry.new_turn("+15551234567")
        telemetry.log_turn(ctx)

        with open(self.log_file, encoding="utf-8") as handle:
            contents = handle.read()

        self.assertNotIn("15551234567", contents)
        self.assertIn(telemetry.hash_phone("+15551234567"), contents)

    def test_cost_is_estimated_from_token_counts(self):
        with patch.dict(os.environ, {"MODEL_PRICE_IN_PER_MTOK": "0.10",
                                     "MODEL_PRICE_OUT_PER_MTOK": "0.40"}):
            # 1M in at $0.10 plus 1M out at $0.40.
            self.assertAlmostEqual(
                telemetry.estimate_cost_usd(1_000_000, 1_000_000), 0.50)
            self.assertEqual(telemetry.estimate_cost_usd(0, 0), 0.0)

    def test_prices_are_configurable(self):
        with patch.dict(os.environ, {"MODEL_PRICE_IN_PER_MTOK": "1.0",
                                     "MODEL_PRICE_OUT_PER_MTOK": "2.0"}):
            self.assertAlmostEqual(
                telemetry.estimate_cost_usd(1_000_000, 1_000_000), 3.0)

    def test_disabled_telemetry_writes_nothing(self):
        with patch.dict(os.environ, {"TELEMETRY_ENABLED": "0"}):
            telemetry.log_turn(telemetry.new_turn("+15551234567"))

        self.assertEqual(self.read_lines(), [])

    def test_read_turns_round_trips(self):
        telemetry.log_turn(telemetry.new_turn("+15551234567", "greeting"))
        telemetry.log_turn(telemetry.new_turn("+15559999999", "support"))

        turns = telemetry.read_turns(self.log_file)

        self.assertEqual([t["message_type"] for t in turns],
                         ["greeting", "support"])


class TestCurrentTurn(TelemetryTestCase):

    def test_begin_and_clear(self):
        self.assertIsNone(telemetry.current_turn())

        ctx = telemetry.begin_turn("+15551234567")
        self.assertIs(telemetry.current_turn(), ctx)

        telemetry.clear_current_turn()
        self.assertIsNone(telemetry.current_turn())


class TestUsageExtraction(TelemetryTestCase):

    def test_reads_phidata_style_metrics(self):
        class FakeResponse:
            metrics = {"input_tokens": [120, 80], "output_tokens": [40]}
            model = "gemini-2.0-flash-exp"

        ctx = telemetry.new_turn("+15551234567")
        telemetry.record_usage(ctx, FakeResponse())

        self.assertEqual(ctx.tokens_in, 200)
        self.assertEqual(ctx.tokens_out, 40)
        self.assertEqual(ctx.model, "gemini-2.0-flash-exp")

    def test_unknown_response_shape_leaves_counts_at_zero(self):
        ctx = telemetry.new_turn("+15551234567")
        telemetry.record_usage(ctx, object())

        self.assertEqual(ctx.tokens_in, 0)
        self.assertEqual(ctx.tokens_out, 0)

    def test_tool_time_is_recorded_when_reported(self):
        class FakeResponse:
            tools = [{"tool_name": "convert_currency", "metrics": {"time": 0.25}},
                     {"tool_name": "duckduckgo_search", "metrics": {"time": 0.5}}]

        ctx = telemetry.new_turn("+15551234567")
        telemetry.record_tool_time(ctx, FakeResponse())

        self.assertAlmostEqual(ctx.stages_ms["tools"], 750.0)
        self.assertEqual(ctx.extra["tool_calls"], 2)

    def test_tool_stage_is_absent_when_not_reported(self):
        class FakeResponse:
            tools = []

        ctx = telemetry.new_turn("+15551234567")
        telemetry.record_tool_time(ctx, FakeResponse())

        self.assertNotIn("tools", ctx.stages_ms)


if __name__ == '__main__':
    unittest.main(verbosity=2)
