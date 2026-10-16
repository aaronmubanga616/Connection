# Connection

A small Python command-line application for discovering Bluetooth Low Energy
(BLE) devices and managing a connection between your computer and a BLE
peripheral. It uses [Bleak](https://bleak.readthedocs.io/).

## Features

- Scan for nearby advertising BLE devices for eight seconds.
- Display device names and Bluetooth addresses.
- Select a device by its displayed number or address.
- Connect to one BLE peripheral at a time.
- Disconnect the connection opened by this program.
- Handle connection failures, timeouts, invalid input, and console input ending.
- Attempt connection cleanup when exiting or cancelling a connection attempt.

## Requirements

- Python 3.10 or newer.
- A working BLE-capable Bluetooth adapter with Bluetooth enabled.
- A target peripheral that advertises BLE services and accepts a GATT connection.

The main application was tested on Windows 11 with Python 3.13 and Bleak 3.0.2.
The pinned dependency below is intended for this setup. Other operating systems
and Bluetooth adapters have not been verified in this project.

## Setup and run on Windows

Open PowerShell in the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe connection.py
```

These commands use the virtual environment directly, so activating it or changing
PowerShell's execution policy is unnecessary.

## Using the menu

| Option | Action |
| --- | --- |
| 1 | Scan and list nearby advertising BLE devices. |
| 2 | Disconnect this program's current BLE connection. |
| 3 | Scan, choose a device, and connect or reconnect this computer to it. |
| 4 | Attempt connection cleanup and exit. |

For option 3, enter a number from the latest results or the device's listed
address. A device without an advertised name is shown as `Unnamed device`.
While connected, use option 2 before starting another scan or connection.

## Scope and limitations

This application manages **its own BLE connection**. It does not manage Bluetooth
Classic audio connections, disconnect a phone from a speaker, control a link
between two other devices, or provide remote desktop access.

Discovery is not a vulnerability scan. A device appearing in the results does
not establish that it is vulnerable, and a device missing from the results does
not establish that it is secure. The program does not implement device-specific
control commands or read and write GATT characteristic values.

## Tests

After installing the requirements, run:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_connection.py
```

The 17 regression tests simulate Bluetooth operations. They cover scanning,
connection success and failure, timeouts, cancellation, device selection, menu
behavior, and cleanup. They do not require a live Bluetooth peripheral.

A real scan was also verified on the development PC. A successful connection to
a physical peripheral has not yet been verified; the paired iPhone was not
available in that BLE scan.

## Troubleshooting

- **No devices found:** Make sure the target supports BLE and is advertising.
  Bluetooth Classic audio devices may not appear in this scan.
- **Scan failed:** Check Bluetooth is enabled and the adapter supports BLE.
- **Connection failed:** The target may be out of range, unavailable, or unable
  to accept a BLE GATT connection. Some peripherals require pairing first.
- **Disconnect failed:** Use option 2 to retry cleanup before attempting another
  connection.
- **`No module named bleak`:** Install `requirements.txt` using the same Python
  interpreter that runs the application.

## Project files

- `connection.py`: Main application and recommended entry point.
- `test_connection.py`: Regression tests for the main application.
- `requirements.txt`: Pinned dependency for the main application.
- `bluetooth_windows.py`: Earlier standalone version, retained for reference.
  Its separate setup notes use Bleak 2.1.1; use `connection.py` for this README's
  installation instructions and test coverage.
- `test_env.py`: Small diagnostic that prints the current Python interpreter.

## API references

- [Bleak scanner API](https://bleak.readthedocs.io/en/latest/api/scanner.html)
- [Bleak client API](https://bleak.readthedocs.io/en/latest/api/client.html)
