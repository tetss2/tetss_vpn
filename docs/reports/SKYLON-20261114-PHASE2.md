# SkylonHost Prague — phase 2, 2026-11-14

Status: six additional isolated profiles (21–26) deployed and verified. Russian mobile-network acceptance is still pending.

## User evidence and interpretation
The user reports successful, stable traffic through most original profiles on Beeline home Wi-Fi in Moscow, including profile 07. Megafon Moscow shows either no latency result or latency without useful traffic. The user mentioned 07, 14, 16, 18, 19 and 20; the message does not establish successful Megafon data transfer for those profiles.
This is consistent with a path-specific problem, including routing, traffic filtering or transport behavior. It does not prove an IP-level block.

## Implementation
- Target remains tetss-prague-test, 109.248.43.81, Prague EPYC.
- No new VPS or billable IP was ordered.
- Original VPN service configuration and process PID were unchanged. A private backup was made and hash-verified.
- Original config SHA-256: 52a11f3d57103212767aeaa57314b762b0e356756f4d933b667784fe264e5719.
- Original profiles 07, 14 and 18 passed checksum-verified downloads before and after the additions.
- New services: skylon-hy-21, skylon-hy-22, skylon-hy-23 and skylon-extra.
- Profiles 21–23: Hysteria2 2.13.0, UDP ports 8448, 8449 and 20443. Profiles 22–23 use Salamander; conservative BBR and server-side disabled PMTU discovery are used.
- HY2 certificates are explicitly SHA-256 pinned in the share links. A wrong-pin negative test was rejected. No unpinned insecure connection is delivered.
- Profiles 24–25: XHTTP REALITY with dl.google.com, packet-up and stream-up, TCP 11443.
- Profile 26: Shadowsocks 2022 AES-128-GCM, port 1443.
- No changes to existing listeners, port 443, firewall, DNS or other providers.
- New services enabled on boot only after health checks; rollback timer stopped after successful validation.
- Source branch sk1114; implementation commit 6c36c0b6014972fe61197c0161f8d2003bd87c98.
- PR/CI: not applicable to this isolated operational helper. No main-branch merge or existing application deployment.
- Official Hysteria binary SHA-256: 907ba8c9693edb104b20582681fb7dc15639d5b64a9cbb616a7b539190a86691.

## Validation
All six downloaded 16,754,078 bytes and matched the known SHA-256 of the official Xray release archive. All six also passed continuous rate-limited transfers of approximately 61–64 seconds.
Scope: client on the new server -> loopback VPN listener -> public HTTPS download. This is not a test from Megafon or Beeline.
Local preflight included authenticated Hysteria handshakes and Xray configuration validation.
Each delivered QR was decoded and compared byte-for-byte with its URI.

| ID | Protocol / transport | Port | Verified bytes | Initial seconds | Sustained seconds | Result |
|---|---|---:|---:|---:|---:|---|
| 21 | Hysteria2 / UDP | 8448 | 16754078 | 0.6 | 62.78 | PASS |
| 22 | Hysteria2 / UDP / salamander | 8449 | 16754078 | 0.86 | 62.55 | PASS |
| 23 | Hysteria2 / UDP / salamander | 20443 | 16754078 | 0.86 | 63.9 | PASS |
| 24 | VLESS / xhttp / packet-up | 11443 | 16754078 | 5.59 | 61.46 | PASS |
| 25 | VLESS / xhttp / stream-up | 11443 | 16754078 | 0.45 | 61.24 | PASS |
| 26 | Shadowsocks2022 / tcp/udp | 1443 | 16754078 | 0.3 | 63.34 | PASS |

## IP options checked
Cloudie Networking shows the existing IPv4 and routed /64 IPv6, DNS, bandwidth controls and reverse DNS, but no self-service IP replacement/add-IP control.
The public API documents instance lifecycle and reverse DNS operations, but no dedicated replacement/additional-IPv4 endpoint.
The current published base VPS price is EUR 0.009/hour capped at EUR 4.99/month, including one IPv4. A second test VPS would therefore cost approximately EUR 0.054 for six hours or EUR 0.216 for 24 hours, in addition to the current VPS.
Replacement/additional IPv4 availability and price remain unconfirmed; free replacement must not be assumed. They require provider confirmation. No support message was sent.
Sources: https://skylonhost.com/cloud.html ; https://skylonhost.com/docs/api/instances/ ; https://skylonhost.com/terms-of-service.html

## Next step
Test new profiles on Megafon Moscow in the order 22, 21, 23, 24, 25, 26, with real page/image/video transfer for at least one minute. Keep the working Beeline profiles. Consider a second-IP test only after choosing its spending limit.
