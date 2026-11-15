# SkylonHost: two new VPS ready for mobile testing

Status: server installation and server-side data-transfer verification complete. Megafon Moscow acceptance remains pending the user’s device test.

Repository: tetss2/tetss_vpn. Operational branch: sk1114. Installer commit: dbd6fdd47fd5787db1b674970e4d7dedbfc4f7ed. No production-app PR or CI run applies to this console deployment.

The existing Prague VPS 109.248.43.81 was not changed, restarted, cancelled or deleted. No cascades, relays, other providers, Connect application changes or DNS changes were introduced.

## New servers

| Label | IPv4 | Hardware | Location | Hourly rate | Monthly cap |
|---|---|---|---|---|---|
| Sky2 | 109.248.43.149 | Ryzen G2 | Prague | €0.009 | €4.99 |
| Sky3 | 109.248.43.30 | EPYC G3 | Prague | €0.009 | €4.99 |

Both new servers are accruing hourly charges: €0.018/hour combined (€0.432 per 24 hours), excluding the retained old server. Both new IPv4 addresses and the old address are in 109.248.43.0/24. Different hardware pools are not different geographic regions; changing these IPs does not establish that the mobile route is usable.

## Implementation

Pinned official Xray v26.11.9 and Hysteria v2.13.0 downloads were SHA-256 verified. Independent client secrets were generated on each VPS and were excluded from this report and GitHub. Services use systemd DynamicUser, restricted filesystem access and credential loading. Configuration validation preceded service startup; the deployment rollback timer was stopped only after all transfer tests passed. VPN services are enabled for restart after boot. No expiration was configured for the client keys.

| Number | Transport | Port |
|---|---|---|
| 01 | VLESS REALITY Vision, Microsoft | TCP 443 |
| 02 | VLESS REALITY Vision, Google, MSS 1200 | TCP 5443 |
| 03 | Trojan REALITY, Google, MSS 1200 | TCP 2443 |
| 04 | VLESS REALITY XHTTP packet-up | TCP 6443 |
| 05 | VLESS REALITY XHTTP stream-up | TCP 6443 |
| 06 | Shadowsocks chacha20-ietf-poly1305 | TCP/UDP 8388 |
| 07 | Hysteria2 Salamander, certificate pin | UDP 443 |
| 08 | Hysteria2 QUIC, certificate pin | UDP 8443 |

## Verification evidence

Each profile downloaded 16,754,078 bytes over its VPN path to public HTTPS, with the expected SHA-256, then repeated the same transfer rate-limited to sustain traffic for over one minute. Test clients ran on the respective VPS, so these checks cover the local VPN configuration and public outbound path, not carrier filtering or the iPhone client.

| Server | Profile | Normal seconds | Sustained seconds | Both SHA-256 checks |
|---|---|---|---|---|
| Sky2 | 01 | 5.7 | 61.44 | Match |
| Sky2 | 02 | 0.47 | 61.83 | Match |
| Sky2 | 03 | 0.37 | 61.2 | Match |
| Sky2 | 04 | 0.5 | 61.32 | Match |
| Sky2 | 05 | 0.46 | 61.35 | Match |
| Sky2 | 06 | 0.34 | 61.35 | Match |
| Sky2 | 07 | 0.75 | 61.48 | Match |
| Sky2 | 08 | 0.52 | 62.16 | Match |
| Sky3 | 01 | 5.78 | 61.16 | Match |
| Sky3 | 02 | 0.33 | 62.7 | Match |
| Sky3 | 03 | 0.31 | 61.45 | Match |
| Sky3 | 04 | 0.58 | 61.82 | Match |
| Sky3 | 05 | 0.45 | 63.89 | Match |
| Sky3 | 06 | 0.31 | 61.31 | Match |
| Sky3 | 07 | 0.47 | 61.68 | Match |
| Sky3 | 08 | 0.48 | 61.58 | Match |

Both servers: skylon-new-xray, skylon-p3-hy27 and skylon-p3-hy28 are active.

## Delivery

Sixteen QR codes were generated and each was decoded back to its exact client URI. The numbered links and adjacent QR codes were prepared separately for Sky2 and Sky3. Two separate Gmail messages with inline QR images were sent to the explicitly requested recipient; send receipts were checked. The QR image files were saved successfully. Neither administrative passwords nor client credentials are present in this public report.

## Checkpoint and next action

Both new VPS are configured and left running. The temporary encrypted delivery service automatically expires after four hours; this does not expire VPN keys or stop VPN services. Private bundles remain on the respective VPS for recovery.

Next: the user disables Wi-Fi and tests real page/video loading for at least one minute on Megafon Moscow, starting with 01, 02 and 03 on each server, and reports the Sky2/Sky3 labels and numbers. Do not interpret ping alone as acceptance. If the carrier tests fail, diagnose those exact new IPs without changing the retained old server or introducing cascades.
