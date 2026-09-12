from __future__ import annotations

import html
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_PATHS = (
    ROOT / "src" / "hud.lua",
    ROOT / "src" / "modern.lua",
)
XML_PATH = ROOT / "DreamsOfTheFallenHUD.xml"
PACKAGE_PATH = ROOT / "DreamsOfTheFallenHUD.mpackage"
CONFIG_PATH = ROOT / "config.lua"


def combined_lua() -> str:
    chunks = []
    for path in SOURCE_PATHS:
        chunks.append(f"-- BEGIN {path.name}\n" + path.read_text(encoding="utf-8").rstrip() + f"\n-- END {path.name}")
    return "\n\n".join(chunks) + "\n"


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


def build() -> Path:
    lua = combined_lua()
    XML_PATH.write_text(build_xml(lua), encoding="utf-8")
    with zipfile.ZipFile(PACKAGE_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(XML_PATH, XML_PATH.name)
        zf.write(CONFIG_PATH, CONFIG_PATH.name)
    return PACKAGE_PATH


def main() -> None:
    print(build())


if __name__ == "__main__":
    main()
