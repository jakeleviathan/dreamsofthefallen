-- Dreams of the Fallen - Official Mudlet HUD
-- Version 1.0.0
--
-- A maximalist gothic-fantasy interface using only Mudlet/Geyser primitives.
-- Text deliberately uses Mudlet's normal readable UI font rather than a
-- decorative typeface so vitals stay legible during real-time combat.

DreamsHUD = DreamsHUD or {}
local H = DreamsHUD

H.version = "1.0.0"
H.handlers = H.handlers or {}
H.state = H.state or {
  hp = 0, max_hp = 1,
  mana = 0, max_mana = 1,
  movement = 0, max_movement = 1,
  target_name = "",
  target_hp = 0, target_max_hp = 1,
  target_active = false,
  character_name = "DREAMER",
  character_level = "",
  character_race = "",
  character_class = "",
}

local function clamp(value, low, high)
  value = tonumber(value) or 0
  if value < low then return low end
  if value > high then return high end
  return value
end

local function safeMax(value)
  value = tonumber(value) or 1
  if value < 1 then return 1 end
  return value
end

local function escapeHtml(value)
  value = tostring(value or "")
  value = value:gsub("&", "&amp;")
  value = value:gsub("<", "&lt;")
  value = value:gsub(">", "&gt;")
  return value
end

local OUTER_FRAME = [[
  QLabel {
    background-color: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #17111b, stop:0.45 #0b080d, stop:1 #050406);
    border: 2px solid #8c7047;
    border-radius: 8px;
    color: #eadfca;
  }
]]

local INNER_FRAME = [[
  QLabel {
    background-color: rgba(8, 6, 10, 225);
    border: 1px solid #3f3344;
    border-radius: 5px;
    color: #eadfca;
  }
]]

local TITLE_STYLE = [[
  QLabel {
    background-color: transparent;
    color: #e3c99a;
    font-size: 12pt;
    font-weight: bold;
    qproperty-alignment: 'AlignCenter';
  }
]]

local SUBTITLE_STYLE = [[
  QLabel {
    background-color: transparent;
    color: #a99cad;
    font-size: 9pt;
    qproperty-alignment: 'AlignCenter';
  }
]]

local ORNAMENT_STYLE = [[
  QLabel {
    background-color: transparent;
    color: #705937;
    font-size: 12pt;
    qproperty-alignment: 'AlignCenter';
  }
]]

local GAUGE_TEXT_STYLE = [[
  QLabel {
    background-color: transparent;
    color: #fff9ef;
    font-size: 9pt;
    font-weight: bold;
    qproperty-alignment: 'AlignCenter';
  }
]]

local HP_FRONT = [[
  background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4d0710, stop:0.45 #9d1628, stop:1 #d62b3d);
  border: 1px solid #d99b82;
  border-radius: 5px;
]]
local HP_BACK = [[
  background-color: #1b080d;
  border: 1px solid #4a222a;
  border-radius: 5px;
]]
local MANA_FRONT = [[
  background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #07183f, stop:0.45 #123f91, stop:1 #2868d7);
  border: 1px solid #8ba8e6;
  border-radius: 5px;
]]
local MANA_BACK = [[
  background-color: #070d1c;
  border: 1px solid #1c315c;
  border-radius: 5px;
]]
local MOVE_FRONT = [[
  background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0b321c, stop:0.45 #187441, stop:1 #32a85e);
  border: 1px solid #8bc99d;
  border-radius: 5px;
]]
local MOVE_BACK = [[
  background-color: #08150d;
  border: 1px solid #23492d;
  border-radius: 5px;
]]
local TARGET_FRONT = [[
  background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #3a0710, stop:0.55 #821527, stop:1 #c52e42);
  border: 1px solid #c88978;
  border-radius: 5px;
]]
local TARGET_BACK = [[
  background-color: #16070a;
  border: 1px solid #49212a;
  border-radius: 5px;
]]

local function styleGauge(gauge, front, back)
  gauge.front:setStyleSheet(front)
  gauge.back:setStyleSheet(back)
  gauge.text:setStyleSheet(GAUGE_TEXT_STYLE)
end

