mpackage = "DreamsOfTheFallenHUD"
author = "Dreams of the Fallen"
title = "Dreams of the Fallen Official HUD"
description = [[
# Dreams of the Fallen Official HUD 2.2.10

A modern gothic-fantasy Mudlet interface for **Dreams of the Fallen** that keeps the normal Telnet command line authoritative.

Features:
- live Health, Mana, Movement, target, character, and combat state
- active-effects panel showing temporary buffs, wards, healing-over-time effects, and remaining durations
- tabbed active-effects, party, quest, and inventory panels with substantially larger high-contrast quest text, a scrollable large-inventory Pack view, and clickable item inspection
- clickable party member targeting for ally abilities
- customizable eight-slot class hotbar with live cooldown/readiness state and per-character saved assignments
- context-sensitive movement, talk, combat, inspect, crafting, and utility actions
- clean timed crafting bar in the existing bottom HUD strip, driven by structured GMCP instead of terminal redraw escape sequences
- gentle first-session onboarding that disappears after the player learns the fundamentals
- selective text emphasis instead of full-screen color noise
- synthesized low-fi level-up, critical-health, and aggro cues with an in-HUD sound toggle
- no text scraping: structured data comes from GMCP (`Dreams.*`, `Room.Info`, and `Char.*`)

Every button sends an ordinary MUD command. Players using a raw Telnet client retain the complete game, including the ASCII `MAP` command.

The HUD is designed to be offered automatically by the Dreams of the Fallen server through Mudlet's `Client.GUI` GMCP extension.
]]
version = "2.2.10"
created = "2026-09-20T16:55:00-04:00"
dependencies = ""
