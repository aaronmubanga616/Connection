"""Regression checks; Bluetooth connections are simulated, not opened."""

import asyncio
import contextlib
import io
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import connection


class ConnectionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.output = io.StringIO()
        redirect = contextlib.redirect_stdout(self.output)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)
        self.device = SimpleNamespace(address="AA:BB:CC:DD:EE:FF", name=None)
        self.client = SimpleNamespace(
            address=self.device.address,
            is_connected=True,
            connect=AsyncMock(),
            disconnect=AsyncMock(),
        )

    async def test_scan_displays_unnamed_devices(self):
        with patch.object(connection.BleakScanner, "discover", AsyncMock(return_value=[self.device])):
            self.assertEqual(await connection.list_nearby_devices(), [self.device])
        self.assertIn("Unnamed device", self.output.getvalue())

    async def test_empty_scan(self):
        with patch.object(connection.BleakScanner, "discover", AsyncMock(return_value=[])):
            self.assertEqual(await connection.list_nearby_devices(), [])
        self.assertIn("No advertising BLE devices", self.output.getvalue())

    async def test_scan_failure_keeps_menu_usable(self):
        with patch.object(connection.BleakScanner, "discover", AsyncMock(side_effect=OSError("Bluetooth off"))), \
                patch.object(connection, "ask", AsyncMock(side_effect=["1", "4"])):
            await connection.main()
        self.assertIn("Scan failed", self.output.getvalue())
        self.assertIn("Exiting...", self.output.getvalue())

    async def test_connect_checks_property_and_returns_client(self):
        with patch.object(connection, "BleakClient", return_value=self.client):
            self.assertIs(await connection.reconnect_device(self.device), self.client)
        self.client.connect.assert_awaited_once()
        self.client.disconnect.assert_not_awaited()

    async def test_constructor_failure_is_reported(self):
        with patch.object(connection, "BleakClient", side_effect=OSError("Adapter missing")):
            self.assertIsNone(await connection.reconnect_device(self.device))
        self.assertIn("Connection failed", self.output.getvalue())

    async def test_connect_failure_cleans_partial_connection(self):
        self.client.connect.side_effect = OSError("Unreachable")
        with patch.object(connection, "BleakClient", return_value=self.client):
            self.assertIsNone(await connection.reconnect_device(self.device))
        self.client.disconnect.assert_awaited_once()

    async def test_connect_timeout_cleans_partial_connection(self):
        async def slow_connect():
            await asyncio.sleep(60)
        self.client.connect.side_effect = slow_connect
        with patch.object(connection, "BleakClient", return_value=self.client), \
                patch.object(connection, "CONNECT_TIMEOUT", 0.01):
            self.assertIsNone(await connection.reconnect_device(self.device))
        self.client.disconnect.assert_awaited_once()
        self.assertIn("TimeoutError", self.output.getvalue())

    async def test_cancelled_connect_cleans_partial_connection(self):
        self.client.connect.side_effect = asyncio.CancelledError
        with patch.object(connection, "BleakClient", return_value=self.client):
            with self.assertRaises(asyncio.CancelledError):
                await connection.reconnect_device(self.device)
        self.client.disconnect.assert_awaited_once()

    async def test_lost_connection_is_not_reported_as_success(self):
        self.client.is_connected = False
        with patch.object(connection, "BleakClient", return_value=self.client):
            self.assertIsNone(await connection.reconnect_device(self.device))
        self.client.disconnect.assert_awaited_once()
        self.assertIn("did not remain connected", self.output.getvalue())

    async def test_failed_cleanup_retains_client_for_retry(self):
        self.client.connect.side_effect = OSError("Unreachable")
        self.client.disconnect.side_effect = OSError("Busy")
        with patch.object(connection, "BleakClient", return_value=self.client):
            self.assertIs(await connection.reconnect_device(self.device), self.client)
        self.client.disconnect.side_effect = None
        self.assertIsNone(await connection.disconnect_device(self.client))
        self.assertEqual(self.client.disconnect.await_count, 2)

    async def test_disconnect_timeout_retains_client(self):
        async def slow_disconnect():
            await asyncio.sleep(60)
        self.client.disconnect.side_effect = slow_disconnect
        with patch.object(connection, "DISCONNECT_TIMEOUT", 0.01):
            self.assertIs(await connection.disconnect_device(self.client), self.client)
        self.assertIn("TimeoutError", self.output.getvalue())

    async def test_disconnect_without_connection(self):
        self.assertIsNone(await connection.disconnect_device(None))
        self.assertIn("no BLE connection", self.output.getvalue())

    async def test_main_connection_blocks_additional_scan_until_disconnect(self):
        with patch.object(connection, "ask", AsyncMock(side_effect=["3", "1", "1", "3", "2", "4"])), \
                patch.object(connection, "list_nearby_devices", AsyncMock(return_value=[self.device])) as scan, \
                patch.object(connection, "BleakClient", return_value=self.client):
            await connection.main()
        scan.assert_awaited_once()
        self.client.connect.assert_awaited_once()
        self.client.disconnect.assert_awaited_once()
        self.assertIn("Already connected", self.output.getvalue())

    async def test_eof_disconnects_existing_connection(self):
        with patch.object(connection, "ask", AsyncMock(side_effect=["3", "1", EOFError()])), \
                patch.object(connection, "list_nearby_devices", AsyncMock(return_value=[self.device])), \
                patch.object(connection, "BleakClient", return_value=self.client):
            await connection.main()
        self.client.disconnect.assert_awaited_once()
        self.assertIn("Console input ended", self.output.getvalue())

    async def test_invalid_device_selection_does_not_connect(self):
        with patch.object(connection, "ask", AsyncMock(side_effect=["3", "999", "4"])), \
                patch.object(connection, "list_nearby_devices", AsyncMock(return_value=[self.device])), \
                patch.object(connection, "BleakClient") as constructor:
            await connection.main()
        constructor.assert_not_called()
        self.assertIn("Invalid selection", self.output.getvalue())

    async def test_empty_scan_does_not_prompt_for_device(self):
        with patch.object(connection, "ask", AsyncMock(side_effect=["3", "4"])) as ask, \
                patch.object(connection, "list_nearby_devices", AsyncMock(return_value=[])), \
                patch.object(connection, "BleakClient") as constructor:
            await connection.main()
        self.assertEqual(ask.await_count, 2)
        constructor.assert_not_called()

    def test_device_selection_handles_number_address_and_bad_input(self):
        self.assertIs(connection.select_device([self.device], " 1 "), self.device)
        self.assertIs(connection.select_device([self.device], self.device.address.lower()), self.device)
        for value in ("", "0", "-1", "unknown", "9" * 5000):
            self.assertIsNone(connection.select_device([self.device], value))


if __name__ == "__main__":
    unittest.main()
