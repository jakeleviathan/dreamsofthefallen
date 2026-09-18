from __future__ import annotations

import os
from dataclasses import dataclass


OFFICIAL_MUDLET_HUD_PACKAGE = "DreamsOfTheFallenHUD"
# Keep the Client.GUI wire version aligned with the distributable HUD release.
# Mudlet uses this value to decide whether a previously installed package needs
# to be refreshed, so bug-fix releases must advance it as well.
OFFICIAL_MUDLET_HUD_VERSION = "2.1.1"
CURRENT_MUDLET_HUD_VERSION = "2.1.1"
OFFICIAL_MUDLET_HUD_URL = "https://mud.lvthn.io/DreamsOfTheFallenHUD.mpackage"


@dataclass(frozen=True, slots=True)
class MudletGuiOffer:
    """Configuration for Mudlet's server-offered Client.GUI package.

    Mudlet downloads GUI packages over HTTP(S), so the live deployment must
    provide a public URL for the bundled .mpackage. During local development
    the URL can remain empty and the package can still be installed manually.
    """

    version: str = OFFICIAL_MUDLET_HUD_VERSION
    url: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.url.strip())


def configured_mudlet_gui_offer() -> MudletGuiOffer:
    return MudletGuiOffer(
        version=os.getenv("DREAMS_MUDLET_HUD_VERSION", OFFICIAL_MUDLET_HUD_VERSION).strip()
        or OFFICIAL_MUDLET_HUD_VERSION,
        url=os.getenv("DREAMS_MUDLET_HUD_URL", OFFICIAL_MUDLET_HUD_URL).strip()
        or OFFICIAL_MUDLET_HUD_URL,
    )
