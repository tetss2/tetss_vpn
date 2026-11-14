#!/usr/bin/env python3
"""Fresh dedicated Skylon test host only; never alters existing VPN services.

Client credentials are created on the host, stored mode 0600, and exported only
as an authenticated encrypted envelope for the task-specific delivery key.
"""
import base64, concurrent.futures, copy, hashlib, json, os, pathlib, secrets
import shutil, socket, subprocess, sys, tempfile, time, urllib.parse, urllib.request
import uuid, zipfile

IP = '109.248.43.81'
XRAY_URL = 'https://github.com/XTLS/Xray-core/releases/download/v26.11.9/Xray-linux-64.zip'
XRAY_SHA256 = 'b651f7e1d9966ee2c1b1ee1bf8b52c72771824d3065dce96bbc8bcc19ed95f82'
PUBLIC_KEY = '''-----BEGIN PUBLIC KEY-----
MIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEA0frkEb82VPilFQTMelE+
HeBN9DBQXuhLwJYgx5MUUbX/74UI4+MmPwMf8Cao514xZTW+jG9E8WM9UZUcjUrc
RK9mIaFrZoJfVBdz5a1yRRHBY/MjMT6RayM2p+sj5SlQGI67oRirpmLNLubxKFRV
cb6RA1/OcSg6u/o3nrXn0j0xcShuMp7gzaFcA3bDBSNMGFwp2/l7z5oQG0Qsn7cL
Uij8tuZwVBpWQH87L0S9yr2JAME9r6OE9Qy09vlt8+Wg+GT/WzsKZ/yeCDN1ZWSl
Oz4ULWm+HTRm3D1TKUN9s0rukeYfvY1mMV/Qzu35o0WhJB89cK/EjkeBhequkQFf
ndEfTTcyaHlgdl83lXNyPLWLkq3r2rYDOAesz78INEuv6iw5+llSu2s+GioEcjhL
3oktx7iy3nnHVXi0Uklw8Qi6FnciFATn+ceLDdwOCG7SdfRB57U+aZjQv7oIcfoU
7vt7FwONgs3upssRgBoDxydvghbEkqgtoFWAAjD4VsHZAgMBAAE=
-----END PUBLIC KEY-----
'''
ROOT = pathlib.Path('/root/skylon-test')
WEB = pathlib.Path('/var/lib/skylon-delivery')
PRIVATE_NETS = ['0.0.0.0/8','10.0.0.0/8','100.64.0.0/10','127.0.0.0/8','169.254.0.0/16','172.16.0.0/12','192.168.0.0/16','224.0.0.0/4','::1/128','fc00::/7','fe80::/10']

def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, **kwargs).stdout

