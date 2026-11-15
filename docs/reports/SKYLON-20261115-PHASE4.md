# SkylonHost phase 4 — 2026-11-15

Status: IPv6 control profile validated and two-hour passive transport diagnostics started. Megafon Moscow acceptance is PENDING; no claim of a fixed mobile connection.

Branch: sk1114. Deployment sources: aff464b8957af90045d512e742ecd49daac8658c (d4.py), a278c844033875934625894976b6bf12e15f706c (d4resume.py).

## Evidence and diagnosis

User reports existing profiles work on Beeline home Wi-Fi but HAPP latency disappears when actual browsing starts on Megafon Moscow. Today's phase-3 access journal contained 1,180 accepted requests from one source and 16 from another during the earlier test window. The second included both probe and non-probe destinations. This proves some requests reached the authenticated proxy, not successful delivery of response data. Exact provider attribution and the failure location are not independently established.

No client IP addresses, destination browsing history, keys, administrative credentials or full packet captures are published here.

## Final implementation

- Profile 33: existing VLESS REALITY Vision listener on TCP5443, addressed through the VPS's included IPv6 address. Same listener, authentication and MSS1200 settings as profile29; only the client endpoint address differs.
- No cascade, new billable IP, VPS purchase or cancellation.
- The first isolated IPv6 TCP443 service could not bind because the existing listener already serves both address families. It was stopped and its rollback timer stopped. The final profile uses the existing dual-stack listener; the unused sidecar remains stopped and is not enabled.
- Eight pre-existing VPN configurations and process IDs were compared with the saved pre-change snapshot and are identical. No VPN service restart, firewall, global MTU, DNS or other provider changes.
- IPv6 host firewall INPUT, FORWARD and OUTPUT policies observed ACCEPT.
- skylon-diag4 is a transient two-hour passive monitor with CAP_NET_RAW and a 7,500-second systemd hard lifetime limit. It records connection headers, byte/packet/ACK and reset counters for selected VPN ports. No payload is retained. It does not inspect SSH traffic.
- Private observations remain root-only; exported delivery is RSA-OAEP/AES-GCM encrypted. Monitor window starts at Unix 1794737330.961833 and ends at 1794744530.961833. HTTP delivery has an independent four-hour lifetime.

## Tests and limits

Profile33 downloaded 16,754,078 bytes in 0.51 seconds, then repeated with rate limiting in 60.55 seconds. Both HTTP 200 responses match SHA256 b651f7e1d9966ee2c1b1ee1bf8b52c72771824d3065dce96bbc8bcc19ed95f82.

The client ran on the VPS through its assigned IPv6 address to the existing listener and then a public HTTPS file. This checks service configuration and transfer integrity; it does NOT test the external IPv6 route or Megafon.

Baseline32 passed after the change: same 16,754,078-byte hash, HTTP 200, 0.37 seconds. All eight existing service hashes/PIDs remained unchanged. Monitoring service, existing phase3 Xray and encrypted delivery service were confirmed active. Monitor encrypted export was successfully retrieved and decrypted.

Parser tests covered synthetic IPv4 TCP SYN/data and an empty frame. Counters may include retransmissions/offload effects; they are not unique application byte counts. IPv6 extension headers are not decoded. A new controlled phone test is needed to correlate connection counters with the failure.

QR image decoded with zxing-cpp and exactly matched the client URI. The user-requested email containing the link and adjacent inline QR was sent to the verified recipient; Gmail returned SENT. QR artifact was saved successfully.

PR/CI: not applicable to this isolated operational helper branch. No application code or main branch deployment.

## IPv4 pricing

Extra IPv4 availability and price remain unconfirmed: no add/replace-IP control was found in the provider dashboard, and no published price was located. No paid order or support message was sent. The control test uses the IPv6 already included in the server plan. A different address cannot guarantee that the mobile path will work.

## Next checkpoint

User tests profile33, then existing32, on Megafon with Wi-Fi disabled and reports real page/video loading and test time. If no IPv6 is available on the phone's mobile connection, profile33 will be unreachable independently of VPN correctness. Inspect the corresponding private packet metadata before deciding on the next configuration or IP purchase.
