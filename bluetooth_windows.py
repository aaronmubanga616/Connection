r"""Scan BLE devices and manage this program's own BLE connection.

Windows / VS Code setup, from the folder containing this file:
    py -m venv .venv
    .\.venv\Scripts\python.exe -m pip install "bleak==2.1.1"
    .\.venv\Scripts\python.exe bluetooth_windows.py

Use a current Python version (3.10 or newer) and a BLE-capable adapter.
Bleak 2.1.1 is pinned to retain Windows 10 support.
Turn Bluetooth on and make the target BLE peripheral advertise.
This program does not control Bluetooth Classic speaker/audio connections
or the connection between a phone and a speaker.

Official API documentation:
    https://bleak.readthedocs.io/en/stable/api/scanner.html
    https://bleak.readthedocs.io/en/stable/api/client.html
"""

import asyncio

from bleak import BleakClient, BleakScanner


async def ask(prompt):
    """Keep the event loop running while waiting for keyboard input."""
    return (await asyncio.to_thread(input, prompt)).strip()


async def list_nearby_devices():
    """Return BLEDevice objects for nearby advertising BLE peripherals."""
    print("Searching for nearby BLE devices for 8 seconds...")
    try:
        devices = await BleakScanner.discover(timeout=8.0)
    except Exception as err:
        # Windows Bluetooth backends can also raise OS-specific exceptions.
        print(f"Scan failed: {type(err).__name__}: {err}")
        print("Check that Bluetooth is enabled and your adapter supports BLE.")
        return []

    if not devices:
        print("No advertising BLE devices found.")
        return []

    print(f"Found {len(devices)} BLE device(s):")
    for number, device in enumerate(devices, start=1):
        print(f"  {number}. {device.address} - {device.name or 'Unnamed device'}")
    return devices


async def disconnect_device(client, announce=True):
    """Close our connection; retain the client if cleanup fails so we can retry."""
    if client is None:
        if announce:
            print("This program has no BLE connection to disconnect.")
        return None

    try:
        # Also clean up a client whose remote device has already disconnected.
        await asyncio.wait_for(client.disconnect(), timeout=10.0)
    except Exception as err:
        print(f"Disconnect failed: {type(err).__name__}: {err}")
        return client

    if announce:
        print(f"Closed this program's BLE connection to {client.address}.")
    return None


async def reconnect_device(device):
    """Connect this PC to a BLE peripheral returned by the scanner."""
    client = BleakClient(device)
    connected = False
    try:
        print(f"Connecting this PC to {device.address}...")
        await asyncio.wait_for(client.connect(), timeout=30.0)
        # connect() returns None; use the property to check connection status.
        if not client.is_connected:
            raise RuntimeError("The peripheral did not remain connected.")
        connected = True
        print(f"Connected to {device.name or 'Unnamed device'} ({device.address}).")
        return client
    except Exception as err:
        print(f"Connection failed: {type(err).__name__}: {err}")
        print("The peripheral must support BLE GATT and accept connections.")
    finally:
        # This also runs if an in-progress connection is cancelled.
        if not connected:
            client = await disconnect_device(client, announce=False)

    return client


def select_device(devices, selection):
    """Accept either a list number or an address from the last scan."""
    if selection.isdecimal():
        index = int(selection) - 1
        if 0 <= index < len(devices):
            return devices[index]
    return next(
        (device for device in devices if device.address.lower() == selection.lower()),
        None,
    )


async def main():
    devices = []
    client = None
    print("BLE controls manage this program's connection from your PC.")
    print("Use option 4 to exit cleanly.")

    try:
        while True:
            print("\nBluetooth Interactions Menu:")
            print("1. List nearby BLE devices")
            print("2. Disconnect this program's BLE connection")
            print("3. Connect / reconnect this PC to a BLE device")
            print("4. Exit")
            choice = await ask("Enter your choice (1-4): ")

            if choice in {"1", "3"}:
                if client is not None and client.is_connected:
                    print(f"Already connected to {client.address}. Use option 2 first.")
                    continue
                if client is not None:
                    client = await disconnect_device(client, announce=False)
                    if client is not None:
                        print("Use option 2 to retry connection cleanup first.")
                        continue

            if choice == "1":
                devices = await list_nearby_devices()
            elif choice == "2":
                client = await disconnect_device(client)
            elif choice == "3":
                # Refresh the scan so the selected peripheral was recently seen.
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
