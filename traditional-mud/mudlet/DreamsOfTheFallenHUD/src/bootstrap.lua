-- Dreams of the Fallen HUD runtime-install bootstrap
--
-- Client.GUI can install or upgrade a package after the Mudlet profile has
-- already finished its normal script-load pass. In that case the Script item is
-- present and active but its top-level initialization has not run yet. This
-- trigger fires on the first subsequent server line, loads the installed HUD
-- Script once, and then disables itself.

local BOOTSTRAP_TRIGGER = "DreamsOfTheFallenHUD Bootstrap"
local HUD_SCRIPT = "Dreams of the Fallen Official HUD"

local function reportOnce(message)
  if DreamsHUDBootstrapErrorShown then return end
  DreamsHUDBootstrapErrorShown = true
  if cecho then
    cecho("\n<red>Dreams HUD startup failed: " .. tostring(message) .. "<reset>\n")
  else
    print("Dreams HUD startup failed: " .. tostring(message))
  end
end

local function startInstalledHud()
  if type(DreamsHUD) == "table" then
    if disableTrigger then disableTrigger(BOOTSTRAP_TRIGGER) end
    return
  end

  local source = getScript and getScript(HUD_SCRIPT) or nil
  if type(source) ~= "string" or source == "" then
    reportOnce("installed HUD script could not be read")
    return
  end

  local chunk, compileError = loadstring(source)
  if not chunk then
    reportOnce(compileError)
    return
  end

  local ok, runtimeError = pcall(chunk)
  if not ok then
    reportOnce(runtimeError)
    return
  end

  if type(DreamsHUD) ~= "table" then
    reportOnce("HUD script completed without creating DreamsHUD")
    return
  end

  DreamsHUDBootstrapErrorShown = nil
  if disableTrigger then disableTrigger(BOOTSTRAP_TRIGGER) end
end

startInstalledHud()