function H.build()
  if H.built then return end

  -- Reserve real border space so game text never renders underneath the HUD.
  setBorderTop(math.max(getBorderTop(), 142))
  setBorderRight(math.max(getBorderRight(), 330))
  setBorderColor(7, 5, 8)

  H.topFrame = Geyser.Label:new({
    name = "DreamsHUD.TopFrame",
    x = "8%", y = 8,
    width = "62%", height = 126,
  })
  H.topFrame:setStyleSheet(OUTER_FRAME)

  H.topInner = Geyser.Label:new({
    name = "DreamsHUD.TopInner",
    x = "1%", y = "5%",
    width = "98%", height = "90%",
  }, H.topFrame)
  H.topInner:setStyleSheet(INNER_FRAME)

  H.leftOrnament = Geyser.Label:new({
    name = "DreamsHUD.LeftOrnament",
    x = "2%", y = 3,
    width = "19%", height = 22,
  }, H.topInner)
  H.leftOrnament:setStyleSheet(ORNAMENT_STYLE)
  H.leftOrnament:echo("<center>◆ ── † ── ◆</center>")

  H.rightOrnament = Geyser.Label:new({
    name = "DreamsHUD.RightOrnament",
    x = "79%", y = 3,
    width = "19%", height = 22,
  }, H.topInner)
  H.rightOrnament:setStyleSheet(ORNAMENT_STYLE)
  H.rightOrnament:echo("<center>◆ ── † ── ◆</center>")

  H.title = Geyser.Label:new({
    name = "DreamsHUD.Title",
    x = "21%", y = 2,
    width = "58%", height = 22,
  }, H.topInner)
  H.title:setStyleSheet(TITLE_STYLE)
  H.title:echo("<center>DREAMS OF THE FALLEN</center>")

  H.character = Geyser.Label:new({
    name = "DreamsHUD.Character",
    x = "5%", y = 24,
    width = "90%", height = 17,
  }, H.topInner)
  H.character:setStyleSheet(SUBTITLE_STYLE)

  H.hp = Geyser.Gauge:new({
    name = "DreamsHUD.Health",
    x = "6%", y = 43,
    width = "88%", height = 18,
  }, H.topInner)
  styleGauge(H.hp, HP_FRONT, HP_BACK)

  H.mana = Geyser.Gauge:new({
    name = "DreamsHUD.Mana",
    x = "6%", y = 66,
    width = "88%", height = 18,
  }, H.topInner)
  styleGauge(H.mana, MANA_FRONT, MANA_BACK)

  H.movement = Geyser.Gauge:new({
    name = "DreamsHUD.Movement",
    x = "6%", y = 89,
    width = "88%", height = 18,
  }, H.topInner)
  styleGauge(H.movement, MOVE_FRONT, MOVE_BACK)

  H.targetFrame = Geyser.Label:new({
    name = "DreamsHUD.TargetFrame",
    x = -318, y = 15,
    width = 304, height = 232,
  })
  H.targetFrame:setStyleSheet(OUTER_FRAME)

  H.targetInner = Geyser.Label:new({
    name = "DreamsHUD.TargetInner",
    x = "3%", y = "3%",
    width = "94%", height = "94%",
  }, H.targetFrame)
  H.targetInner:setStyleSheet(INNER_FRAME)

  H.targetCrown = Geyser.Label:new({
    name = "DreamsHUD.TargetCrown",
    x = "5%", y = 5,
    width = "90%", height = 20,
  }, H.targetInner)
  H.targetCrown:setStyleSheet(ORNAMENT_STYLE)
  H.targetCrown:echo("<center>✦ ━━━ † TARGET † ━━━ ✦</center>")

  H.targetName = Geyser.Label:new({
    name = "DreamsHUD.TargetName",
    x = "5%", y = 32,
    width = "90%", height = 28,
  }, H.targetInner)
  H.targetName:setStyleSheet(TITLE_STYLE)

  H.targetGauge = Geyser.Gauge:new({
    name = "DreamsHUD.TargetHealth",
    x = "8%", y = 68,
    width = "84%", height = 22,
  }, H.targetInner)
  styleGauge(H.targetGauge, TARGET_FRONT, TARGET_BACK)

  H.targetDetail = Geyser.Label:new({
    name = "DreamsHUD.TargetDetail",
    x = "6%", y = 98,
    width = "88%", height = 24,
  }, H.targetInner)
  H.targetDetail:setStyleSheet(SUBTITLE_STYLE)

  H.targetSigil = Geyser.Label:new({
    name = "DreamsHUD.TargetSigil",
    x = "12%", y = 128,
    width = "76%", height = 66,
  }, H.targetInner)
  H.targetSigil:setStyleSheet([[
    QLabel {
      background-color: rgba(13, 9, 15, 180);
      border: 1px solid #352a39;
      border-radius: 6px;
      color: #685573;
      font-size: 14pt;
      qproperty-alignment: 'AlignCenter';
    }
  ]])
  H.targetSigil:echo("<center>◇<br/>†<br/>◇</center>")

  H.built = true
  H.renderAll()
end

