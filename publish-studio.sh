#!/bin/bash
set -euo pipefail
umask 022
name=tetss-studio-edge
base=/opt/$name
unit=/etc/systemd/system/$name.service
if test -e "$base" || test -e "$unit"; then
    echo 'Existing web service found, leaving files intact'
    exit 1
fi
if ss -lntH | awk '{print $4}' | grep -Eq ':(80|10443)$'; then
    echo 'An HTTP port is already in use'
    exit 1
fi
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
cd "$work"
if command -v caddy >/dev/null; then
    bin=$(command -v caddy)
else
    if ! apt-get -qq download caddy; then
        apt-get -qq -o Acquire::Retries=1 update
        apt-get -qq download caddy
    fi
    dpkg-deb -x ./*.deb pkg
    bin=$work/pkg/usr/bin/caddy
fi
cat > Caddyfile <<'CFG'
{
    admin off
    https_port 10443
}
http://prague-web.tetss.com, http://109-248-43-81.skylon.cloud {
    redir https://{host}:10443{uri} 302
}
https://prague-web.tetss.com:10443, https://109-248-43-81.skylon.cloud:10443 {
    tls {
        issuer acme {
            disable_tlsalpn_challenge
        }
    }
    reverse_proxy https://tetss-studio-site-production.up.railway.app {
        header_up Host tetss-studio-site-production.up.railway.app
    }
}
CFG
"$bin" adapt --config "$work/Caddyfile" --adapter caddyfile > /dev/null
install -d -m 0755 "$base"
install -m 0755 "$bin" "$base/caddy"
install -m 0644 Caddyfile "$base/Caddyfile"
cat > "$unit" <<'UNIT'
[Unit]
Description=tetss studio HTTPS entry
Wants=network-online.target
After=network-online.target
[Service]
DynamicUser=yes
StateDirectory=tetss-studio-edge
Environment=HOME=/var/lib/tetss-studio-edge
ExecStart=/opt/tetss-studio-edge/caddy run --config /opt/tetss-studio-edge/Caddyfile --adapter caddyfile
Restart=on-failure
RestartSec=5
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now "$name"
