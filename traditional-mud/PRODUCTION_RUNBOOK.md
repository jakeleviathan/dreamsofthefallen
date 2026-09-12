# Dreams of the Fallen — Production Runbook

This is the minimum operator checklist for moving the Telnet MUD from development into a closed alpha and then a wider public service.

## What the server now protects automatically

- The live SQLite database is checked with `PRAGMA integrity_check` before the server begins serving players.
- A validated SQLite online backup is made on startup, every 30 minutes by default, and again during a clean shutdown.
- Backups are written through a temporary file, integrity-checked, then atomically renamed into place.
- The most recent 48 backups are retained by default.
- Only one authenticated connection may own an account at a time. A newly authenticated connection safely supersedes an older one and stops its combat before the old socket closes.
- Session lifecycle and completed combat samples are recorded for alpha diagnostics.
- Item integrity audits are read-only. They flag unknown item keys, impossible quantities, missing equipped inventory, foreign-key failures, and serialized-fashion provenance mismatches; they never delete or rewrite player possessions automatically.
- Major runtime/operator activity goes to the rotating Dreams log and the production audit tables.

## Recommended environment

Set these values in the service environment rather than editing Python files:

```text
MUD_DB_PATH=/absolute/path/to/data/mud.db
MUD_BACKUP_DIR=/absolute/path/to/backups
MUD_BACKUP_INTERVAL_MINUTES=30
MUD_BACKUP_RETAIN=48
MUD_BACKUP_ON_START=1
MUD_BACKUP_ON_SHUTDOWN=1
MUD_LOG_DIR=/absolute/path/to/logs
MUD_LOG_LEVEL=INFO
MUD_LOG_MAX_BYTES=5242880
MUD_LOG_FILES=5
MUD_OWNER_ACCOUNT=<owner account name>
```

Do **not** set `MUD_ALLOW_CORRUPT_DB=1` during ordinary operation. That switch exists only as an emergency recovery escape hatch when an operator has already copied the broken database and understands the risk.

## Closed alpha gate

To restrict the server to invited accounts, set a comma-separated allowlist:

```text
MUD_ALPHA_ALLOWLIST=Jake,TesterOne,TesterTwo,TesterThree
```

When the variable is empty or absent, the gate is disabled. The configured `MUD_OWNER_ACCOUNT` is always allowed even if it is not explicitly included.

The gate intentionally happens after password verification. It is an invitation gate, not a replacement for authentication.

## Staff production commands

An ADMIN or OWNER must first use `STAFF ON`.

- `STAFF HEALTH` — database integrity, item audit, backup status, active sessions, alpha status, and a 24-hour combat sample.
- `STAFF BACKUP` — take and validate a backup immediately while the server remains online.
- `STAFF ITEM AUDIT` — detailed read-only inventory/provenance invariant scan.
- `STAFF COMBAT [hours]` — completed-fight count, victory/death counts, average duration, and average character level.
- `STAFF SESSIONS` — currently authenticated account/character sessions.
- `STAFF ALPHA` — whether the invitation gate is enabled and how many account names are configured.

Existing staff actions remain separately audited and confirmation-gated where disruptive.

## Before inviting the first outside alpha players

1. Put the database, backups, and logs on persistent storage. Do not run the production service with its only database inside an ephemeral container filesystem.
2. Start the server once with an empty or copied development database and verify `STAFF HEALTH` reports database integrity `OK`.
3. Run `STAFF BACKUP`, stop the server, and confirm the backup file survives independently of the live database.
4. Copy a backup to a throwaway location and boot a test process against that copy using `MUD_DB_PATH`. A backup that has never been restored is not yet a proven backup process.
5. Enable `MUD_ALPHA_ALLOWLIST` and confirm an invited account can enter while an uninvited account receives the closed-alpha message.
6. Log into the same invited account from two clients. The newer login should take ownership and the old connection should close without duplicating the character.
7. Run `STAFF ITEM AUDIT` after deliberately exercising GIVE, TRADE, the Veyra exchange, fragrance consumption, style provenance, vault storage, crafting, party loot, and boss rewards.
8. Walk a fresh character through the complete first-session experience without developer knowledge. Use `HELP HERE`; record every point where the tester asks what to type next.

## Alpha observation targets

The production combat table exists to answer questions, not to dictate design automatically. During the first alpha, pay special attention to:

- time from account creation to entering the first real room;
- time from first combat command to first victory;
- early deaths and failed flee attempts;
- whether Sewer Rats and Small Imps feel instructional rather than grind-efficient;
- where players stop using class abilities and fall back to auto-attacking;
- which commands testers repeatedly search for with `COMMAND SEARCH` or ask staff about;
- where players abandon the homeland → Waymeet → early dungeon path;
- whether fashion, fragrance, keepsakes, board notes, parties, and recurring-world content are discovered naturally rather than only after being explained out of game.

Do not tune solely from averages. Read the actual sessions, talk to testers, and use metrics to find places worth watching.

## Backup recovery outline

1. Stop the MUD process.
2. Copy the damaged/current `mud.db` somewhere safe; never overwrite the only copy during investigation.
3. Choose a validated backup from `MUD_BACKUP_DIR`.
4. Copy that backup to the configured `MUD_DB_PATH`.
5. Start the service and run `STAFF HEALTH` and `STAFF ITEM AUDIT` before reopening access.
6. Record the recovery time and lost time window so alpha testers know exactly what was rolled back.

## Launch progression

Recommended sequence:

**private operator test → 5–10 person closed alpha → larger invite alpha → public beta**.

Move to the next stage only when backups have been restore-tested, duplicate-session behavior is proven, item audits stay clean under real trading, and first-time players can reach the shared world without live coaching from a developer.
