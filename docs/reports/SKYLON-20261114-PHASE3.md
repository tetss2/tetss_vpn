# SkylonHost phase 3 — 2026-11-14

Status: six direct test profiles deployed and validated; Megafon Moscow acceptance PENDING.

Implementation branch: sk1114; deployment source commit: 3c3b11867d8c6d1fad43b000af5be3d6123e961d.

## User evidence
HAPP on iPhone: Beeline home Wi-Fi transfers data; Megafon Moscow shows a latency result but stops when browsing begins. This does not prove an IP block. No cascades authorized or used.

## Changes
- Separate skylon-p3-hy27, skylon-p3-hy28 and skylon-p3-xray services.
- 27: Hysteria2 Salamander UDP443; 28: Hysteria2 plain UDP8443. Certificate SHA256 pinned.
- 29: VLESS REALITY Vision TCP5443; 30/31: XHTTP packet-up/stream-up TCP6443; 32: Trojan REALITY TCP2443.
- TCP sidecars use tcpMaxSeg=1200 with keepalive. Existing TCP443 listener preserved.
- All five previous VPN service configuration hashes and process IDs remained unchanged.
- Baselines 07, 14, 18 passed after deployment. No firewall, global MTU, DNS, other providers, purchases or cancellations changed.
- Backups are root-only; client secrets are only in private host/local bundles and user delivery, never this repository.
- Encrypted result export uses an ephemeral task RSA key and AES-GCM. HTTP delivery expires after four hours.

## Tests
Server-loopback clients through actual VPN listeners to public HTTPS release file; NOT an external Megafon test.
Each test downloaded 16,754,078 bytes matching SHA256 b651f7e1d9966ee2c1b1ee1bf8b52c72771824d3065dce96bbc8bcc19ed95f82.
All QR images decoded and matched their exact URIs.

|Profile|Initial seconds|Sustained seconds|Result|
|---|---:|---:|---|
|27|0.56|61.73|PASS|
|28|5.48|61.92|PASS|
|29|0.49|59.5|PASS|
|30|0.47|62.27|PASS|
|31|0.46|61.43|PASS|
|32|0.49|61.09|PASS|

## Diagnostics and limits
Available RAM was about 620 MiB; five existing VPN services active. Logs contained timeouts and peer resets, but these are not correlated with a particular user test and cannot establish filtering, IP blocking or the precise failure cause.
Actual HAPP import and Megafon end-to-end transfer remain unverified.
PR/CI: not applicable to the operational helper; no main merge or app deployment.

## IP pricing
Cloudie Networking offers no additional-IP or replace-IP control. Public extra IPv4 price and availability remain unconfirmed; no support message sent and no IP purchased. Published base VPS price is EUR0.009/hour capped EUR4.99/month; Prague only.
Sources: https://skylonhost.com/cloud.html ; https://skylonhost.com/faq.html

## Next step
User tests 27,29,32,30,31,28 over Megafon Moscow with real data transfer for a minute, then reports profile numbers and results. Further changes require these network-specific observations; never represent loopback success as Megafon success.
