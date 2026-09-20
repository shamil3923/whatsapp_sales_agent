"""
Tests for the SQLite-backed conversation memory.

The concurrency test is a regression test for real data loss: the previous
JSON-file implementation rewrote a user's whole session from an in-process
cache on every message, so simultaneous writers overwrote each other. Measured
on the same load as `test_concurrent_writes_are_not_lost`, that implementation
recorded 10 of 200 messages.
"""
import os
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from conversation_memory import ConversationMemory


class TestConversationMemory(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="memory-test-")
        self.db_path = os.path.join(self.tmp_dir, "agent.db")
        self.memory = ConversationMemory(db_path=self.db_path)

    def test_new_user_starts_empty(self):
        session = self.memory.get_or_create_session("+15550000001")

        self.assertEqual(session.user_profile.phone_number, "+15550000001")
        self.assertEqual(session.user_profile.preferred_currency, "USD")
        self.assertEqual(session.user_profile.interests, [])
        self.assertEqual(session.user_profile.total_interactions, 0)
        self.assertEqual(session.messages, [])

    def test_messages_round_trip(self):
        self.memory.add_message("+15550000002", "user", "Hello")
        self.memory.add_message(
            "+15550000002", "assistant", "Hi!", "greeting", {"detected": ["hi"]}
        )

        session = self.memory.get_or_create_session("+15550000002")

        self.assertEqual([m.role for m in session.messages], ["user", "assistant"])
        self.assertEqual(session.messages[1].content, "Hi!")
        self.assertEqual(session.messages[1].message_type, "greeting")
        self.assertEqual(session.messages[1].metadata, {"detected": ["hi"]})
        self.assertEqual(session.user_profile.total_interactions, 2)

    def test_state_survives_a_new_instance(self):
        self.memory.add_message("+15550000003", "user", "Remember me")
        self.memory.update_user_preferences("+15550000003", name="Sam",
                                            preferred_currency="EUR")

        reopened = ConversationMemory(db_path=self.db_path)
        session = reopened.get_or_create_session("+15550000003")

        self.assertEqual(session.user_profile.name, "Sam")
        self.assertEqual(session.user_profile.preferred_currency, "EUR")
        self.assertEqual(len(session.messages), 1)

    def test_interests_are_deduplicated_case_insensitively(self):
        self.memory.add_user_interest("+15550000004", "laptop")
        self.memory.add_user_interest("+15550000004", "LAPTOP")
        self.memory.add_user_interest("+15550000004", "phone")

        interests = self.memory.get_or_create_session(
            "+15550000004").user_profile.interests
        self.assertEqual(interests, ["laptop", "phone"])

    def test_message_history_is_capped(self):
        phone = "+15550000005"
        for i in range(self.memory.max_messages_per_session + 20):
            self.memory.add_message(phone, "user", f"message {i}")

        session = self.memory.get_or_create_session(phone)

        self.assertEqual(len(session.messages), self.memory.max_messages_per_session)
        # The oldest are dropped, not the newest.
        self.assertEqual(session.messages[-1].content, "message 69")
        self.assertEqual(session.user_profile.total_interactions, 70)

    def test_conversation_context_includes_profile_and_history(self):
        self.memory.update_user_preferences("+15550000006", name="Sam")
        self.memory.add_message("+15550000006", "user", "Show me laptops")

        context = self.memory.get_conversation_context("+15550000006")

        self.assertIn("Sam", context)
        self.assertIn("Show me laptops", context)
        self.assertIn("USER:", context)

    def test_conversation_context_for_new_user(self):
        context = self.memory.get_conversation_context("+15550000007")
        self.assertEqual(context, "This is a new conversation with the user.")

    def test_concurrent_writes_are_not_lost(self):
        """20 writers x 10 messages to one user must record all 200."""
        phone = "+15550000008"
        writers, per_writer = 20, 10

        def worker(index):
            memory = ConversationMemory(db_path=self.db_path)
            for j in range(per_writer):
                memory.add_message(phone, "user", f"w{index}-m{j}")

        threads = [threading.Thread(target=worker, args=(i,))
                   for i in range(writers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        session = ConversationMemory(db_path=self.db_path).get_or_create_session(phone)

        self.assertEqual(session.user_profile.total_interactions,
                         writers * per_writer)
        self.assertEqual(len(session.messages),
                         self.memory.max_messages_per_session)

    def test_concurrent_interest_writes_are_not_lost(self):
        phone = "+15550000009"

        def worker(index):
            ConversationMemory(db_path=self.db_path).add_user_interest(
                phone, f"interest-{index}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        interests = self.memory.get_or_create_session(phone).user_profile.interests
        self.assertEqual(len(interests), 20)

    def test_all_users_summary(self):
        self.memory.add_message("+15550000010", "user", "hi")
        self.memory.add_message("+15550000011", "user", "hello")

        summaries = self.memory.get_all_users_summary()
        phones = {s["phone_number"] for s in summaries}

        self.assertIn("+15550000010", phones)
        self.assertIn("+15550000011", phones)
        for summary in summaries:
            self.assertIn("total_messages", summary)
            self.assertIn("interests", summary)

    def test_cleanup_removes_only_old_sessions(self):
        self.memory.add_message("+15550000012", "user", "recent")
        self.memory.add_message("+15550000013", "user", "ancient")
        self.memory.update_user_preferences(
            "+15550000013", last_interaction="2020-01-01T00:00:00")

        self.memory.cleanup_old_sessions(days_old=30)

        phones = {s["phone_number"] for s in self.memory.get_all_users_summary()}
        self.assertIn("+15550000012", phones)
        self.assertNotIn("+15550000013", phones)


if __name__ == '__main__':
    unittest.main(verbosity=2)
