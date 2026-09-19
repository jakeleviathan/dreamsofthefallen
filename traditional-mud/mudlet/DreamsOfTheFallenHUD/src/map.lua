-- Dreams of the Fallen - Persistent Discovery Mapper
-- HUD 2.2.2
--
-- The server owns discovery. This panel deliberately refuses to invent rooms
-- from visible exits: Dreams.Map contains only places this character has entered.

DreamsHUD = DreamsHUD or {}
local H = DreamsHUD
H.version = "2.2.2"
H.state = H.state or {}
H.state.map = H.state.map or { current = 0, discovered_count = 0, rooms = {} }
H.mapCoordinates = H.mapCoordinates or {}
H.mapAreaIds = H.mapAreaIds or {}

local directionDelta = {
  north = {0, 1, 0}, south = {0, -1, 0},
  east = {1, 0, 0}, west = {-1, 0, 0},
  up = {0, 0, 1}, down = {0, 0, -1},
  northeast = {1, 1, 0}, northwest = {-1, 1, 0},
  southeast = {1, -1, 0}, southwest = {-1, -1, 0},
}

local function ensureArea(zone)
  zone = tostring(zone or "Astralis")
  if H.mapAreaIds[zone] then return H.mapAreaIds[zone] end
  local id = nil
  if getAreaTable then
    local ok, areas = pcall(getAreaTable)
    if ok and areas then id = areas[zone] end
  end
  if not id and addAreaName then
    local ok, value = pcall(addAreaName, zone)
    if ok then id = value end
  end
  H.mapAreaIds[zone] = id
  return id
end

local function ensureRoom(id, name, zone, x, y, z)
  if not id then return end
  if roomExists then
    local ok, exists = pcall(roomExists, id)
    if ok and not exists and addRoom then pcall(addRoom, id) end
  elseif addRoom then
    pcall(addRoom, id)
  end
  if setRoomName then pcall(setRoomName, id, tostring(name or id)) end
  local area = ensureArea(zone)
  if area and setRoomArea then pcall(setRoomArea, id, area) end
  if x and setRoomCoordinates then pcall(setRoomCoordinates, id, x, y, z or 0) end
end

local function roomIndex(data)
  local result = {}
  for _, room in ipairs((data or {}).rooms or {}) do
    local id = tonumber(room.num)
    if id then result[id] = room end
  end
  return result
end

local function storedCoordinate(id)
  if H.mapCoordinates[id] then return H.mapCoordinates[id] end
  if getRoomCoordinates then
    local ok, x, y, z = pcall(getRoomCoordinates, id)
    if ok and tonumber(x) and tonumber(y) then
      local value = {tonumber(x), tonumber(y), tonumber(z) or 0}
      H.mapCoordinates[id] = value
      return value
    end
  end
  return nil
end

local function chooseCoordinate(candidate, occupied)
  local key = table.concat(candidate, ":")
  if not occupied[key] then return candidate end
  local alternatives = {
    {candidate[1] + 1, candidate[2], candidate[3]},
    {candidate[1] - 1, candidate[2], candidate[3]},
    {candidate[1], candidate[2] + 1, candidate[3]},
    {candidate[1], candidate[2] - 1, candidate[3]},
  }
  for _, value in ipairs(alternatives) do
    local altKey = table.concat(value, ":")
    if not occupied[altKey] then return value end
  end
  return candidate
end

