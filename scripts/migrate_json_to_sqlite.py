#!/usr/bin/env python3
"""
Import legacy per-user JSON sessions into the SQLite store.

The old ConversationMemory wrote one file per user under
``data/conversations/session_<number>.json``. This script reads those files and
inserts them into ``data/agent.db``.

It is idempotent: a message already present for the same user with the same
timestamp, role and content is skipped, and user rows are merged rather than
overwritten (the larger interaction count and the union of interests win), so
re-running it never duplicates or loses history.

    python scripts/migrate_json_to_sqlite.py
    python scripts/migrate_json_to_sqlite.py --source data/conversations \
        --db data/agent.db --dry-run
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from conversation_memory import DEFAULT_DB_PATH, connect, init_db  # noqa: E402


def normalise_phone(raw: str) -> str:
    """Legacy filenames stripped the leading '+'; the loader added it back."""
    digits = raw.replace("+", "").replace("-", "").replace(" ", "")
    return f"+{digits}"


def iter_session_files(source_dir: str):
    if not os.path.isdir(source_dir):
        return
    for filename in sorted(os.listdir(source_dir)):
        if filename.startswith("session_") and filename.endswith(".json"):
            yield os.path.join(source_dir, filename)


def migrate_file(conn, path: str, dry_run: bool) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    profile = data.get("user_profile") or {}
    raw_phone = profile.get("phone_number") or os.path.basename(path)[len("session_"):-len(".json")]
    phone = normalise_phone(str(raw_phone))

    created_at = data.get("created_at") or ""
    updated_at = data.get("updated_at") or created_at

    existing = conn.execute(
        "SELECT * FROM users WHERE phone_number = ?", (phone,)
    ).fetchone()

    incoming_interests = [i for i in (profile.get("interests") or []) if i]
    if existing:
        try:
            current_interests = json.loads(existing["interests"]) or []
        except (json.JSONDecodeError, TypeError):
            current_interests = []
        merged = list(current_interests)
        seen = {i.lower() for i in merged}
        for interest in incoming_interests:
            if interest.lower() not in seen:
                merged.append(interest)
                seen.add(interest.lower())
        user_values = (
            profile.get("name") or existing["name"],
            profile.get("preferred_currency") or existing["preferred_currency"] or "USD",
            json.dumps(merged),
            max(
                filter(None, [profile.get("last_interaction"), existing["last_interaction"]]),
                default=None,
            ),
            max(int(profile.get("total_interactions") or 0), existing["total_interactions"] or 0),
            data.get("session_summary") or existing["session_summary"],
            min(filter(None, [created_at, existing["created_at"]]), default=created_at),
            updated_at or existing["updated_at"],
            phone,
        )
        if not dry_run:
            conn.execute(
                "UPDATE users SET name = ?, preferred_currency = ?, interests = ?, "
                "last_interaction = ?, total_interactions = ?, session_summary = ?, "
                "created_at = ?, updated_at = ? WHERE phone_number = ?",
                user_values,
            )
        users_created = 0
    else:
        if not dry_run:
            conn.execute(
                "INSERT INTO users (phone_number, name, preferred_currency, interests, "
                "last_interaction, total_interactions, session_summary, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    phone,
                    profile.get("name"),
                    profile.get("preferred_currency") or "USD",
                    json.dumps(incoming_interests),
                    profile.get("last_interaction"),
                    int(profile.get("total_interactions") or 0),
                    data.get("session_summary"),
                    created_at,
                    updated_at,
                ),
            )
        users_created = 1

    inserted = 0
    skipped = 0
    for message in data.get("messages") or []:
        timestamp = message.get("timestamp")
        role = message.get("role")
        content = message.get("content")
        if not (timestamp and role and content is not None):
            skipped += 1
            continue

        already_there = conn.execute(
            "SELECT 1 FROM messages WHERE phone_number = ? AND timestamp = ? "
            "AND role = ? AND content = ? LIMIT 1",
            (phone, timestamp, role, content),
        ).fetchone()
        if already_there:
            skipped += 1
            continue

        if not dry_run:
            conn.execute(
                "INSERT INTO messages (phone_number, timestamp, role, content, "
                "message_type, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    phone,
                    timestamp,
                    role,
                    content,
                    message.get("message_type") or "text",
                    json.dumps(message.get("metadata") or {}, ensure_ascii=False),
                ),
            )
        inserted += 1

    return {
        "phone": phone,
        "users_created": users_created,
        "messages_inserted": inserted,
        "messages_skipped": skipped,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="data/conversations",
                        help="directory holding legacy session_*.json files")
    parser.add_argument("--db", default=os.getenv("AGENT_DB_PATH", DEFAULT_DB_PATH),
                        help="target SQLite database")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would be imported without writing")
    args = parser.parse_args()

    files = list(iter_session_files(args.source))
    if not files:
        print(f"No legacy sessions found in {args.source}/ — nothing to migrate.")
        return 0

    init_db(args.db)
    conn = connect(args.db)
    totals = {"users_created": 0, "messages_inserted": 0, "messages_skipped": 0}

    try:
        with conn:
            for path in files:
                try:
                    result = migrate_file(conn, path, args.dry_run)
                except (json.JSONDecodeError, OSError) as exc:
                    print(f"  !! {os.path.basename(path)}: could not read ({exc})")
                    continue
                for key in totals:
                    totals[key] += result[key]
                print(
                    f"  {os.path.basename(path)} -> {result['phone']}: "
                    f"{result['messages_inserted']} inserted, "
                    f"{result['messages_skipped']} already present"
                )
            if args.dry_run:
                conn.rollback()
    finally:
        conn.close()

    prefix = "[dry run] " if args.dry_run else ""
    print(
        f"\n{prefix}{len(files)} file(s) processed: "
        f"{totals['users_created']} new user(s), "
        f"{totals['messages_inserted']} message(s) imported, "
        f"{totals['messages_skipped']} already present."
    )
    if not args.dry_run:
        print(f"Database: {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