def write_json(path, data, private=True):
    path = pathlib.Path(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    path.chmod(0o600 if private else 0o644)

def status(phase, **kwargs):
    print(phase, flush=True)
    if WEB.exists():
        write_json(WEB/'status.json', {'phase':phase, 'timestamp':int(time.time()), **kwargs}, False)

def make_configs():
    from cryptography.hazmat.primitives.asymmetric import x25519
    from cryptography.hazmat.primitives import serialization
    key = x25519.X25519PrivateKey.generate()
    def b64(b): return base64.urlsafe_b64encode(b).decode().rstrip('=')
    private = b64(key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()))
    public = b64(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))
    ident, sid = str(uuid.uuid4()), secrets.token_hex(8)
    ins, profiles = [], []
    def vless(port, sni, network, flow='', fp='chrome', mode=None, new=True):
        path = '/skylon-test'
        inbound_stream = {'network':network,'security':'reality','realitySettings':{
            'show':False,'target':sni+':443','xver':0,'serverNames':[sni],
            'privateKey':private,'shortIds':[sid]}}
        client_stream = {'network':network,'security':'reality','realitySettings':{
            'show':False,'serverName':sni,'fingerprint':fp,'publicKey':public,'shortId':sid}}
        query={'encryption':'none','security':'reality','type':'tcp' if network=='raw' else network,
               'sni':sni,'fp':fp,'pbk':public,'sid':sid}
        client={'id':ident,'encryption':'none'}
        server_client={'id':ident}
        if flow:
            client['flow']=flow; server_client['flow']=flow; query['flow']=flow
        if network=='grpc':
            inbound_stream['grpcSettings']={'serviceName':'skylon'}
            client_stream['grpcSettings']={'serviceName':'skylon'}
            query['serviceName']='skylon'
        if network=='xhttp':
            inbound_stream['xhttpSettings']={'path':path,'mode':'auto'}
            client_stream['xhttpSettings']={'path':path,'mode':mode}
            query.update(path=path,mode=mode)
        if new:
            ins.append({'tag':f'vless-{port}','listen':'0.0.0.0','port':port,'protocol':'vless',
                'settings':{'clients':[server_client],'decryption':'none'},'streamSettings':inbound_stream})
        n=len(profiles)+1
        title=f'Skylon Prague {n:02d} '+('Vision' if flow else network.upper())+f' {port} {fp}'
        uri='vless://'+ident+'@'+IP+':'+str(port)+'?'+urllib.parse.urlencode(query)+'#'+urllib.parse.quote(title)
        outbound={'tag':'proxy','protocol':'vless','settings':{'vnext':[{'address':IP,'port':port,'users':[client]}]},'streamSettings':client_stream}
        profiles.append({'number':n,'name':title,'protocol':'VLESS','transport':network,'port':port,
            'sni':sni,'fingerprint':fp,'mode':mode,'flow':flow,'uri':uri,'outbound':outbound})
    for i,fp in enumerate(['chrome','firefox','safari','edge']):
        vless(443,'www.microsoft.com','raw','xtls-rprx-vision',fp,new=i==0)
    vless(2053,'www.apple.com','raw','xtls-rprx-vision')
    vless(2083,'www.cloudflare.com','raw','xtls-rprx-vision')
    vless(2087,'dl.google.com','raw','xtls-rprx-vision')
    vless(2096,'www.microsoft.com','raw')
    vless(4443,'www.apple.com','raw')
    vless(7443,'www.microsoft.com','grpc')
    vless(7443,'www.microsoft.com','grpc',fp='firefox',new=False)
    vless(7444,'www.apple.com','grpc')
    for i,mode in enumerate(['packet-up','stream-up','stream-one']):
        vless(8443,'www.microsoft.com','xhttp',mode=mode,new=i==0)
    for i,mode in enumerate(['packet-up','stream-up']):
        vless(9443,'www.apple.com','xhttp',mode=mode,new=i==0)
    for port,method in [(8388,'chacha20-ietf-poly1305'),(8389,'aes-256-gcm'),(8390,'aes-128-gcm')]:
        password=secrets.token_urlsafe(24)
        ins.append({'tag':f'ss-{port}','listen':'0.0.0.0','port':port,'protocol':'shadowsocks',
                    'settings':{'method':method,'password':password,'network':'tcp,udp'}})
        n=len(profiles)+1; title=f'Skylon Prague {n:02d} SS {method} {port}'
        user=b64((method+':'+password).encode())
        outbound={'tag':'proxy','protocol':'shadowsocks','settings':{'servers':[{'address':IP,'port':port,'method':method,'password':password}]}}
        profiles.append({'number':n,'name':title,'protocol':'Shadowsocks','transport':'tcp/udp','port':port,
                         'method':method,'uri':f'ss://{user}@{IP}:{port}#'+urllib.parse.quote(title),'outbound':outbound})
    server={'log':{'loglevel':'warning'},'inbounds':ins,
            'outbounds':[{'tag':'direct','protocol':'freedom','settings':{'domainStrategy':'UseIPv4'}},
                         {'tag':'block','protocol':'blackhole'}],
            'routing':{'domainStrategy':'IPIfNonMatch','rules':[{'type':'field','ip':PRIVATE_NETS,'outboundTag':'block'}]}}
    return server, profiles

