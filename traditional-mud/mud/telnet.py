from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

from mud.client_gui import configured_mudlet_gui_offer

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
    client_gui_offer_sent: bool = False

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

        # Client.GUI should be offered only once per connection. PlayerSession
        # also contains a later fallback offer, so keeping this guard in the
        # Telnet layer prevents duplicate downloads when GMCP negotiation works
        # normally and the immediate offer has already been sent.
        if package == "Client.GUI" and self.client_gui_offer_sent:
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

        if package == "Client.GUI":
            self.client_gui_offer_sent = True

        return True

    async def _offer_official_mudlet_hud(self) -> bool:
        """Offer the official Dreams of the Fallen Mudlet HUD immediately.

        Mudlet's Client.GUI extension is handled as GMCP. Sending this as soon
        as the client answers DO GMCP lets a first-time Mudlet connection begin
        downloading/installing the official package before account login rather
        than waiting until the player submits a later command.
        """
        if self.client_gui_offer_sent:
            return False

        offer = configured_mudlet_gui_offer()
        if not offer.enabled:
            return False

        return await self.send_gmcp(
            "Client.GUI",
            {
                "version": offer.version,
                "url": offer.url,
            },
        )

    async def _enable_gmcp(self) -> None:
        """Enable GMCP and perform one-time post-negotiation setup."""
        was_enabled = self.gmcp_enabled
        self.gmcp_enabled = True
        if not was_enabled:
            await self._offer_official_mudlet_hud()

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
                    # This is the critical moment for Mudlet: it has accepted
                    # the server's WILL GMCP. Enable GMCP and immediately send
                    # the Client.GUI package offer instead of waiting for a
                    # later player prompt/command cycle.
                    await self._enable_gmcp()
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
                # Some clients may send GMCP subnegotiation immediately. Treat
                # that as confirmation that GMCP is active and make the same
                # one-time GUI offer if DO GMCP was not observed first.
                await self._enable_gmcp()
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
