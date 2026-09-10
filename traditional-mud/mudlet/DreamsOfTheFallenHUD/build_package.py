from __future__ import annotations

import html
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LUA_PATH = ROOT / "src" / "hud.lua"
XML_PATH = ROOT / "DreamsOfTheFallenHUD.xml"
PACKAGE_PATH = ROOT / "DreamsOfTheFallenHUD.mpackage"
CONFIG_PATH = ROOT / "config.lua"


def build_xml(lua: str) -> str:
    escaped = html.escape(lua, quote=False)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE MudletPackage>
<MudletPackage version="1.001">
  <TriggerPackage />
  <TimerPackage />
  <AliasPackage />
  <ActionPackage />
  <ScriptPackage>
    <ScriptGroup isActive="yes" isFolder="yes">
      <name>DreamsOfTheFallenHUD</name>
      <packageName>DreamsOfTheFallenHUD</packageName>
      <script></script>
      <eventHandlerList />
      <Script isActive="yes" isFolder="no">
        <name>Dreams of the Fallen Official HUD</name>
        <packageName>DreamsOfTheFallenHUD</packageName>
        <script>{escaped}</script>
        <eventHandlerList />
      </Script>
    </ScriptGroup>
  </ScriptPackage>
  <KeyPackage />
  <VariablePackage><HiddenVariables /></VariablePackage>
</MudletPackage>
'''


def main() -> None:
    lua = LUA_PATH.read_text(encoding="utf-8")
    XML_PATH.write_text(build_xml(lua), encoding="utf-8")
    with zipfile.ZipFile(PACKAGE_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(XML_PATH, XML_PATH.name)
        zf.write(CONFIG_PATH, CONFIG_PATH.name)
    print(PACKAGE_PATH)


if __name__ == "__main__":
    main()
