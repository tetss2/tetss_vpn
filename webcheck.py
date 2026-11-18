"""A 24-hour, static HTTPS reachability check for a server's own public IPv4."""
import concurrent.futures
import hashlib
import http.server
import ipaddress
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import urllib.request

PORT = 10443
FILE = bytes(range(256)) * 32768
DIGEST = hashlib.sha256(FILE).hexdigest()
PAGE = """<!doctype html><html lang="ru"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Проверка соединения · tetss</title>
<style>body{margin:12vh auto;padding:0 22px;max-width:34rem;font:18px/1.5 system-ui;color:#25252b;background:#fff}h1{font-size:clamp(30px,7vw,44px);line-height:1.1}button{padding:12px 18px;font:inherit;color:#fff;background:#9f2634;border:0;border-radius:10px;cursor:pointer}button:disabled{opacity:.55}output{display:block;margin:28px 0;font-weight:600}</style>
<main><h1>Проверка соединения</h1><p>Страница открылась. Проверяем, загружается ли файл целиком.</p>
<output role="status" aria-live="polite" id="result">Загрузка 8 МиБ…</output>
<button id="again" disabled>Повторить проверку</button></main>
<script>
const output=document.querySelector('#result'), button=document.querySelector('#again');
async function run(){
  button.disabled=true;
  output.textContent='Загрузка 8 МиБ…';
  const start=performance.now(), controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),90000);
  try{
    const response=await fetch('/8m.bin',{cache:'no-store',signal:controller.signal});
    if(!response.ok)throw Error('http');
    const data=await response.arrayBuffer();
    const bytes=new Uint8Array(await crypto.subtle.digest('SHA-256',data));
    const hash=Array.from(bytes,x=>x.toString(16).padStart(2,'0')).join('');
    if(data.byteLength!==8388608 || hash!=='EXPECTED_HASH')throw Error('integrity');
    const seconds=((performance.now()-start)/1000).toLocaleString('ru',{maximumFractionDigits:1});
    output.textContent='Готово — 8 МиБ загружены за '+seconds+' с. Файл проверен.';
  }catch(e){output.textContent='Страница открылась, но проверка файла не завершилась.';}
  finally{clearTimeout(timer);button.disabled=false;}
}
button.addEventListener('click',run);run();
</script></html>""".replace("EXPECTED_HASH", DIGEST).encode()


class Handler(http.server.BaseHTTPRequestHandler):
    def serve(self, send_body):
        path = self.path.partition("?")[0]
        if path == "/":
            content, mime = PAGE, "text/html; charset=utf-8"
        elif path == "/8m.bin":
            content, mime = FILE, "application/octet-stream"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if send_body:
            self.wfile.write(content)

    def do_GET(self):
        self.serve(True)

    def do_HEAD(self):
        self.serve(False)

    def log_message(self, *args):
        pass


class Server(http.server.HTTPServer):
    def __init__(self, address, context):
        self.context = context
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=8)
        import threading
        self.capacity = threading.BoundedSemaphore(8)
        super().__init__(address, Handler)

    def process_request(self, request, client):
        if self.capacity.acquire(blocking=False):
            self.pool.submit(self.handle_client, request, client)
        else:
            request.close()

    def handle_client(self, request, client):
        try:
            request.settimeout(20)
            with self.context.wrap_socket(request, server_side=True) as conn:
                conn.settimeout(90)
                self.finish_request(conn, client)
        except (OSError, ValueError):
            pass
        finally:
            request.close()
            self.capacity.release()


def issue_certificate(root, address):
    config = root / "acme"
    bundle = config / "live" / address
    if (bundle / "fullchain.pem").is_file() and (bundle / "privkey.pem").is_file():
        return bundle
    packages = root / "packages"
    packages.mkdir(exist_ok=True)
    env = dict(os.environ, PYTHONPATH=str(packages), HOME=str(root))
    if not (packages / "certbot").exists():
        pip = root / "pip.pyz"
        if not pip.exists():
            with urllib.request.urlopen("https://bootstrap.pypa.io/pip/pip.pyz", timeout=30) as src, pip.open("wb") as dst:
                shutil.copyfileobj(src, dst)
        subprocess.run([sys.executable, str(pip), "install", "--disable-pip-version-check",
                        "--no-cache-dir", "--only-binary=:all:", "--target", str(packages),
                        "certbot>=5.4,<7"], env=env, timeout=300, check=True)
    subprocess.run([sys.executable, "-m", "certbot", "certonly", "--standalone",
                    "--non-interactive", "--agree-tos", "--register-unsafely-without-email",
                    "--preferred-profile", "shortlived", "--preferred-challenges", "http",
                    "--ip-address", address, "--cert-name", address, "--config-dir", str(config),
                    "--work-dir", str(root / "work"), "--logs-dir", str(root / "logs")],
                   env=env, timeout=150, check=True)
    return bundle


def main():
    address = str(ipaddress.IPv4Address(sys.argv[1]))
    if "RUNTIME_DIRECTORY" not in os.environ:
        if os.geteuid() != 0:
            raise SystemExit("Launch as the systemd administrator")
        subprocess.run(["systemd-run", "--unit=prague-webcheck-24h", "--collect",
                        "-p", "Type=exec", "-p", "DynamicUser=yes",
                        "-p", "RuntimeDirectory=prague-webcheck-24h", "-p", "RuntimeDirectoryMode=0700",
                        "-p", "RuntimeMaxSec=24h", "-p", "PrivateTmp=yes", "-p", "ProtectSystem=strict",
                        "-p", "ProtectHome=yes", "-p", "NoNewPrivileges=yes", "-p", "TasksMax=40",
                        "-p", "MemoryMax=320M", "-p", "CapabilityBoundingSet=CAP_NET_BIND_SERVICE",
                        "-p", "AmbientCapabilities=CAP_NET_BIND_SERVICE", "/usr/bin/python3",
                        "-u", "-c", Path(__file__).read_text(), *sys.argv[1:]], check=True)
        return
    root = Path(os.environ["RUNTIME_DIRECTORY"])
    os.umask(0o077)
    for port in (80, PORT):
        with socket.socket() as sock:
            sock.bind((address, port))
    for host in sys.argv[2:]:
        try:
            with urllib.request.urlopen("https://" + host + "/", timeout=12) as resp:
                print(host, resp.status, len(resp.read(2_000_000)), flush=True)
        except OSError as error:
            print(host, "upstream check failed", str(error)[:140], flush=True)
    cert = issue_certificate(root, address)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert / "fullchain.pem", cert / "privkey.pem")
    with Server((address, PORT), context) as server:
        print("READY", address, PORT, len(FILE), DIGEST, flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
