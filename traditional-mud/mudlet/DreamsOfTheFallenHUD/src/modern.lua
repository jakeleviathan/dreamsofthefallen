-- Dreams of the Fallen - Modern Telnet Experience
-- Version 2.0.0
--
-- This layer is intentionally a client presentation of normal Telnet commands.
-- Every click sends the same command a player could type by hand. GMCP supplies
-- structured state so the UI never has to scrape prose or guess at combat data.

DreamsHUD = DreamsHUD or {}
local H = DreamsHUD
H.version = "2.0.0"
H.handlers = H.handlers or {}
H.state = H.state or {}
H.state.room = H.state.room or nil
H.state.party = H.state.party or { active = false, members = {} }
H.state.quests = H.state.quests or { active = {} }
H.state.inventory = H.state.inventory or { items = {} }
H.state.abilities = H.state.abilities or { abilities = {} }
H.state.context = H.state.context or { actions = {} }
H.state.onboarding = H.state.onboarding or { active = false }
H.state.selected_ally = H.state.selected_ally or ""
H.activePanel = H.activePanel or "map"
H.modernHandlers = H.modernHandlers or {}
H.modernTriggers = H.modernTriggers or {}
H.soundEnabled = H.soundEnabled ~= false

local function escape(value)
  value = tostring(value or "")
  value = value:gsub("&", "&amp;")
  value = value:gsub("<", "&lt;")
  value = value:gsub(">", "&gt;")
  return value
end

local function truncate(value, length)
  value = tostring(value or "")
  if #value <= length then return value end
  return value:sub(1, math.max(1, length - 1)) .. "…"
end

local PANEL_STYLE = [[
  QLabel {
    background-color: rgba(8, 6, 10, 238);
    border: 1px solid #4b3c52;
    border-radius: 6px;
    color: #e8dfd1;
  }
]]

local BUTTON_STYLE = [[
  QLabel {
    background-color: rgba(22, 17, 25, 245);
    border: 1px solid #6d5a72;
    border-radius: 5px;
    color: #e8dfd1;
    font-size: 9pt;
    qproperty-alignment: 'AlignCenter';
  }
  QLabel:hover {
    background-color: rgba(52, 39, 58, 250);
    border: 1px solid #b69772;
    color: #fff4df;
  }
]]

local BUTTON_ACTIVE_STYLE = [[
  QLabel {
    background-color: rgba(91, 70, 49, 245);
    border: 1px solid #d0ad75;
    border-radius: 5px;
    color: #fff4df;
    font-size: 9pt;
    font-weight: bold;
    qproperty-alignment: 'AlignCenter';
  }
]]

local BUTTON_DANGER_STYLE = [[
  QLabel {
    background-color: rgba(84, 16, 27, 245);
    border: 1px solid #c45161;
    border-radius: 5px;
    color: #fff0ec;
    font-size: 9pt;
    font-weight: bold;
    qproperty-alignment: 'AlignCenter';
  }
  QLabel:hover { background-color: rgba(125, 22, 39, 250); }
]]

local SMALL_TEXT = [[
  QLabel {
    background-color: transparent;
    border: 0px;
    color: #cfc4d2;
    font-size: 9pt;
    qproperty-wordWrap: true;
    qproperty-alignment: 'AlignLeft|AlignVCenter';
  }
]]

local MUTED_TEXT = [[
  QLabel {
    background-color: transparent;
    border: 0px;
    color: #94889a;
    font-size: 8pt;
    qproperty-wordWrap: true;
    qproperty-alignment: 'AlignLeft|AlignVCenter';
  }
]]

local GOLD_TEXT = [[
  QLabel {
    background-color: transparent;
    border: 0px;
    color: #dfc18c;
    font-size: 10pt;
    font-weight: bold;
    qproperty-wordWrap: true;
    qproperty-alignment: 'AlignLeft|AlignVCenter';
  }
]]

local function label(parent, name, x, y, width, height, style)
  local result = Geyser.Label:new({
    name = name, x = x, y = y, width = width, height = height,
  }, parent)
  result:setStyleSheet(style or SMALL_TEXT)
  return result
end

local function setTooltip(widget, text)
  if widget and widget.setToolTip then pcall(function() widget:setToolTip(text or "") end) end
