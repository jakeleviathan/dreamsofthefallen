# Dreams of the Fallen - Production Runbook

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
DREAMS_DISCORD_APPLICATION_ID=<Discord application snowflake>
DREAMS_DISCORD_INVITE_URL=https://discord.gg/<invite-code>
DOTF_VOTE_REWARDS_ENABLED=0
MUDVERSE_LISTING_ID=606
MUDVERSE_API_KEY=<server-side API key from MUDVerse>
MUDVERSE_VOTE_URL=https://www.mudverse.com/vote/606
```

## MUDVerse vote rewards

The vote-reward integration is deliberately shipped behind a feature flag. Leave `DOTF_VOTE_REWARDS_ENABLED=0` until the MUDVerse API key is present and an operator has verified a manual sync.

MUDVerse's API is read-only. Dreams reads listing 606's current monthly vote total and never submits a vote on a player's behalf. A player must type `VOTE` before visiting MUDVerse; that snapshots the aggregate count and opens one two-hour account-wide pending claim. New vote-count increments are converted into immutable local events and matched FIFO to pending claims. Because MUDVerse exposes an aggregate count rather than voter identity, the game is explicit about that limitation in the claim UI.

The daily reward is:

- 1 Echo of Favour on the account;
- 6 Sparks on the character that armed the claim;
- 5 percent of that character level's XP requirement, capped at 250 XP.

The account reward cooldown is 24 hours. Streaks use a forgiving 54-hour continuation window. Echoes purchase account-wide presentation unlocks only. Titles, auras, and sigils have no combat stats and do not occupy equipment or fashion slots.

Before enabling rewards:

1. Sign in to MUDVerse, create an API key from its API account tab, and store it only as `MUDVERSE_API_KEY` in the service environment.
2. Restart with `DOTF_VOTE_REWARDS_ENABLED=0` and use `VOTE ADMIN STATUS` while on staff duty to confirm schema health and configuration.
3. Temporarily enable the flag, restart, and run `VOTE ADMIN SYNC`. Confirm the displayed count agrees with the public listing.
4. Arm a real test claim with `VOTE`, cast one legitimate vote yourself, and use `VOTE CLAIM`. Confirm exactly one local event and exactly one reward are recorded.
5. Check `VOTE ADMIN HISTORY` and the account's Echo balance before opening the feature to players.

Staff inspection commands are `VOTE ADMIN STATUS`, `PENDING`, `HISTORY [n]`, `ACCOUNT <account>`, and `SYNC`. ADMIN and OWNER may use audited manual grants when a legitimate reward needs correction. Every manual grant requires a written reason.

## Discord Rich Presence

Dreams implements Mudlet's `External.Discord` GMCP protocol directly on the server. Presence is dynamic and spoiler-conscious: it reports level/race/class, public room and region, combat state, crafting activity, party size, and session elapsed time, while hidden/secret room tags collapse to deliberately vague wording.

Create one Discord application for **Dreams of the Fallen**, put its numeric application ID in `DREAMS_DISCORD_APPLICATION_ID`, and optionally put the official community invite in `DREAMS_DISCORD_INVITE_URL`.

For the best branded presence, configure these lowercase Rich Presence assets in that Discord application:

- `server-icon` - Dreams of the Fallen logo; this is the universal fallback.
- `class-brute`
- `class-wizard`
- `class-necromancer`
- `class-druid`
- `class-priest`

The server replies to `External.Discord.Hello` with `External.Discord.Info` and a complete `External.Discord.Status`, then refreshes status only when meaningful presence changes. Discord usernames from the Hello packet are never retained or used for a directory.

Mudlet keeps Discord Rich Presence **player opt-in for privacy**. The game must not try to force-enable that client preference. Once a player enables Discord for the profile, the server-side integration requires no scripts or manual status configuration.

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

- `STAFF HEALTH` - database integrity, item audit, backup status, active sessions, alpha status, and a 24-hour combat sample.
- `STAFF BACKUP` - take and validate a backup immediately while the server remains online.
- `STAFF ITEM AUDIT` - detailed read-only inventory/provenance invariant scan.
- `STAFF COMBAT [hours]` - completed-fight count, victory/death counts, average duration, and average character level.
- `STAFF SESSIONS` - currently authenticated account/character sessions.
- `STAFF ALPHA` - whether the invitation gate is enabled and how many account names are configured.

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
