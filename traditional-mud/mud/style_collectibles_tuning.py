from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from mud.database import Database
import mud.style_collectibles as style


def _remove_style_login_announcement() -> None:
    """Keep style systems live without advertising them on every character entry.

    The style runtime originally wrapped ``enter_character`` with one informational
    announcement. Production applies this tuning immediately after that runtime, so
    replace only that wrapper with the same schema/discovery/GMCP work and omit the
    unsolicited login text. WARDROBE, FRAGRANCES, LOOK <player>, and all style
    mechanics remain unchanged.
    """
    from mud.session import PlayerSession

    if getattr(PlayerSession, "_style_login_announcement_removed", False):
        return

    current_enter = PlayerSession.enter_character
    closure = {
        name: cell.cell_contents
        for name, cell in zip(
            current_enter.__code__.co_freevars,
            current_enter.__closure__ or (),
        )
    }
    previous_enter = closure.get("previous_enter")
    if previous_enter is None:
        # This tuning module is also exercised in isolation by unit tests. If the
        # style runtime has not been installed on PlayerSession yet, there is no
        # login announcement to remove.
        return

    async def enter_character(self) -> None:
        await previous_enter(self)
        if self.character is None:
            return
        style.ensure_style_schema(self.database)
        style._sync_discoveries(self)
        await style._send_style_gmcp(self)

    PlayerSession.enter_character = enter_character
    PlayerSession._style_login_announcement_removed = True


def apply_style_collectibles_tuning() -> None:
    """Keep the advertised fragrance XP bonus mathematically exact.

    The first style pass stores sub-XP remainder so a 10% fragrance can apply to
    tiny awards instead of rounding every award up. Binary floats can still leave
    ten 0.1 remainders at 0.999999..., however. Replace only that hook with a
    Decimal-backed version while preserving the original unmodified DB XP method.
    """
    base_add_experience = getattr(Database, "_style_xp_original", Database.add_experience)

    def add_experience(self, character_id: int, amount: int) -> int:
        if amount < 0:
            return base_add_experience(self, character_id, amount)
        style.ensure_style_schema(self)
        effect = style._active_fragrance(self, character_id)
        if effect is None or amount == 0:
            return base_add_experience(self, character_id, amount)
        fragrance = style.FRAGRANCE_BY_KEY.get(str(effect["fragrance_key"]))
        if fragrance is None:
            return base_add_experience(self, character_id, amount)

        raw_bonus = (
            Decimal(amount) * Decimal(fragrance.xp_bonus_percent) / Decimal(100)
            + Decimal(str(effect["bonus_fraction"]))
        )
        bonus = int(raw_bonus.to_integral_value(rounding=ROUND_DOWN))
        remainder = raw_bonus - Decimal(bonus)
        level = base_add_experience(self, character_id, amount + bonus)
        with self.connect() as db:
            db.execute(
                "UPDATE character_fragrance_effects "
                "SET bonus_fraction = ?, bonus_xp_earned = bonus_xp_earned + ? "
                "WHERE character_id = ?",
                (float(remainder), bonus, character_id),
            )
        return level

    Database.add_experience = add_experience
    Database._style_xp_original = base_add_experience
    Database._style_xp_hook_installed = True
    Database._style_xp_precision_tuned = True
    _remove_style_login_announcement()
