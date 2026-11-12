# USB reverse workflow

Use this reference when a phone-side application must connect to the ADB daemon of an Android Emulator running on the same laptop or workstation.

## Why this works

The first standard emulator normally appears as `emulator-5554`. Its console uses host port `5554`, while its ADB daemon is reachable through host loopback port `5555`. The emulator guest addresses, commonly `10.0.2.15` on Ethernet and `10.0.2.16` or later on Wi-Fi, live behind the emulator virtual router.

`adb reverse tcp:<phone-port> tcp:<host-port>` creates a transport associated with one selected physical device. A client on that phone can then connect to `127.0.0.1:<phone-port>`, and ADB carries that connection back to the host port.

## Manual preflight

Use the same ADB executable for every command:

```powershell
$adbTool = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
& $adbTool version
& $adbTool devices -l
```

If more than one `adb.exe` might exist:

```powershell
where.exe adb
Get-Command adb -All | Select-Object Source, Version
Get-Process adb -ErrorAction SilentlyContinue | Select-Object Id, Path
```

Do not kill the server merely to make the lists look cleaner. Killing the server interrupts every target and removes active reverse sessions.

## Verify exact targets

Example with two phones and one emulator:

```text
PHONE_A_SERIAL    device ... model:PHONE_A_MODEL
PHONE_B_SERIAL       device ... model:PHONE_B_MODEL
emulator-5554 device ... model:sdk_gphone64_x86_64
```

Verify the intended phone instead of assuming that the second line is correct:

```powershell
& $adbTool -s PHONE_B_SERIAL shell getprop ro.product.model
& $adbTool -s PHONE_B_SERIAL shell getprop ro.boot.qemu
& $adbTool -s emulator-5554 shell getprop ro.boot.qemu
& $adbTool -s emulator-5554 shell getprop service.adb.tcp.port
```

Expected evidence:

- Physical phone model matches the user's target.
- Physical phone `ro.boot.qemu` is blank or not `1`.
- Emulator `ro.boot.qemu` is `1`.
- Standard first emulator ADB port is `5555`.

## Create one phone's tunnel

```powershell
& $adbTool -s PHONE_B_SERIAL reverse tcp:5555 tcp:5555
& $adbTool -s PHONE_B_SERIAL reverse --list
```

Valid list output can include either transport label:

```text
UsbFfs tcp:5555 tcp:5555
```

or:

```text
(reverse) tcp:5555 tcp:5555
```

The transport label is not the acceptance criterion. The exact `tcp:5555 tcp:5555` mapping is.

The phone-side client uses:

```text
Host/IP: 127.0.0.1
Port:    5555
```

## Multiple phones

Reverse mappings are independent per physical-device transport. Use an explicit serial for each phone:

```powershell
& $adbTool -s PHONE_A_SERIAL reverse tcp:5555 tcp:5555
& $adbTool -s PHONE_B_SERIAL    reverse tcp:5555 tcp:5555

& $adbTool -s PHONE_A_SERIAL reverse --list
& $adbTool -s PHONE_B_SERIAL    reverse --list
```

Both phones may use `127.0.0.1:5555` because each phone has its own loopback namespace and its own ADB transport. Adding the second phone's mapping must not disconnect or rewrite the first one.

## Multiple emulators

Standard adjacent port pairs are:

| Emulator serial | Console port | ADB port |
| --- | ---: | ---: |
| `emulator-5554` | 5554 | 5555 |
| `emulator-5556` | 5556 | 5557 |
| `emulator-5558` | 5558 | 5559 |

Confirm `service.adb.tcp.port` because an emulator can be started with custom ports.

One phone can have mappings to multiple emulators if phone-side ports are unique:

```powershell
& $adbTool -s PHONE_B_SERIAL reverse tcp:5555 tcp:5555
& $adbTool -s PHONE_B_SERIAL reverse tcp:5557 tcp:5557
```

The client then selects `127.0.0.1:5555` for the first emulator or `127.0.0.1:5557` for the second.

## Bounded wait for unstable USB enumeration

If a phone appears briefly and disappears, do not retry mutations indefinitely. Keep the phone unlocked, fix the USB state, then use a bounded wait such as 30 seconds. The helper script supports `-WaitSeconds 30` and only applies the mapping after the exact serial reaches `device` state.

If the phone does not stabilize, stop and report the live device list. Do not fall back to another phone merely because it is still connected.

## Persistence and cleanup

Reverse mappings are transport state. Expect to recreate them after phone reconnects, phone reboots, host ADB server restarts, or some USB mode changes.

Remove only the selected mapping:

```powershell
& $adbTool -s PHONE_B_SERIAL reverse --remove tcp:5555
```

Verify removal:

```powershell
& $adbTool -s PHONE_B_SERIAL reverse --list
```

Do not use `--remove-all` when unrelated mappings may exist.

## Verification boundaries

A reverse mapping proves the route exists. It does not by itself prove that a phone-side app completed authentication or an ADB protocol handshake. If the user asks for application-level verification, inspect the app's visible connection state, process state, and sanitized logs without exposing pairing codes, device identifiers beyond authorized serials, or command contents.