function H.renderVitals()
  if not H.built then return end
  local s = H.state
  s.max_hp = safeMax(s.max_hp)
  s.max_mana = safeMax(s.max_mana)
  s.max_movement = safeMax(s.max_movement)
  s.hp = clamp(s.hp, 0, s.max_hp)
  s.mana = clamp(s.mana, 0, s.max_mana)
  s.movement = clamp(s.movement, 0, s.max_movement)

  H.hp:setValue(s.hp, s.max_hp)
  H.hp.text:echo(string.format("<center>HEALTH  %d / %d</center>", s.hp, s.max_hp))
  H.mana:setValue(s.mana, s.max_mana)
  H.mana.text:echo(string.format("<center>MANA  %d / %d</center>", s.mana, s.max_mana))
  H.movement:setValue(s.movement, s.max_movement)
  H.movement.text:echo(string.format("<center>MOVEMENT  %d / %d</center>", s.movement, s.max_movement))
end

function H.renderCharacter()
  if not H.built then return end
  local s = H.state
  local bits = {}
  if s.character_name and s.character_name ~= "" then table.insert(bits, escapeHtml(s.character_name)) end
  if s.character_level and tostring(s.character_level) ~= "" then table.insert(bits, "Level " .. escapeHtml(s.character_level)) end
  if s.character_race and s.character_race ~= "" then table.insert(bits, escapeHtml(s.character_race)) end
  if s.character_class and s.character_class ~= "" then table.insert(bits, escapeHtml(s.character_class)) end
  H.character:echo("<center>" .. table.concat(bits, "  •  ") .. "</center>")
end

function H.renderTarget()
  if not H.built then return end
  local s = H.state
  if not s.target_active or not s.target_name or s.target_name == "" then
    H.targetName:echo("<center>NO TARGET</center>")
    H.targetGauge:setValue(0, 1)
    H.targetGauge.text:echo("<center>—</center>")
    H.targetDetail:echo("<center>The dark is watching.</center>")
    H.targetSigil:echo("<center>◇<br/>†<br/>◇</center>")
    return
  end

  s.target_max_hp = safeMax(s.target_max_hp)
  s.target_hp = clamp(s.target_hp, 0, s.target_max_hp)
  local pct = math.floor((s.target_hp / s.target_max_hp) * 100 + 0.5)
  H.targetName:echo("<center>" .. escapeHtml(s.target_name) .. "</center>")
  H.targetGauge:setValue(s.target_hp, s.target_max_hp)
  H.targetGauge.text:echo(string.format("<center>%d%%</center>", pct))
  H.targetDetail:echo(string.format("<center>HEALTH  %d / %d</center>", s.target_hp, s.target_max_hp))
  H.targetSigil:echo("<center>✦<br/>†<br/>✦</center>")
end

function H.renderAll()
  H.renderCharacter()
  H.renderVitals()
  H.renderTarget()
end

function H.onVitals()
  local v = gmcp and gmcp.Dreams and gmcp.Dreams.Vitals
  if not v then return end
  H.state.hp = tonumber(v.hp) or H.state.hp
  H.state.max_hp = tonumber(v.max_hp) or H.state.max_hp
  H.state.mana = tonumber(v.mana) or H.state.mana
  H.state.max_mana = tonumber(v.max_mana) or H.state.max_mana
  H.state.movement = tonumber(v.movement) or H.state.movement
  H.state.max_movement = tonumber(v.max_movement) or H.state.max_movement
  H.renderVitals()
end

function H.onTarget()
  local t = gmcp and gmcp.Dreams and gmcp.Dreams.Target
  if not t then return end
  H.state.target_name = tostring(t.name or "")
  H.state.target_hp = tonumber(t.hp) or 0
  H.state.target_max_hp = tonumber(t.max_hp) or 1
  H.state.target_active = t.active == true
  H.renderTarget()
end

function H.onStatus()
  local s = gmcp and gmcp.Char and gmcp.Char.Status
  if not s then return end
  H.state.character_name = tostring(s.name or H.state.character_name)
  H.state.character_level = tostring(s.level or H.state.character_level)
  H.state.character_race = tostring(s.race or H.state.character_race)
  H.state.character_class = tostring(s.class or H.state.character_class)
  H.renderCharacter()
end

function H.registerHandlers()
  if H.handlers.vitals then killAnonymousEventHandler(H.handlers.vitals) end
  if H.handlers.target then killAnonymousEventHandler(H.handlers.target) end
  if H.handlers.status then killAnonymousEventHandler(H.handlers.status) end
  if H.handlers.load then killAnonymousEventHandler(H.handlers.load) end

  H.handlers.vitals = registerAnonymousEventHandler("gmcp.Dreams.Vitals", H.onVitals)
  H.handlers.target = registerAnonymousEventHandler("gmcp.Dreams.Target", H.onTarget)
  H.handlers.status = registerAnonymousEventHandler("gmcp.Char.Status", H.onStatus)
  H.handlers.load = registerAnonymousEventHandler("sysLoadEvent", function()
    H.build()
    H.renderAll()
  end)
end

function H.init()
  H.build()
  H.registerHandlers()
  H.renderAll()
end

H.init()
