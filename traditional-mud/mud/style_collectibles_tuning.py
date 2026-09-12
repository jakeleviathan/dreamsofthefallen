from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from mud.database import Database
import mud.style_collectibles as style


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
