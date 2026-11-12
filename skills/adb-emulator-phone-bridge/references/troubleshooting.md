# Troubleshooting and recovery

Use the narrowest diagnostic branch supported by current evidence. Preserve other devices, active mappings, installed apps, and local data.

## Device-state matrix

| Evidence | Likely condition | Safe response |
| --- | --- | --- |
| `<serial> device` | Authorized and online | Verify model, then apply the selected mapping. |
| `<serial> unauthorized` | RSA prompt not accepted | Unlock the phone, accept the fingerprint prompt, then recheck. Do not bypass authorization. |
| `<serial> offline` | Transport exists but ADB session is unhealthy | Reconnect only that phone and recheck. Avoid killing the global ADB server while other sessions matter. |
| No phone line, but Windows shows the phone | USB mode or ADB interface issue | Select File Transfer/MTP, enable USB debugging, inspect the Android ADB interface and drivers. |
| Phone appears then vanishes | USB re-enumeration, cable, hub, port, power, or mode instability | Use a known data cable, direct USB port, unlocked screen, and a bounded wait. |
| Only a phantom Windows device remains | The device was previously enumerated but is not currently present | Treat it as physically absent. Do not claim it is connected. |
| `more than one device/emulator` | A mutating command omitted `-s` | Stop and rerun with the verified exact serial. |
| `device '<serial>' not found` | Serial disappeared or a different ADB server is active | Re-run `adb devices -l`, compare ADB executable paths, and do not target another row. |

## Windows USB diagnostics

Read-only checks:

```powershell
Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
  Where-Object {
    $_.InstanceId -match 'VID_04E8' -or
    $_.FriendlyName -match 'Samsung|Android|ADB'
  } |
  Select-Object Status, Problem, Class, FriendlyName, InstanceId
```

For recent driver evidence:

```powershell
$eventStart = (Get-Date).AddMinutes(-15)
Get-WinEvent -FilterHashtable @{ LogName = 'System'; StartTime = $eventStart } |
  Where-Object { $_.ProviderName -match 'Kernel-PnP|DriverFrameworks|USB|UserPnp' } |
  Select-Object -First 25 TimeCreated, Id, LevelDisplayName, ProviderName, Message
```

Interpretation matters:

- A successful Samsung ADB/MTP driver installation followed by a phantom device points toward physical disconnect or USB function re-enumeration, not an RSA denial.
- RSA denial normally leaves an `unauthorized` ADB row.
- Do not uninstall USB drivers or disable devices without explicit approval and evidence that the driver is the root cause.

## Phone-side recovery checklist

1. Keep the phone unlocked and screen on.
2. Confirm Developer options and USB debugging are enabled.
3. Select File Transfer/MTP rather than charge-only mode.
4. Accept the USB debugging fingerprint prompt and optionally select Always allow only on a trusted laptop.
5. Prefer a known data cable and a direct laptop port. Old devices may be more stable on USB 2.0.
6. Avoid hubs when enumeration is unstable.
7. Re-run `adb devices -l` and require the same serial to remain in `device` state.

## ADB executable or server mismatch

Compare paths and versions:

```powershell
where.exe adb
Get-Command adb -All | Select-Object Source, Version
adb version
```

Use one absolute `platform-tools\adb.exe` path for the complete workflow. A list that differs between terminals often indicates a path, user-session, environment, or timing difference. Check before restarting anything.

Do not use `adb kill-server` as a first response. It interrupts every phone, emulator, wireless, forward, and reverse transports managed by that server.

## Emulator or port diagnosis

```powershell
adb devices -l
adb -s emulator-5554 shell getprop ro.boot.qemu
adb -s emulator-5554 shell getprop service.adb.tcp.port
Get-NetTCPConnection -State Listen -LocalPort 5554,5555 -ErrorAction SilentlyContinue
```

For the first standard emulator:

- `5554` is the console port.
- `5555` is the host ADB port.
- `10.0.2.15` is a guest NAT address and is not the USB reverse endpoint.

If port `5555` is not listening, verify the emulator state and configured ports. Do not create a reverse mapping to an unverified listener.

## Reverse command succeeds but client cannot connect

Check in order:

1. The mapping still exists on the same phone serial.
2. The emulator is still `device`, not `offline`.
3. The phone-side client uses `127.0.0.1` and the mapped phone port.
4. The host port matches the selected emulator ADB port.
5. A security app is not blocking the phone-side client.
6. The client supports the emulator's ADB authentication and protocol mode.

Do not dismiss antivirus or mobile-security warnings automatically. Record the warning and ask the user to decide.

## APK installation is a separate workflow

An ADB route does not require reinstalling the phone-side app. If installation is requested, verify the existing APK before acting:

```powershell
aapt dump badging path\to\app-debug.apk
apksigner verify --print-certs path\to\app-debug.apk
adb -s <phone-serial> shell dumpsys package <application-id>
```

Important failures:

- `INSTALL_FAILED_UPDATE_INCOMPATIBLE`: installed and candidate APK signatures differ. `-r`, `-d`, and `-t` cannot bypass signature security.
- `INSTALL_FAILED_VERSION_DOWNGRADE`: candidate versionCode is lower. Do not add `-d` unless the user explicitly authorizes a downgrade and the package permits it.
- `INSTALL_FAILED_TEST_ONLY`: a test-only APK may require `-t`, but verify that this is expected.

Never uninstall or clear the installed package merely to fix a signature mismatch without explicit authorization. Uninstalling normally deletes that application's local data. Building, resigning, changing the application ID, or installing a coexistence variant are separate implementation choices.

