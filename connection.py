"""Scan BLE devices and manage this program's connection from the PC.

Run with: python connection.py
Requires Bleak (install with: python -m pip install bleak).
The target must be a Bluetooth Low Energy (BLE) GATT peripheral.
"""

import asyncio

from bleak import BleakClient, BleakScanner


SCAN_TIMEOUT = 8.0
CONNECT_TIMEOUT = 30.0
DISCONNECT_TIMEOUT = 10.0


async def ask(prompt):
    """Wait for input without blocking Bluetooth callbacks."""
    return (await asyncio.to_thread(input, prompt)).strip()


async def list_nearby_devices():
    """Return nearby advertising BLE devices."""
    print(f"Searching for nearby BLE devices for {SCAN_TIMEOUT:g} seconds...")
    try:
        devices = await BleakScanner.discover(timeout=SCAN_TIMEOUT)
    except Exception as err:
        # Bluetooth backends can raise OS-specific exceptions as well.
        print(f"Scan failed: {type(err).__name__}: {err}")
        print("Check that Bluetooth is enabled and your adapter supports BLE.")
        return []

    if not devices:
        print("No advertising BLE devices found.")
    else:
        print(f"Found {len(devices)} BLE device(s):")
        for number, device in enumerate(devices, start=1):
            print(f"  {number}. {device.address} - {device.name or 'Unnamed device'}")
    return devices


async def disconnect_device(client, announce=True):
    """Disconnect our client, retaining it if cleanup fails so we can retry."""
    if client is None:
        if announce:
            print("This program has no BLE connection to disconnect.")
        return None

    try:
        # Clean up even if the remote peripheral has already disconnected.
        await asyncio.wait_for(client.disconnect(), timeout=DISCONNECT_TIMEOUT)
    except Exception as err:
        print(f"Disconnect failed: {type(err).__name__}: {err}")
        return client

    if announce:
        print(f"Closed this program's BLE connection to {client.address}.")
    return None


async def reconnect_device(device):
    """Connect using a BLEDevice returned by a recent scan."""
    client = None
    connected = False
    try:
        client = BleakClient(device)
        print(f"Connecting this PC to {device.address}...")
        await asyncio.wait_for(client.connect(), timeout=CONNECT_TIMEOUT)
        # Bleak connect() returns None; check the connection property instead.
        if not client.is_connected:
            raise RuntimeError("The peripheral did not remain connected.")
        connected = True
        print(f"Connected to {device.name or 'Unnamed device'} ({device.address}).")
    except Exception as err:
        print(f"Connection failed: {type(err).__name__}: {err}")
        print("The peripheral must support BLE GATT and accept connections.")
    finally:
        # Also clean up a partially opened or cancelled connection.
        if client is not None and not connected:
            client = await disconnect_device(client, announce=False)
    return client


def select_device(devices, selection):
    """Accept a displayed number or address, without trusting arbitrary input."""
    selection = selection.strip()
    for number, device in enumerate(devices, start=1):
        if selection == str(number) or selection.casefold() == device.address.casefold():
            return device
    return None


async def main():
    client = None
    print("BLE controls manage this program's connection from your PC.")
    try:
        while True:
            print("\nBluetooth Interactions Menu:")
            print("1. List nearby BLE devices")
            print("2. Disconnect this program's BLE connection")
            print("3. Connect / reconnect this PC to a BLE device")
            print("4. Exit")
            choice = await ask("Enter your choice (1-4): ")

            if choice in {"1", "3"} and client is not None:
                if client.is_connected:
                    print(f"Already connected to {client.address}. Use option 2 first.")
                    continue
                client = await disconnect_device(client, announce=False)
                if client is not None:
                    print("Use option 2 to retry connection cleanup first.")
                    continue

            if choice == "1":
                await list_nearby_devices()
            elif choice == "2":
                client = await disconnect_device(client)
            elif choice == "3":
                devices = await list_nearby_devices()
                if not devices:
                    continue
                selection = await ask("Enter a device number or its listed address: ")
                device = select_device(devices, selection)
                if device is None:
                    print("Invalid selection. Choose a device from the scan results.")
                    continue
                client = await reconnect_device(device)
            elif choice == "4":
                break
            else:
                print("Invalid choice. Enter 1, 2, 3, or 4.")
    except EOFError:
        print("\nConsole input ended.")
    finally:
        if client is not None:
            await disconnect_device(client)
        print("Exiting...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
