# SkylonHost Prague test deployment — 2026-11-14

Status: server configured; 19 test profiles verified and ready for device testing. Profile 04 (Edge fingerprint) failed twice and is excluded from delivery.

## Scope and checkpoint
- Dedicated new instance: tetss-prague-test, Prague EPYC, Debian 12.
- IPv4: 109.248.43.81.
- Plan: EPYC-NVME-G3.1G, 1 CPU, 1 GB RAM, 20 GB NVMe, 15 TB transfer.
- Displayed price at creation: EUR 0.009/hour, capped at EUR 4.99/month.
- Source branch: sk1114.
- Bootstrap commit: 2e1ee43794fbd9021b50701a70e8d8b799cf666f.
- Retest commit: 57083c2906454af073f092ceda30667e30d03017.
- PR/CI: not applicable to this isolated operational helper branch; no merge or production deployment performed.
- Existing GreenCloud, Cloudzy, Vultr, ServerPoint, Connect and DNS were not changed.

## Implementation
- Pinned official Xray 26.11.9 binary, SHA-256 verified before execution.
- Server-specific host/IP and fresh-install guards; existing VPN installations refused.
- Sixteen VLESS variants delivered across REALITY + TCP/Vision, raw TCP, gRPC and XHTTP, plus three AEAD Shadowsocks profiles.
- VPN service uses systemd DynamicUser, restricted capabilities and a protected credential file.
- VPN service enabled on boot and confirmed active at completion.
- Keys have no configured expiration. Hosting must remain funded.
- Credentials generated on the server. Private server keys and root password are not included in source or this report.
- Client bundle exported only as RSA-OAEP/AES-GCM authenticated ciphertext. Temporary delivery HTTP service automatically stops after four hours.
- Initial rollback timer stopped by the retest routine; VPN remains running.
- Client credential backup is held on the server under /root/skylon-test/bundle.json, mode 0600.

## Validation and limits
- Server configuration and all 20 client configurations passed the Xray configuration parser.
- The first test URL returned HTTP 403 and was discarded as an unsuitable test source.
- Retests downloaded the official Xray release archive through each VPN profile: 16,754,078 bytes. Every reported PASS matched SHA-256 b651f7e1d9966ee2c1b1ee1bf8b52c72771824d3065dce96bbc8bcc19ed95f82.
- Profiles 01, 05, 10, 13 and 18 also passed rate-limited continuous transfers lasting approximately 59–63 seconds.
- Test path: Xray client on the new server -> loopback VPN inbound -> public HTTPS download. These tests verify protocol handling and server egress; they do not establish reachability or DPI behavior from Russian ISP networks.
- External SSH from the execution environment was not available; configuration was performed through the provider's authenticated console.
- No claim is made that all variants work in every client application. XHTTP requires a supporting application build.
- Original numbering is retained, with 04 omitted from client delivery.

| ID | Protocol / transport | Port | SNI or cipher | Result | Bytes | Seconds | Sustained |
|---|---|---:|---|---|---:|---:|---|
| 01 | VLESS / raw | 443 | www.microsoft.com | PASS | 16754078 | 0.41 | 59.31 s, PASS |
| 02 | VLESS / raw | 443 | www.microsoft.com | PASS | 16754078 | 0.37 | — |
| 03 | VLESS / raw | 443 | www.microsoft.com | PASS | 16754078 | 0.33 | — |
| 04 | VLESS / raw | 443 | www.microsoft.com | EXCLUDED: connection reset | 0 | 2.15 | — |
| 05 | VLESS / raw | 2053 | www.apple.com | PASS | 16754078 | 0.33 | 61.7 s, PASS |
| 06 | VLESS / raw | 2083 | www.cloudflare.com | PASS | 16754078 | 0.35 | — |
| 07 | VLESS / raw | 2087 | dl.google.com | PASS | 16754078 | 0.34 | — |
| 08 | VLESS / raw | 2096 | www.microsoft.com | PASS | 16754078 | 0.33 | — |
| 09 | VLESS / raw | 4443 | www.apple.com | PASS | 16754078 | 0.37 | — |
| 10 | VLESS / grpc | 7443 | www.microsoft.com | PASS | 16754078 | 0.41 | 60.07 s, PASS |
| 11 | VLESS / grpc | 7443 | www.microsoft.com | PASS | 16754078 | 0.35 | — |
| 12 | VLESS / grpc | 7444 | www.apple.com | PASS | 16754078 | 0.36 | — |
| 13 | VLESS / xhttp/packet-up | 8443 | www.microsoft.com | PASS | 16754078 | 0.55 | 63.11 s, PASS |
| 14 | VLESS / xhttp/stream-up | 8443 | www.microsoft.com | PASS | 16754078 | 0.42 | — |
| 15 | VLESS / xhttp/stream-one | 8443 | www.microsoft.com | PASS | 16754078 | 0.39 | — |
| 16 | VLESS / xhttp/packet-up | 9443 | www.apple.com | PASS | 16754078 | 0.5 | — |
| 17 | VLESS / xhttp/stream-up | 9443 | www.apple.com | PASS | 16754078 | 0.41 | — |
| 18 | Shadowsocks / tcp/udp | 8388 | chacha20-ietf-poly1305 | PASS | 16754078 | 0.32 | 63.23 s, PASS |
| 19 | Shadowsocks / tcp/udp | 8389 | aes-256-gcm | PASS | 16754078 | 0.33 | — |
| 20 | Shadowsocks / tcp/udp | 8390 | aes-128-gcm | PASS | 16754078 | 0.36 | — |

## Next step
Test profiles 18, 01, 05, 10 and 13 on the user's Megafon and Beeline networks for actual page, image and video loading for at least one minute. Keep the working profile numbers for subsequent selection; do not automatically add unverified variants to Connect.
