"""Account-linked Lanternkeeper persistence and in-game Wisp command adapter."""
import json
from datetime import datetime, timezone
from mud.lanternkeeper_wisp import Lanternkeeper, LanternWisp

def ensure_schema(database):
    with database.connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS lanternkeeper_memberships (
          account_id INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
          stripe_customer_id TEXT UNIQUE, stripe_subscription_id TEXT UNIQUE,
          stripe_status TEXT NOT NULL DEFAULT 'inactive',
          current_period_end TEXT);
        CREATE TABLE IF NOT EXISTS lantern_wisps (
          character_id INTEGER PRIMARY KEY REFERENCES characters(id) ON DELETE CASCADE,
          color TEXT NOT NULL DEFAULT 'violet',
          appearance TEXT NOT NULL DEFAULT 'lantern',
          name TEXT NOT NULL DEFAULT '',
          summoned INTEGER NOT NULL DEFAULT 0,
          unlocked_appearances TEXT NOT NULL DEFAULT '["lantern"]');
        CREATE TABLE IF NOT EXISTS lanternkeeper_stripe_events (
          event_id TEXT PRIMARY KEY, received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        """)

def membership(database, account_id):
    ensure_schema(database)
    with database.connect() as db:
        row = db.execute("SELECT * FROM lanternkeeper_memberships WHERE account_id=?", (account_id,)).fetchone()
    if not row:
        return Lanternkeeper()
    end = datetime.fromisoformat(row["current_period_end"]) if row["current_period_end"] else None
    return Lanternkeeper(row["stripe_customer_id"] or "", row["stripe_subscription_id"] or "",
                         row["stripe_status"], end)

def load_wisp(database, character_id):
    ensure_schema(database)
    with database.connect() as db:
        row = db.execute("SELECT * FROM lantern_wisps WHERE character_id=?", (character_id,)).fetchone()
    if not row:
        return LanternWisp()
    return LanternWisp(color=row["color"], appearance=row["appearance"], name=row["name"],
                       summoned=bool(row["summoned"]),
                       unlocked_appearances=set(json.loads(row["unlocked_appearances"])))

def save_wisp(database, character_id, wisp):
    ensure_schema(database)
    with database.connect() as db:
        db.execute("""INSERT INTO lantern_wisps
          (character_id,color,appearance,name,summoned,unlocked_appearances)
          VALUES (?,?,?,?,?,?)
          ON CONFLICT(character_id) DO UPDATE SET
          color=excluded.color,appearance=excluded.appearance,name=excluded.name,
          summoned=excluded.summoned,unlocked_appearances=excluded.unlocked_appearances""",
          (character_id,wisp.color,wisp.appearance,wisp.name,int(wisp.summoned),
           json.dumps(sorted(wisp.unlocked_appearances))))

def visible_wisp(database, character, now=None):
    wisp = load_wisp(database, character.id)
    return wisp if wisp.visible(membership(database, character.account_id), True, now) else None

def room_wisp_lines(database, room_key, online_character_ids=None):
    """Query authoritative character positions; do not create combat targets."""
    ensure_schema(database)
    with database.connect() as db:
        rows = db.execute("""SELECT c.id,c.name,c.account_id FROM characters c
          JOIN lantern_wisps w ON w.character_id=c.id
          WHERE c.current_room=? AND w.summoned=1""", (room_key,)).fetchall()
    lines=[]
    for row in rows:
        if online_character_ids is not None and row["id"] not in online_character_ids:
            continue
        wisp=visible_wisp(database, type("Character", (), dict(row))())
        if wisp:
            lines.append(f"{row['name']}'s wisp drifts nearby, glowing {wisp.color}.")
    return lines

def lanternkeeper_information(member, ready=False):
    """Player-facing membership overview; no account or payment secrets."""
    status = "ACTIVE" if member.active() else member.stripe_status.upper()
    if status in ("INACTIVE", ""):
        status = "NOT SUBSCRIBED"
    return (
        "\r\n== LANTERNKEEPER | KEEP A LIGHT BURNING ==\r\n"
        "Help sustain Astralis and receive a personal Lantern Wisp.\r\n"
        "Membership: $4.99 USD each month. Cancel anytime.\r\n"
        "This is cosmetic only: no combat bonuses, XP boosts, or advantages.\r\n"
        "Your Wisp can be named and customized with colors and appearances.\r\n"
        "Your support helps Dreams of the Fallen grow.\r\n"
        f"Account status: {status}.\r\n"
        "Commands: LANTERNKEEPER STATUS | LANTERNKEEPER SUBSCRIBE | LANTERNKEEPER MANAGE\r\n"
        "Wisp commands: WISP STATUS | SUMMON | DISMISS | COLOR | NAME | APPEARANCE\r\n"
        + ("The subscription service is not open yet.\r\n" if not ready else "")
        + "Payment and cancellation are completed securely in your browser, never in telnet.\r\n"
    )


def lanternkeeper_status(member):
    if member.active():
        end = member.current_period_end
        until = end.strftime("%Y-%m-%d") if end else "unknown"
        return (
            "Lanternkeeper: ACTIVE. Your cosmetic Lantern Wisp is available.\r\n"
            f"Current paid period ends: {until} (UTC).\r\n"
            "Use WISP SUMMON and LANTERNKEEPER MANAGE for billing.\r\n"
        )
    if member.stripe_status in ("active", "trialing"):
        return (
            "Lanternkeeper: billing is active, but the paid period is not yet confirmed.\r\n"
            "Your Wisp is dormant until the billing period is verified.\r\n"
            "Use LANTERNKEEPER MANAGE if this does not resolve.\r\n"
        )
    if member.stripe_status not in ("", "inactive"):
        return (
            f"Lanternkeeper: {member.stripe_status.upper().replace('_', ' ')}.\r\n"
            "The Lantern Wisp is dormant unless membership is active.\r\n"
            "Use LANTERNKEEPER MANAGE to review billing, or SUBSCRIBE if canceled.\r\n"
        )
    return (
        "Lanternkeeper: NOT SUBSCRIBED.\r\n"
        "Use LANTERNKEEPER INFO for benefits or SUBSCRIBE to join.\r\n"
    )


def _lanternkeeper_billing_action(database, member, account_id, action):
    from mud.lanternkeeper_links import issue_action_link, links_enabled

    if not links_enabled():
        return "Lanternkeeper billing is not open yet. Please check again later.\r\n"
    if action == "subscribe" and member.stripe_subscription_id and member.stripe_status in (
        "active", "trialing", "past_due", "unpaid", "incomplete", "paused"
    ):
        return "You already have a Lanternkeeper subscription. Use LANTERNKEEPER MANAGE.\r\n"
    if action == "manage" and not member.stripe_customer_id:
        return "No linked billing account yet. Use LANTERNKEEPER SUBSCRIBE first.\r\n"
    try:
        url = issue_action_link(database, account_id, action)
    except ValueError:
        return "Unable to prepare a billing link. Try again or contact game staff.\r\n"
    except (RuntimeError, OSError):
        return "Secure billing is temporarily unavailable. Please try again later.\r\n"
    purpose = "join Lanternkeeper" if action == "subscribe" else "manage your membership"
    return (
        f"Your private link to {purpose} (expires in 10 minutes):\r\n"
        f"{url}\r\n"
        "Open it in a browser. The HTTPS page confirms your game password "
        "before opening Stripe. Never enter payment details in the MUD.\r\n"
        "Treat this link like a password: do not share it.\r\n"
    )


def install_lanternkeeper_runtime(player_session_class):
    if getattr(player_session_class, "_lanternkeeper_installed", False):
        return
    previous = player_session_class.playing_prompt

    async def playing_prompt(self):
        if getattr(self, "character", None) is None:
            return await previous(self)

        async def replay(_prompt):
            return command

        command = await self.prompt("\r\n> ")
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return

        words = command.strip().split(maxsplit=2)
        if not words or words[0].lower() not in ("wisp", "lanternkeeper"):
            old_prompt = self.__dict__.get("prompt")
            had_prompt = "prompt" in self.__dict__
            self.prompt = replay
            try:
                return await previous(self)
            finally:
                if had_prompt:
                    self.prompt = old_prompt
                else:
                    self.__dict__.pop("prompt", None)

        character = self.character
        member = membership(self.database, character.account_id)
        action = words[1].lower() if len(words) > 1 else "info"
        arg = words[2] if len(words) > 2 else ""

        if words[0].lower() == "lanternkeeper":
            from mud.lanternkeeper_links import links_enabled
            if action in ("info", "about", "benefits"):
                message = lanternkeeper_information(member, links_enabled())
            elif action in ("status", "check"):
                message = lanternkeeper_status(member)
            elif action in ("subscribe", "join", "buy"):
                message = _lanternkeeper_billing_action(
                    self.database, member, character.account_id, "subscribe"
                )
            elif action in ("manage", "billing", "cancel", "payment"):
                message = _lanternkeeper_billing_action(
                    self.database, member, character.account_id, "manage"
                )
            else:
                message = (
                    "LANTERNKEEPER INFO | STATUS | SUBSCRIBE | MANAGE\r\n"
                    "Billing changes open securely in your browser.\r\n"
                )
        else:
            wisp = load_wisp(self.database, character.id)
            if action == "summon":
                message = wisp.summon(member)
            elif action == "dismiss":
                message = wisp.dismiss()
            elif action == "color":
                message = wisp.set_color(arg)
            elif action == "name":
                message = wisp.set_name(arg)
            elif action == "appearance":
                message = wisp.set_appearance(arg)
            elif action == "status" or action == "info":
                message = wisp.status(member)
            else:
                message = "WISP SUMMON | DISMISS | STATUS | COLOR <color> | NAME <name> | APPEARANCE <style>"
            save_wisp(self.database, character.id, wisp)
        await self.send(message + "\r\n")

    player_session_class.playing_prompt = playing_prompt
    player_session_class._lanternkeeper_installed = True
