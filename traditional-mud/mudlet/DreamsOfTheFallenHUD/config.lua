mpackage = "DreamsOfTheFallenHUD"
author = "Dreams of the Fallen"
title = "Dreams of the Fallen Official HUD"
description = [[
# Dreams of the Fallen Official HUD 2.1.1

A modern gothic-fantasy Mudlet interface for **Dreams of the Fallen** that keeps the normal Telnet command line authoritative.

Features:
- live Health, Mana, Movement, target, character, and combat state
- persistent per-character exploration mapper driven by `Dreams.Map`; only rooms you have actually entered are revealed
- tabbed party, quest, and inventory panels
- clickable party member targeting for ally abilities
- class hotbar with live cooldown/readiness state
- context-sensitive movement, talk, combat, inspect, crafting, and utility actions
- gentle first-session onboarding that disappears after the player learns the fundamentals
- selective text emphasis instead of full-screen color noise
- synthesized low-fi level-up, critical-health, and aggro cues with an in-HUD sound toggle
- no text scraping: structured data comes from GMCP (`Dreams.*`, `Room.Info`, and `Char.*`)

Every button sends an ordinary MUD command. Players using a raw Telnet client retain the complete game, including the ASCII `MAP` command.

The HUD is designed to be offered automatically by the Dreams of the Fallen server through Mudlet's `Client.GUI` GMCP extension.
]]
version = "2.1.1"
created = "2026-09-18T13:45:00-04:00"
dependencies = ""