function H.updateMapper()
  local data = H.state.map or {}
  local rooms = roomIndex(data)
  local current = tonumber(data.current)
  if not current or not rooms[current] then
    if H.mapFallback and not H.mapWidget then
      H.mapFallback:echo("<center>MAP<br/><br/>Walk into rooms to add them to your personal map.</center>")
    end
    return
  end

  -- Each character gets separate Mudlet mapper areas. This prevents a player who
  -- switches alts in one Mudlet profile from seeing rooms only another character
  -- has discovered, while still allowing each character's map to persist locally.
  local characterLabel = tostring(data.character_name or "Explorer")

  -- Rebuild local coordinates outward from the current room. Pull coordinates
  -- back out of Mudlet's persistent mapper database after a client restart so the
  -- explored graph does not jump back to the origin every time Mudlet relaunches.
  for id, _room in pairs(rooms) do storedCoordinate(id) end
  local currentCoord = storedCoordinate(current) or {0, 0, 0}
  H.mapCoordinates[current] = currentCoord
  local occupied = {}
  for id, coord in pairs(H.mapCoordinates) do
    if rooms[tonumber(id)] then occupied[table.concat(coord, ":")] = tonumber(id) end
  end

  local queue = {current}
  local queued = {[current] = true}
  local cursor = 1
  while cursor <= #queue do
    local source = queue[cursor]
    cursor = cursor + 1
    local sourceRoom = rooms[source]
    local sourceCoord = H.mapCoordinates[source] or currentCoord
    for direction, targetValue in pairs(sourceRoom.exits or {}) do
      local target = tonumber(targetValue)
      if target and rooms[target] then
        if not H.mapCoordinates[target] then
          local delta = directionDelta[tostring(direction):lower()] or {0, 0, 0}
          local candidate = {
            sourceCoord[1] + delta[1],
            sourceCoord[2] + delta[2],
            sourceCoord[3] + delta[3],
          }
          candidate = chooseCoordinate(candidate, occupied)
          H.mapCoordinates[target] = candidate
          occupied[table.concat(candidate, ":")] = target
        end
        if not queued[target] then
          queued[target] = true
          queue[#queue + 1] = target
        end
      end
    end
  end

  -- Only rooms present in Dreams.Map are created or connected. A visible exit to
  -- an unvisited place remains text-only until the player actually goes there.
  for id, room in pairs(rooms) do
    local coord = H.mapCoordinates[id] or {0, 0, 0}
    local scopedZone = tostring(room.zone or "Astralis") .. " · " .. characterLabel
    ensureRoom(id, room.name, scopedZone, coord[1], coord[2], coord[3])
  end
  for id, room in pairs(rooms) do
    -- HUD 2.0 speculatively created exits to visible-but-unvisited destinations.
    -- Clear any such old standard-direction exits from rooms now owned by the
    -- discovery mapper, then add back only the server-authorized discovered ones.
    if setExit then
      for direction, _delta in pairs(directionDelta) do
        if not (room.exits or {})[direction] then
          pcall(setExit, id, -1, direction)
        end
      end
    end
    for direction, targetValue in pairs(room.exits or {}) do
      local target = tonumber(targetValue)
      if target and rooms[target] and setExit then
        pcall(setExit, id, target, tostring(direction):lower())
      end
    end
  end

  if centerview then pcall(centerview, current) end
  if H.mapFallback and not H.mapWidget then
    H.mapFallback:echo(string.format(
      "<center>MAP<br/><br/>%d rooms discovered.<br/>The graphical mapper widget is unavailable in this Mudlet build.<br/><br/>Type MAP for the ASCII map.</center>",
      tonumber(data.discovered_count) or 0
    ))
  end
end

function H.onMapModern()
  local data = gmcp and gmcp.Dreams and gmcp.Dreams.Map
  if not data then return end
  H.state.map = data
  H.updateMapper()
end

-- modern.lua registers its ordinary handlers before this extension loads. Add the
-- discovery graph handler afterward; its Room handler will call this overridden
-- updateMapper function on future room changes too.
if H.modernHandlers then
  if H.modernHandlers.map then pcall(killAnonymousEventHandler, H.modernHandlers.map) end
  H.modernHandlers.map = registerAnonymousEventHandler("gmcp.Dreams.Map", H.onMapModern)
end

if H.mapFallback and not H.mapWidget then
  H.mapFallback:echo("<center>MAP<br/><br/>Your discovered-room graph will appear here as you explore.<br/><br/>Type MAP for the ASCII version.</center>")
end

H.updateMapper()
