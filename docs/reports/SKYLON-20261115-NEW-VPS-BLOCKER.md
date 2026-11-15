# SkylonHost: two new hourly VPS — 2026-11-15

Status: provisioning COMPLETE; VPN configuration and delivery BLOCKED on initial console authentication.

## Authorized scope
User authorized two additional VPS at the previously reviewed EUR0.009/hour per instance, direct VPN profiles with numbered links/QR, and one email per VPS to the established recipient. No cascades or cancellation of existing servers.

## Provisioned and verified
| Label | IPv4 | Platform | Rate |
|---|---|---|---|
| tetss-prague-ip2-test | 109.248.43.149 | Prague Ryzen G2, 1GB, Debian12 | EUR0.009/hour |
| tetss-prague-ip3-test | 109.248.43.30 | Prague EPYC G3, 1GB, Debian12 | EUR0.009/hour |

Both orders were explicitly confirmed by Cloudie, and both later appeared Running. Combined new cost EUR0.018/hour, EUR0.432 per 24 hours; combined monthly cap EUR9.98. Existing server billing is additional. Both new IPv4 addresses are in the same /24 as the original, so this changes host addresses without proving a different network path. Only Prague is offered; hardware pools are not separate geographic regions.

## Blocker and safe alternatives checked
- Existing signed-in Cloudie session was reused successfully.
- Direct TCP22 to the first new server from the execution environment returned Network unreachable before authentication.
- noVNC console for the first new host visibly shows a Debian login prompt. The browser DOM has a canvas rather than supported secure credential fields.
- Both new console pages have been opened for user sign-in. Provider deployment emails were located for each corresponding host.
- No credential values are in this report. No passwords reset and no existing VPN services changed.
- No VPN profiles on these two new hosts have been created or validated yet. No client-key emails sent yet; provider credential emails are not VPN delivery.

## Continuation
After user signs into both new consoles as root, configure direct test profiles with unique names per host, validate large-file and sustained transfers, generate QR codes and verify each decodes to its exact URI, then send one separate requested email per host. Final phone acceptance must be on Megafon; server tests do not prove it works.

## Checkpoint
Branch sk1114, preceding report commit09cdfedb5e8e5e9eca77794e0e001d7fc012a18a. This is an operational provisioning checkpoint; PR/CI not applicable, main application unchanged.