def client_config(profile, listen_port, loopback=True):
    out=copy.deepcopy(profile['outbound'])
    key='vnext' if out['protocol']=='vless' else 'servers'
    if loopback: out['settings'][key][0]['address']='127.0.0.1'
    return {'log':{'loglevel':'error'},'inbounds':[{'listen':'127.0.0.1','port':listen_port,
            'protocol':'socks','settings':{'udp':True}}],'outbounds':[out]}

def encrypt_bundle(bundle):
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    pub=serialization.load_pem_public_key(PUBLIC_KEY.encode())
    aes=os.urandom(32); nonce=os.urandom(12)
    ciphertext=AESGCM(aes).encrypt(nonce,json.dumps(bundle,ensure_ascii=False).encode(),b'skylon-test-v1')
    wrapped=pub.encrypt(aes,padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    write_json(WEB/'results.enc.json',{k:base64.b64encode(v).decode() for k,v in {'key':wrapped,'nonce':nonce,'ciphertext':ciphertext}.items()},False)

def test_profile(profile, sustained=False):
    port=18000+profile['number']+(100 if sustained else 0)
    cf=ROOT/f'client-{port}.json'; logfile=ROOT/f'client-{port}.log'
    write_json(cf,client_config(profile,port))
    log=logfile.open('w'); proc=subprocess.Popen(['/usr/local/bin/skylon-xray','run','-c',str(cf)],stdout=log,stderr=log)
    try:
        for i in range(40):
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.3): break
            except OSError: time.sleep(.1)
        cmd=['curl','--silent','--show-error','--fail','--connect-timeout','12','--max-time','100',
             '--proxy',f'socks5h://127.0.0.1:{port}','--output','/dev/null','--write-out','%{http_code} %{size_download} %{time_total}',
             'https://speed.cloudflare.com/__down?bytes=16777216']
        if sustained: cmd[1:1]=['--limit-rate','256k']
        t=time.time(); r=subprocess.run(cmd,capture_output=True,text=True,timeout=110)
        fields=r.stdout.strip().split(); size=int(float(fields[1])) if len(fields)==3 else 0
        return {'passed':r.returncode==0 and size==16777216,'bytes':size,'seconds':round(time.time()-t,2),
                'http':fields[0] if fields else None,'curl_exit':r.returncode,'error':r.stderr[:300],
                'scope':'server loopback VPN client -> VPN inbound -> public HTTPS download','sustained':sustained}
    except Exception as e: return {'passed':False,'error':type(e).__name__,'scope':'server loopback'}
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait()
        log.close(); cf.unlink(missing_ok=True)