end

function H.runAction(command)
  if not command or command == "" then return end
  send(command, true)
end

function H.selectAlly(name)
  H.state.selected_ally = tostring(name or "")
  H.renderPartyPanel()
  H.renderHotbar()
end

function H.runAbility(index)
  local list = (H.state.abilities or {}).abilities or {}
  local ability = list[tonumber(index) or 0]
  if not ability then return end
  local command = tostring(ability.command or "")
  if command == "" then return end
  local mode = tostring(ability.target_mode or "enemy")
  local selected = tostring(H.state.selected_ally or "")
  if (mode == "ally" or mode == "dead_ally") and selected ~= "" then
    command = command .. " " .. selected
  end
  send(command, true)
end

function H.setPanel(panel)
  H.activePanel = panel or "map"
  local panels = { "map", "party", "quests", "inventory" }
  for _, key in ipairs(panels) do
    if H.panelButtons and H.panelButtons[key] then
      H.panelButtons[key]:setStyleSheet(key == H.activePanel and BUTTON_ACTIVE_STYLE or BUTTON_STYLE)
    end
  end
  if H.mapWidget then if H.activePanel == "map" then H.mapWidget:show() else H.mapWidget:hide() end end
  if H.mapFallback then if H.activePanel == "map" and not H.mapWidget then H.mapFallback:show() else H.mapFallback:hide() end end
  if H.partyPane then if H.activePanel == "party" then H.partyPane:show() else H.partyPane:hide() end end
  if H.questPane then if H.activePanel == "quests" then H.questPane:show() else H.questPane:hide() end end
  if H.inventoryPane then if H.activePanel == "inventory" then H.inventoryPane:show() else H.inventoryPane:hide() end end
end

function H.toggleSound()
  H.soundEnabled = not H.soundEnabled
  if H.soundButton then
    H.soundButton:echo("<center>Sound: " .. (H.soundEnabled and "ON" or "OFF") .. "</center>")
  end
end

-- Self-contained tiny audio cues. They are synthesized into the profile folder
-- the first time this package runs so the official package does not need to ship
-- binary audio assets. They are deliberately short and quiet-ish: information,
-- not a soundtrack.
local function le16(value)
  value = math.floor(value) % 65536
  return string.char(value % 256, math.floor(value / 256) % 256)
end

local function le32(value)
  value = math.floor(value) % 4294967296
  return string.char(
    value % 256,
    math.floor(value / 256) % 256,
    math.floor(value / 65536) % 256,
    math.floor(value / 16777216) % 256
  )
end

