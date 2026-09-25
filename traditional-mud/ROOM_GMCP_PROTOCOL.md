# Structured room feed for UI developers

The server sends one **`Dreams.Room` GMCP JSON object** whenever the player
enters a room or uses `LOOK`. Each GMCP subnegotiation is already framed by
Telnet `IAC SB GMCP` and `IAC SE`: that is the unambiguous start/end of the
room message. **Do not look for visible `[ROOM_START]` / `[ROOM_END]` tags.**
The ordinary ANSI-colored Telnet room view remains unchanged.

The renderer builds the text and structured data in **one pass**, so the UI
gets the actual player-visible description, discoveries, NPCs, players, creatures,
ground contents, corpses and exits rather than an approximate reconstruction.

## Example

Below is illustrative data, not a dump of the current world database:

```text
Dreams.Room {"schema_version":1,"revision":1,"id":"waymeet_crossroads",...}
```

```json
{
  "schema_version": 1,
  "revision": 1,
  "id": "waymeet_crossroads",
  "title": "Waymeet Crossroads",
  "region_id": "waymeet_frontier",
  "region": "Waymeet Frontier",
  "description": "Four roads meet around a weather-dark stone post...",
  "tags": ["road", "safe"],
  "notable": [
    {"id": "waymeet_stone", "name": "Waymeet Stone", "description": "A weather-dark distance post"}
  ],
  "on_ground": [{"text": "Wildflowers - a patch of bright flowers"}],
  "people": [
    {"id": "marshal_aven_marr", "name": "Marshal Aven Marr", "description": "studying the notices"}
  ],
  "local_reception": "",
  "players": [
    {
      "id": 1,
      "name": "Prime",
      "label": "Prime (you)",
      "role": "Goblin Priest",
      "description": "a Goblin Priest resting",
      "activity": "resting",
      "is_self": true
    }
  ],
  "creatures": [{"name": "Road Rat", "description": "sniffing around a wagon"}],
  "hostile": [],
  "corpses": [],
  "business": [],
  "exits": [
    {"direction": "north", "title": "The Fifth Lantern", "room_id": "waymeet_tavern"}
  ],
  "overlays": ["Rain has uncovered chalk marks beneath the notice board."]
}
```

The data in `overlays` represents authored extra room text from existing
content layers. It is plain text (ANSI formatting removed). It may be absent
in practice (an empty list), and clients should display it after the main
description. The core room description is **only** `description`; overlays are
never silently concatenated into it.

All section arrays are present, even when empty. Lists of creatures and players
preserve separate entries for separate individuals, so two rats are two records,
not a collapsed `Rat x2` string. `players[].activity` is the live activity
(resting, casting, fighting or standing nearby) at the time of the snapshot.

## When snapshots are sent

- **On entry / `LOOK`:** a complete new snapshot; even repeated `LOOK`
  receives an explicit packet.
- **On player-state events:** the existing `send_client_state` path checks for
  room changes, throttled to avoid processing every combat tick.
- **On NPC movement:** source and destination rooms receive an immediate update.
- **While idle:** the server checks connected GMCP players about every three
  seconds. If visible data changed, it sends the *full* new snapshot; otherwise
  it sends nothing. This detects other players resting/standing, actor arrivals
  or departures, weather-dependent features, dropped items and corpses.
- **No GMCP:** no room JSON is sent; normal text still works, with no visible
  protocol delimiters.

`revision` starts at 1 in a new room and increases with each successfully
sent packet for that room. Treat every packet as an **authoritative full
replacement**, not a partial patch: if `players` or `hostile` is empty, all
previous entries in that section are gone. `schema_version` is currently 1.
The `id` is the stable game room key; `exits[].room_id` is the destination key.

## Mudlet integration

The official HUD already registers the `gmcp.Dreams.Room` event and assigns
the payload to `DreamsHUD.state.room`. A custom UI can register the same event
and render `gmcp.Dreams.Room.title`, `.description`, `.people`, `.players`,
`.exits`, etc. An illustrative handler:

```lua
registerAnonymousEventHandler("gmcp.Dreams.Room", function()
  local room = gmcp.Dreams.Room
  if type(room) ~= "table" or room.schema_version ~= 1 then return end
  -- room is a COMPLETE snapshot. Replace your prior UI room model here.
  updateRoomPanel(room)
end)
```

This works with the existing GMCP negotiation. Respect account accessibility
and HUD preferences: when GMCP is disabled, the text presentation remains the
source of truth for that client.

## Server implementation

- `mud.room_presentation.render_room_lines(..., room_data=data)` populates
  the same semantic data used for the ANSI text (without reparsing text).
- `mud.room_player_presence.room_player_data` is the shared live player
  projection used by both the text and GMCP renderers.
- `mud.room_gmcp.push_room_snapshot` owns the wire package, per-session
  serialization, deduplication and revision tracking.
- `MudServer.refresh_room_clients` runs idle refreshes for online GMCP players.

Regression tests: `python -m unittest tests.test_room_gmcp -v` from
`traditional-mud/`, plus the existing room and Telnet tests.