def setup():
    assert os.geteuid()==0, 'root required'
    assert socket.gethostname()=='tetss-prague-test', 'unexpected host'
    assert IP in run(['hostname','-I']).split(), 'unexpected host IP'
    if pathlib.Path('/etc/skylon-test/xray.json').exists():
        raise RuntimeError('Existing test setup: refusing to overwrite credentials')
    for path in ['/etc/xray','/usr/local/etc/xray','/etc/x-ui','/etc/sing-box']:
        assert not pathlib.Path(path).exists(), 'Existing VPN installation detected'
    listeners=run(['ss','-H','-lntup'])
    for port in [80,443,2053,2083,2087,2096,4443,7443,7444,8443,9443,8388,8389,8390]:
        assert not any(':'+str(port)+' ' in l for l in listeners.splitlines()), 'occupied target port'
    ROOT.mkdir(mode=0o700,exist_ok=True); WEB.mkdir(parents=True,exist_ok=True); WEB.chmod(0o755)
    (ROOT/'listeners-before.txt').write_text(listeners)
    status('installing dependencies')
    env=dict(os.environ,DEBIAN_FRONTEND='noninteractive')
    run(['apt-get','update','-qq'],env=env,timeout=180)
    run(['apt-get','install','-y','-qq','curl','ca-certificates','python3-cryptography'],env=env,timeout=180)
    status('verifying official binary')
    archive=ROOT/'xray.zip'; urllib.request.urlretrieve(XRAY_URL,archive)
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==XRAY_SHA256, 'binary checksum mismatch'
    with zipfile.ZipFile(archive) as z: pathlib.Path('/usr/local/bin/skylon-xray').write_bytes(z.read('xray'))
    pathlib.Path('/usr/local/bin/skylon-xray').chmod(0o755)
    server,profiles=make_configs()
    pathlib.Path('/etc/skylon-test').mkdir(mode=0o700)
    write_json('/etc/skylon-test/xray.json',server)
    run(['/usr/local/bin/skylon-xray','run','-test','-c','/etc/skylon-test/xray.json'])
    for p in profiles:
        write_json(ROOT/'validate.json',client_config(p,18000))
        run(['/usr/local/bin/skylon-xray','run','-test','-c',str(ROOT/'validate.json')])
    (ROOT/'validate.json').unlink()
    unit='''[Unit]
Description=Skylon isolated VPN test profiles
After=network-online.target
Wants=network-online.target
[Service]
DynamicUser=yes
LoadCredential=config.json:/etc/skylon-test/xray.json
ExecStart=/usr/local/bin/skylon-xray run -c %d/config.json
Restart=on-failure
RestartSec=3
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
LimitNOFILE=65536
[Install]
WantedBy=multi-user.target
'''
    pathlib.Path('/etc/systemd/system/skylon-test.service').write_text(unit)
    delivery='''[Unit]
Description=Encrypted Skylon setup result delivery
After=network-online.target
[Service]
DynamicUser=yes
ExecStart=/usr/bin/python3 -m http.server 80 --bind 0.0.0.0 --directory /var/lib/skylon-delivery
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
RestrictAddressFamilies=AF_INET AF_UNIX
RuntimeMaxSec=14400
'''
    pathlib.Path('/etc/systemd/system/skylon-delivery.service').write_text(delivery)
    run(['systemctl','daemon-reload'])
    run(['systemd-run','--unit=skylon-setup-rollback','--on-active=15m','/bin/systemctl','stop','skylon-test.service'])
    run(['systemctl','start','skylon-delivery.service'])
    run(['systemctl','enable','--now','skylon-test.service'])
    assert run(['systemctl','is-active','skylon-test.service']).strip()=='active'
    bundle={'server':IP,'location':'Prague','xray_version':'26.11.9','created':int(time.time()),'profiles':profiles,
            'test_scope':'Tests originate on server through loopback; Russian ISP path not verified.'}
    encrypt_bundle(bundle)
    for p in profiles:
        status('testing',profile=p['number'],total=len(profiles))
        p['test']=test_profile(p)
        encrypt_bundle(bundle)
    chosen=[p for p in profiles if p['number'] in [1,10,13,18] and p['test']['passed']]
    status('sustained tests',count=len(chosen))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for p,result in zip(chosen,pool.map(lambda p:test_profile(p,True),chosen)):
            p['sustained_test']=result
    write_json(ROOT/'bundle.json',bundle)
    encrypt_bundle(bundle)
    passed=sum(p['test']['passed'] for p in profiles)
    if not passed: raise RuntimeError('No tested data path passed')
    assert run(['systemctl','is-active','skylon-test.service']).strip()=='active'
    run(['systemctl','stop','skylon-setup-rollback.timer'])
    status('complete',passed=passed,total=len(profiles))
    print('Completed. Client credentials are encrypted; no plaintext credentials published.',flush=True)

if __name__=='__main__':
    if '--validate-only' in sys.argv:
        directory=pathlib.Path(sys.argv[-1]); directory.mkdir(exist_ok=True)
        server,profiles=make_configs(); write_json(directory/'server.json',server)
        for p in profiles: write_json(directory/f"client-{p['number']:02d}.json",client_config(p,18000+p['number']))
        print('Generated',len(profiles),'validation profiles')
    else:
        try: setup()
        except Exception as exc:
            status('failed',error=type(exc).__name__)
            print('Setup failed:',type(exc).__name__,str(exc)[:160],flush=True)
            raise