local function synthCue(path, segments)
  local sampleRate = 8000
  local amplitude = 4800
  local samples = {}
  local total = 0
  for _, segment in ipairs(segments) do
    local frequency = segment[1]
    local duration = segment[2]
    local count = math.max(1, math.floor(sampleRate * duration))
    for i = 0, count - 1 do
      local fade = math.min(1, i / 120, (count - i) / 160)
      local raw = math.floor(math.sin(2 * math.pi * frequency * i / sampleRate) * amplitude * fade)
      if raw < 0 then raw = raw + 65536 end
      samples[#samples + 1] = le16(raw)
    end
    total = total + count
  end
  local data = table.concat(samples)
  local header = "RIFF" .. le32(36 + #data) .. "WAVE" ..
    "fmt " .. le32(16) .. le16(1) .. le16(1) .. le32(sampleRate) ..
    le32(sampleRate * 2) .. le16(2) .. le16(16) .. "data" .. le32(#data)
  local file = io.open(path, "wb")
  if not file then return false end
  file:write(header)
  file:write(data)
  file:close()
  return true
end

function H.ensureCueFiles()
  if H.cueFiles then return end
  local home = getMudletHomeDir and getMudletHomeDir() or "."
  H.cueFiles = {
    level_up = home .. "/dreams_level_up.wav",
    critical = home .. "/dreams_critical.wav",
    aggro = home .. "/dreams_aggro.wav",
  }
  local definitions = {
    level_up = { {523.25, 0.07}, {659.25, 0.08}, {783.99, 0.11} },
    critical = { {196.00, 0.10}, {146.83, 0.13} },
    aggro = { {392.00, 0.055}, {329.63, 0.07} },
  }
  for kind, path in pairs(H.cueFiles) do
    local file = io.open(path, "rb")
    if file then
      file:close()
    else
      pcall(function() synthCue(path, definitions[kind]) end)
    end
  end
end

function H.playCue(kind)
  if not H.soundEnabled then return end
  if kind ~= "level_up" and kind ~= "critical" and kind ~= "aggro" then return end
  H.ensureCueFiles()
  local path = H.cueFiles and H.cueFiles[kind]
  if path and playSoundFile then
    local ok = pcall(function() playSoundFile(path) end)
    if ok then return end
  end
  if beep then pcall(beep) end
end

function H.flashEvent(kind)
  if not H.eventBanner then return end
  local messages = {
    level_up = "LEVEL UP",
    critical = "CRITICAL HEALTH",
    aggro = "YOU HAVE AGGRO",
    combat_start = "COMBAT",
    combat_end = "CLEAR",
  }
  local message = messages[kind]
  if not message then return end
  H.eventBanner:echo("<center>" .. message .. "</center>")
  H.eventBanner:show()
  tempTimer(1.4, function()
    if H.eventBanner then H.eventBanner:hide() end
  end)
end

function H.buildModern()
  if H.modernBuilt then return end
  H.build()

  setBorderTop(math.max(getBorderTop(), 142))
  setBorderRight(math.max(getBorderRight(), 430))
  setBorderBottom(math.max(getBorderBottom(), 154))

  -- The old target panel remains useful and visually distinctive. The modern
  -- dock lives below it and uses tabs instead of trying to show every list at
  -- once on smaller laptop/projector displays.
  H.sideFrame = Geyser.Label:new({
    name = "DreamsHUD.SideFrame", x = -420, y = 254, width = 406, height = -164,
  })
  H.sideFrame:setStyleSheet(PANEL_STYLE)

  H.panelButtons = {}
  local tabs = {
    { "map", "MAP" }, { "party", "PARTY" }, { "quests", "QUESTS" }, { "inventory", "PACK" },
  }
  for index, spec in ipairs(tabs) do
    local button = label(H.sideFrame, "DreamsHUD.Tab." .. spec[1],
      tostring((index - 1) * 25 + 1) .. "%", 5, "24%", 28, BUTTON_STYLE)
    button:echo("<center>" .. spec[2] .. "</center>")
    button:setClickCallback("DreamsHUD.setPanel", spec[1])
    H.panelButtons[spec[1]] = button
  end

  H.contentFrame = Geyser.Container:new({
    name = "DreamsHUD.SideContent", x = "2%", y = 39, width = "96%", height = -47,
  }, H.sideFrame)

  if Geyser.Mapper then
    local ok, mapper = pcall(function()
      return Geyser.Mapper:new({
        name = "DreamsHUD.Mapper", x = 0, y = 0, width = "100%", height = "100%",
      }, H.contentFrame)
    end)
    if ok then H.mapWidget = mapper end
  end
  if not H.mapWidget then
    H.mapFallback = label(H.contentFrame, "DreamsHUD.MapFallback", 8, 8, -16, -16, SMALL_TEXT)
    H.mapFallback:echo("<center>MAP<br/><br/>Your client does not expose the embedded mapper widget.<br/>Room data is still being received through GMCP.</center>")
  end

  H.partyPane = Geyser.Container:new({ name = "DreamsHUD.PartyPane", x = 0, y = 0, width = "100%", height = "100%" }, H.contentFrame)
  H.partyHeader = label(H.partyPane, "DreamsHUD.PartyHeader", 8, 5, -16, 28, GOLD_TEXT)
  H.partyMembers = {}
  for i = 1, 5 do
    H.partyMembers[i] = label(H.partyPane, "DreamsHUD.PartyMember" .. i, 8, 36 + (i - 1) * 44, -16, 39, BUTTON_STYLE)
  end
  H.partyFooter = label(H.partyPane, "DreamsHUD.PartyFooter", 8, 260, -16, -8, MUTED_TEXT)

  H.questPane = Geyser.Container:new({ name = "DreamsHUD.QuestPane", x = 0, y = 0, width = "100%", height = "100%" }, H.contentFrame)
  H.questTitle = label(H.questPane, "DreamsHUD.QuestTitle", 8, 8, -16, 30, GOLD_TEXT)
  H.questObjective = label(H.questPane, "DreamsHUD.QuestObjective", 8, 42, -16, 120, SMALL_TEXT)
  H.questMore = label(H.questPane, "DreamsHUD.QuestMore", 8, 166, -16, 70, MUTED_TEXT)
  H.questButton = label(H.questPane, "DreamsHUD.QuestButton", 8, -42, -16, 34, BUTTON_STYLE)
  H.questButton:echo("<center>OPEN QUEST LOG</center>")
  H.questButton:setClickCallback("DreamsHUD.runAction", "QUESTS")

  H.inventoryPane = Geyser.Container:new({ name = "DreamsHUD.InventoryPane", x = 0, y = 0, width = "100%", height = "100%" }, H.contentFrame)
  H.inventoryHeader = label(H.inventoryPane, "DreamsHUD.InventoryHeader", 8, 6, -16, 28, GOLD_TEXT)
  H.inventoryRows = {}
  for i = 1, 8 do
    H.inventoryRows[i] = label(H.inventoryPane, "DreamsHUD.InventoryRow" .. i, 8, 34 + (i - 1) * 29, -16, 26, SMALL_TEXT)
  end
  H.inventoryButton = label(H.inventoryPane, "DreamsHUD.InventoryButton", 8, -42, -16, 34, BUTTON_STYLE)
  H.inventoryButton:echo("<center>OPEN INVENTORY</center>")
  H.inventoryButton:setClickCallback("DreamsHUD.runAction", "INVENTORY")

  -- Bottom command deck: one short onboarding line, then class hotbar and
  -- context-sensitive verbs. It behaves like a modern action bar but every
  -- button simply sends ordinary MUD text.
  H.bottomFrame = Geyser.Label:new({
    name = "DreamsHUD.BottomFrame", x = 8, y = -146, width = -438, height = 136,
  })
  H.bottomFrame:setStyleSheet(PANEL_STYLE)

  H.onboarding = label(H.bottomFrame, "DreamsHUD.Onboarding", 8, 4, -94, 24, MUTED_TEXT)
  H.soundButton = label(H.bottomFrame, "DreamsHUD.Sound", -82, 4, 74, 24, BUTTON_STYLE)
  H.soundButton:echo("<center>Sound: " .. (H.soundEnabled and "ON" or "OFF") .. "</center>")
  H.soundButton:setClickCallback("DreamsHUD.toggleSound")

  H.hotbar = {}
  for i = 1, 8 do
    local x = tostring((i - 1) * 12.5 + 0.5) .. "%"
    H.hotbar[i] = label(H.bottomFrame, "DreamsHUD.Hotbar" .. i, x, 34, "12%", 43, BUTTON_STYLE)
    H.hotbar[i]:setClickCallback("DreamsHUD.runAbility", i)
  end

  H.contextButtons = {}
  for i = 1, 10 do
    local x = tostring((i - 1) * 10 + 0.5) .. "%"
    H.contextButtons[i] = label(H.bottomFrame, "DreamsHUD.Context" .. i, x, 84, "9.5%", 40, BUTTON_STYLE)
  end

  H.eventBanner = label(nil, "DreamsHUD.EventBanner", "37%", 12, "26%", 34, BUTTON_ACTIVE_STYLE)
  H.eventBanner:hide()

  H.modernBuilt = true
  H.setPanel(H.activePanel)
  H.renderModernAll()
end

local directionDelta = {
  north = {0, 1, 0}, south = {0, -1, 0},
  east = {1, 0, 0}, west = {-1, 0, 0},
  up = {0, 0, 1}, down = {0, 0, -1},
  northeast = {1, 1, 0}, northwest = {-1, 1, 0},
  southeast = {1, -1, 0}, southwest = {-1, -1, 0},
}

H.mapCoordinates = H.mapCoordinates or {}
H.mapAreaIds = H.mapAreaIds or {}

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

function H.updateMapper()
  local room = H.state.room
  if not room or not room.num then return end
  local current = tonumber(room.num)
  if not current then return end

  local coords = H.mapCoordinates[current]
  if not coords then
    coords = {0, 0, 0}
    H.mapCoordinates[current] = coords
  end
  ensureRoom(current, room.name, room.zone, coords[1], coords[2], coords[3])

  for direction, targetValue in pairs(room.exits or {}) do
    local target = tonumber(targetValue)
    if target then
      local targetCoords = H.mapCoordinates[target]
      if not targetCoords then
        local d = directionDelta[tostring(direction):lower()] or {0, 0, 0}
        targetCoords = {coords[1] + d[1], coords[2] + d[2], coords[3] + d[3]}
        H.mapCoordinates[target] = targetCoords
      end
      local targetKey = room.exit_keys and room.exit_keys[direction]
      ensureRoom(target, targetKey or "Unexplored", room.zone, targetCoords[1], targetCoords[2], targetCoords[3])
      if setExit then pcall(setExit, current, target, tostring(direction):lower()) end
    end
  end
  if centerview then pcall(centerview, current) end
end

function H.renderPartyPanel()
  if not H.modernBuilt then return end
  local party = H.state.party or { active = false, members = {} }
  if not party.active then
    local nearby = party.nearby or {}
    H.partyHeader:echo("PARTY — SOLO")
    for i = 1, 5 do
      local row = H.partyMembers[i]
      local candidate = nearby[i]
      if candidate then
        row:echo(string.format("<center>%s  •  Lv %s  •  invite</center>", escape(candidate.name), escape(candidate.level)))
        row:setClickCallback("DreamsHUD.runAction", "PARTY INVITE " .. candidate.name)
        row:show()
      elseif i == 1 then
        row:echo("<center>PARTY NEARBY — find adventurers here</center>")
        row:setClickCallback("DreamsHUD.runAction", "PARTY NEARBY")
        row:show()
      else
        row:hide()
      end
    end
    H.partyFooter:echo("Forming a group never changes the underlying text commands.")
    return
  end

  local focus = tostring(party.focus or "")
  H.partyHeader:echo("PARTY  •  " .. escape(string.upper(tostring(party.loot_mode or "roundrobin"))) .. (focus ~= "" and ("  •  FOCUS: " .. escape(focus)) or ""))
  local members = party.members or {}
  for i = 1, 5 do
    local row = H.partyMembers[i]
    local member = members[i]
    if not member then
      row:hide()
    else
      local markers = {}
      if member.leader then markers[#markers + 1] = "LEAD" end
      if member.aggro then markers[#markers + 1] = "AGGRO" end
      if member.dead then markers[#markers + 1] = "DEAD" end
      if member.here == false then markers[#markers + 1] = "AWAY" end
      if member.ready == true then markers[#markers + 1] = "READY" elseif member.ready == false then markers[#markers + 1] = "WAIT" end
      local selected = tostring(H.state.selected_ally or "") == tostring(member.name or "")
      row:setStyleSheet(selected and BUTTON_ACTIVE_STYLE or (member.dead and BUTTON_DANGER_STYLE or BUTTON_STYLE))
      local hp = member.online and string.format("%d%%", tonumber(member.hp_percent) or 0) or "OFFLINE"
      row:echo(string.format("<center>%s  •  %s  %s<br/>%s</center>",
        escape(member.name), hp, table.concat(markers, " "), selected and "SELECTED TARGET" or "click to target"))
      row:setClickCallback("DreamsHUD.selectAlly", tostring(member.name or ""))
      row:show()
    end
  end
  H.partyFooter:echo("Click a member to make ally-target hotbar abilities use that character.")
end

function H.renderQuestPanel()
  if not H.modernBuilt then return end
  local active = (H.state.quests or {}).active or {}
  local quest = active[1]
  if not quest then
    H.questTitle:echo("NO ACTIVE QUEST")
    H.questObjective:echo("The road is yours. Exploration, hunting, crafting, and social play continue without a quest marker.")
    H.questMore:echo("")
    return
  end
  H.questTitle:echo(escape(quest.name))
  H.questObjective:echo("<b>Current objective</b><br/>" .. escape(quest.objective or "Explore and learn what the situation requires."))
  local other = #active - 1
  H.questMore:echo(other > 0 and (tostring(other) .. " other active quest" .. (other == 1 and "" or "s") .. ". Open the log to switch context.") or "This is your only active quest.")
end

function H.renderInventoryPanel()
  if not H.modernBuilt then return end
  local inventory = H.state.inventory or { items = {} }
  H.inventoryHeader:echo(string.format("PACK  •  %d items / %d kinds", tonumber(inventory.count) or 0, tonumber(inventory.unique) or 0))
  local items = inventory.items or {}
  for i = 1, 8 do
    local row = H.inventoryRows[i]
    local item = items[i]
    if not item then
      row:echo("")
      row:hide()
    else
      local equipped = item.equipped and ("  <span style='color:#d9bc7e'>[" .. escape(item.slot) .. "]</span>") or ""
      row:echo(string.format("%dx  %s%s", tonumber(item.quantity) or 0, escape(item.name), equipped))
      setTooltip(row, item.description or "")
      row:show()
    end
  end
end

function H.renderHotbar()
  if not H.modernBuilt then return end
  local abilities = (H.state.abilities or {}).abilities or {}
  local selected = tostring(H.state.selected_ally or "")
  for i = 1, 8 do
    local button = H.hotbar[i]
    local ability = abilities[i]
    if not ability then
      button:echo("<center>—</center>")
      button:setStyleSheet(PANEL_STYLE)
      setTooltip(button, "")
    else
      local ready = ability.ready ~= false and (tonumber(ability.cooldown_remaining) or 0) <= 0.05
      local suffix = ""
      if not ready then suffix = string.format("<br/><span style='color:#a9949f'>%.1fs</span>", tonumber(ability.cooldown_remaining) or 0) end
      local target = ""
      if (ability.target_mode == "ally" or ability.target_mode == "dead_ally") and selected ~= "" then
        target = "<br/><span style='color:#9ab6d6'>→ " .. escape(truncate(selected, 10)) .. "</span>"
      end
      button:setStyleSheet(ready and BUTTON_STYLE or PANEL_STYLE)
      button:echo("<center>" .. tostring(i) .. "  " .. escape(truncate(ability.name, 16)) .. suffix .. target .. "</center>")
      setTooltip(button, (ability.description or "") .. "\nMana: " .. tostring(ability.mana or 0) .. " | Cooldown: " .. tostring(ability.cooldown or 0) .. "s")
    end
  end
end

function H.renderContext()
  if not H.modernBuilt then return end
  local actions = (H.state.context or {}).actions or {}
  for i = 1, 10 do
    local button = H.contextButtons[i]
    local action = actions[i]
    if not action then
      button:hide()
    else
      button:show()
      button:setStyleSheet(action.kind == "danger" and BUTTON_DANGER_STYLE or (action.primary and BUTTON_ACTIVE_STYLE or BUTTON_STYLE))
      button:echo("<center>" .. escape(truncate(action.label, 14)) .. "</center>")
      button:setClickCallback("DreamsHUD.runAction", tostring(action.command or ""))
      setTooltip(button, tostring(action.command or ""))
    end
  end
end

function H.renderOnboarding()
  if not H.modernBuilt then return end
  local o = H.state.onboarding or { active = false }
  if not o.active then
    H.onboarding:echo("The command line is always authoritative. Clicks are shortcuts, not a different game.")
    return
  end
  H.onboarding:echo("<span style='color:#dfc18c'><b>" .. escape(o.title or "") .. "</b></span>  —  " .. escape(o.text or ""))
  setTooltip(H.onboarding, o.command and ("Suggested command: " .. o.command) or "")
  if o.command and o.command ~= "" then H.onboarding:setClickCallback("DreamsHUD.runAction", o.command) end
end

function H.renderModernAll()
  if not H.modernBuilt then return end
  H.renderPartyPanel()
  H.renderQuestPanel()
  H.renderInventoryPanel()
  H.renderHotbar()
  H.renderContext()
  H.renderOnboarding()
  H.updateMapper()
end

function H.onRoomModern()
  local room = gmcp and gmcp.Dreams and gmcp.Dreams.Room
  if not room then return end
  H.state.room = room
  H.updateMapper()
end

function H.onPartyModern()
  local data = gmcp and gmcp.Dreams and gmcp.Dreams.Party
  if not data then return end
  H.state.party = data
  H.renderPartyPanel()
end

function H.onQuestsModern()
  local data = gmcp and gmcp.Dreams and gmcp.Dreams.Quests
  if not data then return end
  H.state.quests = data
  H.renderQuestPanel()
end

function H.onInventoryModern()
  local data = gmcp and gmcp.Dreams and gmcp.Dreams.Inventory
  if not data then return end
  H.state.inventory = data
  H.renderInventoryPanel()
end

function H.onAbilitiesModern()
  local data = gmcp and gmcp.Dreams and gmcp.Dreams.Abilities
  if not data then return end
  H.state.abilities = data
  H.renderHotbar()
end

function H.onContextModern()
  local data = gmcp and gmcp.Dreams and gmcp.Dreams.Context
  if not data then return end
  H.state.context = data
  H.renderContext()
end

function H.onOnboardingModern()
  local data = gmcp and gmcp.Dreams and gmcp.Dreams.Onboarding
  if not data then return end
  H.state.onboarding = data
  H.renderOnboarding()
end

function H.onEventModern()
  local data = gmcp and gmcp.Dreams and gmcp.Dreams.Event
  if not data then return end
  local kind = tostring(data.kind or "")
  H.playCue(kind)
  H.flashEvent(kind)
end

local function tintCurrentLine(r, g, b)
  if not selectCurrentLine or not setFgColor then return end
  pcall(function()
    selectCurrentLine()
    setFgColor(r, g, b)
    if deselect then deselect() end
  end)
end

function H.registerTextEmphasis()
  for _, triggerId in ipairs(H.modernTriggers) do pcall(killTrigger, triggerId) end
  H.modernTriggers = {}
  if not tempRegexTrigger then return end
  H.modernTriggers[#H.modernTriggers + 1] = tempRegexTrigger("^\\*\\*\\*.*\\*\\*\\*$", function() tintCurrentLine(224, 190, 126) end)
  H.modernTriggers[#H.modernTriggers + 1] = tempRegexTrigger("^Quest (updated|complete):", function() tintCurrentLine(171, 203, 154) end)
  H.modernTriggers[#H.modernTriggers + 1] = tempRegexTrigger("^\\[(Party|Ready Check|Party Combat|Party Loot|Party Focus)", function() tintCurrentLine(151, 182, 214) end)
  H.modernTriggers[#H.modernTriggers + 1] = tempRegexTrigger("CRITICAL", function() tintCurrentLine(229, 93, 105) end)
end

function H.registerModernHandlers()
  local names = {
    room = {"gmcp.Dreams.Room", H.onRoomModern},
    party = {"gmcp.Dreams.Party", H.onPartyModern},
    quests = {"gmcp.Dreams.Quests", H.onQuestsModern},
    inventory = {"gmcp.Dreams.Inventory", H.onInventoryModern},
    abilities = {"gmcp.Dreams.Abilities", H.onAbilitiesModern},
    context = {"gmcp.Dreams.Context", H.onContextModern},
    onboarding = {"gmcp.Dreams.Onboarding", H.onOnboardingModern},
    event = {"gmcp.Dreams.Event", H.onEventModern},
  }
  for key, spec in pairs(names) do
    if H.modernHandlers[key] then pcall(killAnonymousEventHandler, H.modernHandlers[key]) end
    H.modernHandlers[key] = registerAnonymousEventHandler(spec[1], spec[2])
  end
  if H.modernHandlers.load then pcall(killAnonymousEventHandler, H.modernHandlers.load) end
  H.modernHandlers.load = registerAnonymousEventHandler("sysLoadEvent", function()
    H.buildModern()
    H.renderModernAll()
  end)
end

function H.initModern()
  H.buildModern()
  H.registerModernHandlers()
  H.registerTextEmphasis()
  H.ensureCueFiles()
  if sendGMCP then
    pcall(function()
      sendGMCP([[Core.Supports.Add ["Dreams 2","Room 1","Char 1"]]])
    end)
  end
  H.setPanel(H.activePanel)
  H.renderModernAll()
end

H.initModern()
