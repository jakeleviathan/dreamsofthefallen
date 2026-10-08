"""Lanternkeeper membership and cosmetic Lantern Wisp domain logic.

No payment credentials or client-supplied subscription flags are trusted here.
The server must supply membership state from verified Stripe webhook records.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import re

LANTERNKEEPER_PRICE_USD_CENTS = 499
WISP_COLORS = ("violet", "blue", "gold", "rose", "green", "silver", "white")
WISP_APPEARANCES = ("lantern", "ember", "starlight")


@dataclass
class Lanternkeeper:
    stripe_customer_id: str = ""
    stripe_subscription_id: str = ""
    stripe_status: str = "inactive"
    current_period_end: datetime | None = None

    def active(self, now=None):
        now = now or datetime.now(timezone.utc)
        if self.stripe_status not in ("active", "trialing"):
            return False
        if self.current_period_end is None:
            return False
        end = self.current_period_end
        if end.tzinfo is None:
            return False
        return now < end


@dataclass
class LanternWisp:
    color: str = "violet"
    appearance: str = "lantern"
    name: str = ""
    summoned: bool = False
    unlocked_appearances: set[str] = field(default_factory=lambda: {"lantern"})

    def label(self, owner_name):
        return f"{owner_name}'s wisp"

    def visible(self, membership: Lanternkeeper, online: bool, now=None):
        return online and self.summoned and membership.active(now)

    def summon(self, membership: Lanternkeeper, now=None):
        if not membership.active(now):
            self.summoned = False
            return "The Lantern Wisp is dormant. An active Lanternkeeper membership is required."
        self.summoned = True
        return "Your Lantern Wisp gathers into view."

    def dismiss(self):
        self.summoned = False
        return "Your Lantern Wisp fades from view."

    def set_color(self, color):
        color = color.strip().lower()
        if color not in WISP_COLORS:
            return "Available colors: " + ", ".join(WISP_COLORS) + "."
        self.color = color
        return f"Your Lantern Wisp glows {color}."

    def set_name(self, name):
        name = name.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z '-]{0,23}", name):
            return "Choose a name of 1-24 letters, spaces, apostrophes, or hyphens."
        self.name = name
        return f"Your Lantern Wisp answers to {name}."

    def set_appearance(self, appearance):
        appearance = appearance.strip().lower()
        if appearance not in self.unlocked_appearances:
            return "That Wisp appearance has not been unlocked."
        self.appearance = appearance
        return f"Your Lantern Wisp takes its {appearance} appearance."

    def unlock_appearance(self, appearance):
        if appearance not in WISP_APPEARANCES:
            raise ValueError("Unknown Wisp appearance")
        self.unlocked_appearances.add(appearance)

    def status(self, membership, now=None):
        state = "active" if membership.active(now) else "dormant"
        return (f"Lantern Wisp: {state}; color: {self.color}; "
                f"appearance: {self.appearance}; name: {self.name or 'unnamed'}; "
                f"summoned: {'yes' if self.summoned and state == 'active' else 'no'}.")

    def public_emote(self, owner_name, scene=""):
        """Purely descriptive: callers control frequency and room broadcasting."""
        if scene == "rain":
            return f"{self.label(owner_name)} shivers softly beneath the rain."
        if scene == "night":
            return f"{self.label(owner_name)} pulses like a distant star."
        return f"{self.label(owner_name)} drifts in a slow, silent circle."


def wisp_room_entities(players, memberships, wisps, now=None):
    """Return visible cosmetic entities; never NPCs, targets or light sources.

    players: iterable of (player_id, player_name, online, room_id)
    memberships/wisps: dict keyed by player_id.
    """
    result = []
    for player_id, name, online, room_id in players:
        membership = memberships.get(player_id)
        wisp = wisps.get(player_id)
        if membership and wisp and wisp.visible(membership, online, now):
            result.append({"type": "lantern_wisp", "owner_id": player_id,
                           "room_id": room_id, "label": wisp.label(name),
                           "color": wisp.color, "appearance": wisp.appearance})
    return result
