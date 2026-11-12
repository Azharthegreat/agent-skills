# No-USB LAN relay

Read this only when the user explicitly requires the phone to reach the desktop emulator without a USB reverse tunnel.

## Security boundary

The emulator ADB port normally listens only on desktop loopback. Exposing it to a LAN changes the attack surface of a powerful debugging service.

Before changing anything:

- Confirm the phone and laptop are authorized and on a trusted private network.
- Verify the exact laptop LAN IP, phone LAN IP, emulator ADB port, and chosen external relay port.
- Ask for explicit authorization immediately before creating the relay or firewall rule.
- Bind to the exact laptop LAN address, never `0.0.0.0`.
- Restrict the firewall rule to the exact phone IP, never Any.
- Prefer a non-default external port such as `15555` that forwards to emulator ADB port `5555`.
- Do not use this on public, guest, hotel, office visitor, or otherwise untrusted Wi-Fi.
- Record exact cleanup commands before creating the rule.

## Read-only Windows preflight

```powershell
Get-NetIPConfiguration |
  Where-Object { $_.NetAdapter.Status -eq 'Up' -and $_.IPv4Address } |
  ForEach-Object {
    [pscustomobject]@{
      Interface = $_.InterfaceAlias
      IPv4 = $_.IPv4Address.IPAddress
      Gateway = $_.IPv4DefaultGateway.NextHop
    }
  }

Get-NetTCPConnection -State Listen -LocalPort 5555 -ErrorAction SilentlyContinue
netsh interface portproxy show all
```

Do not confuse virtualization-only networks such as `192.168.56.0/24` with the active Wi-Fi or Ethernet network that the phone uses.

## Guarded Windows example

Example values that must be replaced with verified local evidence:

```text
Laptop LAN IP:       192.0.2.10
Authorized phone IP: 192.0.2.20
External relay port: 15555
Emulator ADB port:   5555
Firewall rule name:  ADB Emulator Relay - phone 192.0.2.20
```

After explicit authorization, an administrator may create an exact-address proxy:

```powershell
netsh interface portproxy add v4tov4 `
  listenaddress=192.0.2.10 `
  listenport=15555 `
  connectaddress=127.0.0.1 `
  connectport=5555
```

Create a firewall rule restricted to the authorized phone IP:

```powershell
New-NetFirewallRule `
  -DisplayName 'ADB Emulator Relay - phone 192.0.2.20' `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalAddress 192.0.2.10 `
  -LocalPort 15555 `
  -RemoteAddress 192.0.2.20 `
  -Profile Private
```

The phone-side client would connect to `192.0.2.10:15555`, not `10.0.2.15:5555`.

Verify the exact listener, proxy, firewall scope, and an established client connection. Do not claim success from rule creation alone.

## Cleanup

Remove only the exact relay created for this workflow:

```powershell
netsh interface portproxy delete v4tov4 `
  listenaddress=192.0.2.10 `
  listenport=15555

Remove-NetFirewallRule -DisplayName 'ADB Emulator Relay - phone 192.0.2.20'
```

Verify cleanup:

```powershell
netsh interface portproxy show all
Get-NetFirewallRule -DisplayName 'ADB Emulator Relay - phone 192.0.2.20' -ErrorAction SilentlyContinue
```

## Linux or macOS relay

If `socat` is already installed, the equivalent concept is an exact-address listener:

```bash
socat TCP-LISTEN:15555,bind=<laptop-lan-ip>,reuseaddr,fork TCP:127.0.0.1:5555
```

Apply the host firewall's exact phone-IP restriction. Do not install packages, start background services, or persist the relay without separate user authorization. Stop the relay when the session ends.

## Prefer USB when practical

USB reverse avoids exposing ADB to the LAN, works independently for multiple phones, and allows every phone to use its own loopback address. Use LAN relay only when USB is genuinely unavailable or the user explicitly requires cable-free operation.
