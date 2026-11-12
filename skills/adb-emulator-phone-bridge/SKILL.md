---
name: adb-emulator-phone-bridge
description: Safely connect one or more USB-attached Android phones to a desktop Android Emulator ADB endpoint, especially when a phone-side ADB client must reach the emulator through adb reverse. Use for device identification, per-serial tunnel setup, connection verification, transient USB failures, multi-phone or multi-emulator routing, and guarded no-USB alternatives.
---

# ADB Emulator Phone Bridge

Connect an authorized physical Android phone to an authorized desktop Android Emulator without disturbing other attached phones, emulators, apps, or data.

## Safety invariants

- Observe first. Run status checks before changing a tunnel.
- When more than one ADB target exists, every mutating command must include the exact `-s <serial>` selector.
- Verify a claimed phone serial with `getprop ro.product.model` and verify the emulator with `getprop ro.boot.qemu` before setup.
- Treat reverse mappings as per-phone state. Adding a mapping to one selected phone must not remove or replace another phone's mapping.
- Never run `adb kill-server`, `adb reverse --remove-all`, uninstall an app, clear app data, dismiss a security warning, change a firewall, or expose a port to the LAN unless the user explicitly authorizes that separate action.
- Do not assume `emulator-5554` means the app should connect to port `5554`. For the standard first emulator, `5554` is the console port and `5555` is the ADB port.
- Do not give a physical phone the emulator guest address such as `10.0.2.15`. It normally sits behind the emulator's virtual router and is not the correct USB reverse endpoint.
- The normal phone-side endpoint after a successful USB reverse is `127.0.0.1:<phone-port>`.
- Do not claim success from command exit alone. Verify the mapping, device states, selected models, and final endpoint.

## Preferred workflow

1. Locate one consistent ADB executable. Prefer the configured Android SDK `platform-tools/adb` and report if multiple ADB executables or servers may be involved.
2. Run the helper in read-only mode:

   ```powershell
   & "<skill-dir>\scripts\Connect-EmulatorAdbBridge.ps1" -Action Status
   ```

3. Identify the exact physical phone and emulator serials from evidence. If multiple phones exist, never infer the target from list position alone. Verify its model.
4. For the standard first emulator and a verified phone, create only that phone's tunnel:

   ```powershell
   & "<skill-dir>\scripts\Connect-EmulatorAdbBridge.ps1" `
     -Action Connect `
     -PhoneSerial PHONE_B_SERIAL `
     -EmulatorSerial emulator-5554 `
     -WaitSeconds 30
   ```

5. Report the verified phone-side endpoint. For the example above it is `127.0.0.1:5555`.
6. Confirm other attached phones and their mappings remain present.

Read [references/usb-reverse.md](references/usb-reverse.md) for manual commands, multiple phones, multiple emulators, persistence, and cleanup.

## Failure routing

- If a phone is missing, `unauthorized`, `offline`, repeatedly appears and disappears, or Windows sees only a phantom Samsung device, read [references/troubleshooting.md](references/troubleshooting.md).
- If an APK install fails with a signature or downgrade error, stop. Connection setup does not authorize uninstalling, clearing data, recompiling, or resigning the APK. Follow the guarded deployment section in [references/troubleshooting.md](references/troubleshooting.md).
- If the user explicitly requires a connection without a USB cable, read [references/lan-relay.md](references/lan-relay.md). LAN exposure is not the default and requires explicit approval immediately before firewall or port-proxy changes.

## Expected evidence in the final report

- Selected phone serial and verified model.
- Selected emulator serial and verified QEMU status.
- Host emulator ADB port and phone loopback port.
- Exact `reverse --list` evidence. Accept transport labels such as `UsbFfs` and `(reverse)` when the TCP mapping is correct.
- Confirmation that other named devices and mappings remained connected.
- The address the user should enter in the phone-side client.
- Anything not verified, including whether the client application completed the ADB protocol handshake.

## Authoritative behavior

- [Android Debug Bridge documentation](https://developer.android.com/tools/adb)
- [Android Emulator port assignments](https://developer.android.com/studio/run/emulator-commandline)
- [Android Emulator network address space](https://developer.android.com/studio/run/emulator-networking-address)
- [Android device and USB debugging setup](https://developer.android.com/studio/run/device)
