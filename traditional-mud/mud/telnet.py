from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

# Telnet command bytes.
IAC = 255
DONT = 254
DO = 253
WONT = 252
WILL = 251
SB = 250
SE = 240

# Generic Mud Communication Protocol (GMCP).
GMCP = 201


@dataclass(slots=True)
class TelnetConnection:
    """Minimal Telnet protocol layer with GMCP support.

    Dreams of the Fallen remains a normal Telnet MUD. Clients that negotiate
    GMCP receive structured out-of-band data; clients that do not simply see
    the ordinary text game.
    """

    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    gmcp_enabled: bool = False
    client_name: str | None = None
    client_version: str | None = None
    gmcp_packages: set[str] = field(default_factory=set)

    async def begin_negotiation(self) -> None:
        # Advertise server-side GMCP support. A supporting client replies DO GMCP.
        self.writer.write(bytes((IAC, WILL, GMCP)))
        await self.writer.drain()

    async def send_text(self, text: str) -> None:
        self.writer.write(text.encode("utf-8", errors="replace"))
        await self.writer.drain()

    async def send_gmcp(self, package: str, payload: dict | list | str | int | float | bool | None = None) -> bool:
        if not self.gmcp_enabled:
            return False
        body = package
        if payload is not None:
            if isinstance(payload, str):
                encoded_payload = payload
            else:
                encoded_payload = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
            body += " " + encoded_payload
        raw = body.encode("utf-8", errors="replace").replace(bytes((IAC,)), bytes((IAC, IAC)))
        self.writer.write(bytes((IAC, SB, GMCP)) + raw + bytes((IAC, SE)))
        await self.writer.drain()
        return True

    async def read_line(self) -> str | None:
        """Read one player text line while consuming Telnet negotiations.

        This prevents protocol bytes from leaking into account names/commands
        when a real MUD client such as Mudlet negotiates GMCP on connect.
        """
        line = bytearray()
        while True:
            byte = await self.reader.read(1)
            if not byte:
                if not line:
                    return None
                break
            value = byte[0]
            if value == IAC:
                await self._consume_iac()
                continue
            if value == 10:  # LF
                break
            if value == 13:  # CR
                continue
            line.append(value)
        return line.decode("utf-8", errors="ignore").strip()

    async def _consume_iac(self) -> None:
        command_b = await self.reader.read(1)
        if not command_b:
            return
        command = command_b[0]

        if command == IAC:
            return

        if command in {DO, DONT, WILL, WONT}:
            option_b = await self.reader.read(1)
            if not option_b:
                return
            option = option_b[0]
            if option == GMCP:
                if command == DO:
                    self.gmcp_enabled = True
                elif command == DONT:
                    self.gmcp_enabled = False
            return

        if command == SB:
            option_b = await self.reader.read(1)
            if not option_b:
                return
            option = option_b[0]
            payload = await self._read_subnegotiation_payload()
            if option == GMCP:
                self.gmcp_enabled = True
                self._handle_gmcp_from_client(payload)
            return

    async def _read_subnegotiation_payload(self) -> bytes:
        data = bytearray()
        while True:
            byte = await self.reader.read(1)
            if not byte:
                break
            if byte[0] != IAC:
                data.extend(byte)
                continue
            next_b = await self.reader.read(1)
            if not next_b:
                break
            if next_b[0] == IAC:
                data.append(IAC)
                continue
            if next_b[0] == SE:
                break
            # Ignore unexpected command sequences inside subnegotiation.
        return bytes(data)

    def _handle_gmcp_from_client(self, payload: bytes) -> None:
        text = payload.decode("utf-8", errors="ignore").strip()
        if not text:
            return
        package, _, json_text = text.partition(" ")
        if package == "Core.Hello" and json_text:
            try:
                hello = json.loads(json_text)
            except json.JSONDecodeError:
                return
            if isinstance(hello, dict):
                client = hello.get("client")
                version = hello.get("version")
                self.client_name = str(client) if client is not None else None
                self.client_version = str(version) if version is not None else None
        elif package in {"Core.Supports.Set", "Core.Supports.Add"} and json_text:
            try:
                supported = json.loads(json_text)
            except json.JSONDecodeError:
                return
            if isinstance(supported, list):
                if package == "Core.Supports.Set":
                    self.gmcp_packages.clear()
                self.gmcp_packages.update(str(value) for value in supported)
