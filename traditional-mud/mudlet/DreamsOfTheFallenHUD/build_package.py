from __future__ import annotations

import html
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_PATHS = (
    ROOT / "src" / "hud.lua",
    ROOT / "src" / "modern.lua",
    ROOT / "src" / "map.lua",
)
BOOTSTRAP_PATH = ROOT / "src" / "bootstrap.lua"
XML_PATH = ROOT / "DreamsOfTheFallenHUD.xml"
PACKAGE_PATH = ROOT / "DreamsOfTheFallenHUD.mpackage"
CONFIG_PATH = ROOT / "config.lua"
DISTRIBUTION_PATH = ROOT.parents[2] / "DreamsOfTheFallenHUD.mpackage"


def combined_lua() -> str:
    chunks = []
    for path in SOURCE_PATHS:
        chunks.append(f"-- BEGIN {path.name}\n" + path.read_text(encoding="utf-8").rstrip() + f"\n-- END {path.name}")
    return "\n\n".join(chunks) + "\n"


def build_xml(lua: str, bootstrap: str) -> str:
    escaped = html.escape(lua, quote=False)
    bootstrap_escaped = html.escape(bootstrap, quote=False)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE MudletPackage>
<MudletPackage version="1.001">
  <TriggerPackage>
    <Trigger isActive="yes" isFolder="no" isTempTrigger="no" isMultiline="no" isPerlSlashGOption="no" isColorizerTrigger="no" isFilterTrigger="no" isSoundTrigger="no" isColorTrigger="no" isColorTriggerFg="no" isColorTriggerBg="no">
      <name>DreamsOfTheFallenHUD Bootstrap</name>
      <script>{bootstrap_escaped}</script>
      <triggerType>0</triggerType>
      <conditonLineDelta>0</conditonLineDelta>
      <mStayOpen>0</mStayOpen>
      <mCommand></mCommand>
      <packageName>DreamsOfTheFallenHUD</packageName>
      <mFgColor>#ff0000</mFgColor>
      <mBgColor>#ffff00</mBgColor>
      <mSoundFile></mSoundFile>
      <colorTriggerFgColor>#000000</colorTriggerFgColor>
      <colorTriggerBgColor>#000000</colorTriggerBgColor>
      <regexCodeList>
        <string>^.*$</string>
      </regexCodeList>
      <regexCodePropertyList>
        <integer>1</integer>
      </regexCodePropertyList>
    </Trigger>
  </TriggerPackage>
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
    bootstrap = BOOTSTRAP_PATH.read_text(encoding="utf-8")
    XML_PATH.write_text(build_xml(lua, bootstrap), encoding="utf-8")
    with zipfile.ZipFile(PACKAGE_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(XML_PATH, XML_PATH.name)
        zf.write(CONFIG_PATH, CONFIG_PATH.name)
    shutil.copyfile(PACKAGE_PATH, DISTRIBUTION_PATH)
    return PACKAGE_PATH


def main() -> None:
    print(build())


if __name__ == "__main__":
    main()
