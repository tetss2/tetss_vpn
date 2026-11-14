#!/usr/bin/env python3
"""Add isolated Skylon test sidecars; never restart or rewrite the working VPN."""
import base64, concurrent.futures, copy, datetime, hashlib, ipaddress, json, os
import pathlib, secrets, shutil, socket, subprocess, sys, time, urllib.parse, urllib.request
import sk

ROOT=pathlib.Path('/root/skylon-phase2')
CONF=pathlib.Path('/etc/skylon-phase2')
HY_URL='https://github.com/HyNetworks/hysteria/releases/download/app/v2.13.0/hysteria-linux-amd64'
HY_SHA='907ba8c9693edb104b20582681fb7dc15639d5b64a9cbb616a7b539190a86691'
HY='/usr/local/bin/skylon-hysteria'
XR='/usr/local/bin/skylon-xray'
UNITS=['skylon-hy-21.service','skylon-hy-22.service','skylon-hy-23.service','skylon-extra.service']
SIZE=16754078

def export(bundle):
    from cryptography.hazmat.primitives import serialization,hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    pub=serialization.load_pem_public_key(sk.PUBLIC_KEY.encode()); aes=os.urandom(32); nonce=os.urandom(12)
    data=AESGCM(aes).encrypt(nonce,json.dumps(bundle).encode(),b'skylon-test-v1')
    wrapped=pub.encrypt(aes,padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    sk.write_json(sk.WEB/'phase2.enc.json',{k:base64.b64encode(v).decode() for k,v in {'key':wrapped,'nonce':nonce,'ciphertext':data}.items()},False)

def report(phase,**fields):
    print(phase,flush=True)
    sk.write_json(sk.WEB/'phase2-status.json',{'phase':phase,'time':int(time.time()),**fields},False)

def generate(directory, system_credentials=True):
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    key=ec.generate_private_key(ec.SECP256R1())
    subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Skylon private test endpoint')])
    now=datetime.datetime.utcnow()
    cert=(x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(days=1))
        .not_valid_after(now+datetime.timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(sk.IP))]),False)
        .sign(key,hashes.SHA256()))
    (directory/'cert.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (directory/'key.pem').write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    (directory/'key.pem').chmod(0o600)
    pin=cert.fingerprint(hashes.SHA256()).hex()
    profiles=[]; servers=[]
    for n,port,obfs in [(21,8448,False),(22,8449,True),(23,20443,True)]:
        password=secrets.token_urlsafe(24); obpass=secrets.token_urlsafe(24)
        cred=f'/run/credentials/skylon-hy-{n}.service' if system_credentials else str(directory)
        server={'listen':f'0.0.0.0:{port}','tls':{'cert':cred+'/cert.pem','key':cred+'/key.pem'},
            'auth':{'type':'password','password':password},'quic':{'disablePathMTUDiscovery':True},
            'ignoreClientBandwidth':True,'congestion':{'type':'bbr','bbrProfile':'conservative'},
            'acl':{'inline':[f'reject({net})' for net in sk.PRIVATE_NETS]+['direct(all)']},
            'outbounds':[{'name':'direct','type':'direct','direct':{'mode':4}}]}
        query={'sni':sk.IP,'insecure':'1','pinSHA256':pin}
        client={'server':f'127.0.0.1:{port}','auth':password,'tls':{'sni':sk.IP,'insecure':True,'pinSHA256':pin},
            'quic':{'disablePathMTUDiscovery':True},'socks5':{'listen':f'127.0.0.1:{19000+n}'}}
        if obfs:
            server['obfs']={'type':'salamander','salamander':{'password':obpass}}
            client['obfs']=copy.deepcopy(server['obfs'])
            query.update(obfs='salamander',**{'obfs-password':obpass})
        name=f'Skylon Prague {n} HY2 '+('Salamander' if obfs else 'QUIC')+f' {port}'
        profiles.append({'number':n,'name':name,'protocol':'Hysteria2','transport':'UDP','port':port,'obfs':'salamander' if obfs else None,
            'uri':f'hysteria2://{password}@{sk.IP}:{port}/?'+urllib.parse.urlencode(query)+'#'+urllib.parse.quote(name),'client':client})
        servers.append((n,server))
    seed,templates=sk.make_configs()
    base=next(x for x in seed['inbounds'] if x['port']==2087)
    base['port']=11443; base['tag']='phase2-google-xhttp'; base['settings']['clients'][0].pop('flow',None)
    base['streamSettings']['network']='xhttp'; base['streamSettings']['xhttpSettings']={'path':'/upload','mode':'auto'}
    seed['inbounds']=[base]
    for n,mode in [(24,'packet-up'),(25,'stream-up')]:
        p=copy.deepcopy(templates[6]); p.update(number=n,name=f'Skylon Prague {n} XHTTP Google {mode}',port=11443,transport='xhttp',mode=mode,flow='')
        out=p['outbound']; out['settings']['vnext'][0]['port']=11443;out['settings']['vnext'][0]['users'][0].pop('flow',None)
        out['streamSettings']['network']='xhttp';out['streamSettings']['xhttpSettings']={'path':'/upload','mode':mode}
        u=urllib.parse.urlsplit(p['uri']);q=dict(urllib.parse.parse_qsl(u.query));q.pop('flow',None);q.update(type='xhttp',path='/upload',mode=mode)
        p['uri']='vless://'+u.username+'@'+sk.IP+':11443?'+urllib.parse.urlencode(q)+'#'+urllib.parse.quote(p['name']);profiles.append(p)
    method='2022-blake3-aes-128-gcm'; password=base64.b64encode(os.urandom(16)).decode()
    seed['inbounds'].append({'tag':'phase2-ss2022','listen':'0.0.0.0','port':1443,'protocol':'shadowsocks',
        'settings':{'method':method,'password':password,'network':'tcp,udp'}})
    name='Skylon Prague 26 SS2022 AES128 1443'
    auth=base64.urlsafe_b64encode((method+':'+password).encode()).decode().rstrip('=')
    profiles.append({'number':26,'name':name,'protocol':'Shadowsocks2022','transport':'tcp/udp','port':1443,'method':method,
        'uri':f'ss://{auth}@{sk.IP}:1443#'+urllib.parse.quote(name),
        'outbound':{'tag':'proxy','protocol':'shadowsocks','settings':{'servers':[{'address':sk.IP,'port':1443,'method':method,'password':password}]}}})
    return servers,seed,profiles

def transfer(p,sustained=False,bad_pin=False):
    port=19000+p['number']+(100 if sustained else 0)+(200 if bad_pin else 0)
    cf=ROOT/f'client-{port}.json'; logpath=ROOT/f'client-{port}.log'; target=ROOT/f'download-{port}.zip'
    if p['protocol']=='Hysteria2':
        cfg=copy.deepcopy(p['client']); cfg['socks5']['listen']=f'127.0.0.1:{port}'
        if bad_pin: cfg['tls']['pinSHA256']='00'*32
        command=[HY,'client','-c',str(cf)]
    else:
        cfg=sk.client_config(p,port); command=[XR,'run','-c',str(cf)]
    sk.write_json(cf,cfg);log=logpath.open('w');proc=subprocess.Popen(command,stdout=log,stderr=log)
    try:
        ready=False
        for _ in range(70):
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.1): ready=True;break
            except OSError:
                if proc.poll() is not None: break
                time.sleep(.1)
        if not ready: return {'passed':False,'error':'client not ready','certificate_rejected':bad_pin}
        cmd=['curl','--silent','--show-error','--fail','--location','--connect-timeout','12','--max-time','125',
             '--proxy',f'socks5h://127.0.0.1:{port}','--output',str(target),'--write-out','%{http_code}',sk.XRAY_URL]
        if sustained:cmd[1:1]=['--limit-rate','256k']
        start=time.time();r=subprocess.run(cmd,capture_output=True,text=True,timeout=135)
        size=target.stat().st_size if target.exists() else 0
        match=size==SIZE and hashlib.sha256(target.read_bytes()).hexdigest()==sk.XRAY_SHA256
        return {'passed':r.returncode==0 and match,'bytes':size,'sha256_match':match,'seconds':round(time.time()-start,2),
            'http':r.stdout,'error':r.stderr[:200],'sustained':sustained,'scope':'server loopback VPN path to public HTTPS file'}
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
        log.close(); cf.unlink(missing_ok=True);target.unlink(missing_ok=True)

def invariant(digest,pid):
    assert hashlib.sha256(pathlib.Path('/etc/skylon-test/xray.json').read_bytes()).hexdigest()==digest,'working config changed'
    assert sk.run(['systemctl','show','skylon-test','-p','MainPID','--value']).strip()==pid,'working process changed'
    assert sk.run(['systemctl','is-active','skylon-test']).strip()=='active','working VPN stopped'

def setup():
    assert os.geteuid()==0 and socket.gethostname()=='tetss-prague-test'
    assert sk.IP in sk.run(['hostname','-I']).split()
    assert not CONF.exists(),'phase2 already exists; preserve keys'
    ROOT.mkdir(mode=0o700);CONF.mkdir(mode=0o700)
    old=pathlib.Path('/etc/skylon-test/xray.json');digest=hashlib.sha256(old.read_bytes()).hexdigest()
    shutil.copy2(old,ROOT/'working-config-backup.json')
    assert hashlib.sha256((ROOT/'working-config-backup.json').read_bytes()).hexdigest()==digest
    pid=sk.run(['systemctl','show','skylon-test','-p','MainPID','--value']).strip();invariant(digest,pid)
    old_profiles=json.loads((sk.ROOT/'bundle.json').read_text())['profiles']
    baseline=[p for p in old_profiles if p['number'] in [7,14,18]]
    for p in baseline: assert transfer(p)['passed'],'baseline failed before change'
    listeners=sk.run(['ss','-H','-lntup'])
    for port in [8448,8449,20443,11443,1443]:
        assert not any(':'+str(port)+' ' in l for l in listeners.splitlines()),'target port occupied'
    report('downloading official Hysteria')
    binary=ROOT/'hysteria';urllib.request.urlretrieve(HY_URL,binary)
    assert hashlib.sha256(binary.read_bytes()).hexdigest()==HY_SHA,'binary checksum mismatch'
    shutil.copy2(binary,HY);pathlib.Path(HY).chmod(0o755)
    servers,extra,profiles=generate(CONF)
    sk.write_json(CONF/'extra.json',extra);sk.run([XR,'run','-test','-c',str(CONF/'extra.json')])
    for p in profiles:
        if p['protocol']!='Hysteria2':
            sk.write_json(ROOT/'validate.json',sk.client_config(p,19000+p['number']))
            sk.run([XR,'run','-test','-c',str(ROOT/'validate.json')])
    (ROOT/'validate.json').unlink(missing_ok=True)
    common='''Restart=on-failure
RestartSec=3
DynamicUser=yes
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
MemoryMax=160M
LimitNOFILE=32768
[Install]
WantedBy=multi-user.target
'''
    for n,cfg in servers:
        sk.write_json(CONF/f'hy-{n}.json',cfg)
        unit=f'''[Unit]
Description=Skylon phase2 HY2 profile {n}
After=network-online.target
[Service]
LoadCredential=config.json:{CONF}/hy-{n}.json
LoadCredential=cert.pem:{CONF}/cert.pem
LoadCredential=key.pem:{CONF}/key.pem
ExecStart={HY} server -c %d/config.json
'''+common
        pathlib.Path(f'/etc/systemd/system/skylon-hy-{n}.service').write_text(unit)
    unit=f'''[Unit]
Description=Skylon isolated Google XHTTP and SS2022
After=network-online.target
[Service]
LoadCredential=config.json:{CONF}/extra.json
ExecStart={XR} run -c %d/config.json
'''+common
    pathlib.Path('/etc/systemd/system/skylon-extra.service').write_text(unit)
    sk.run(['systemctl','daemon-reload'])
    sk.run(['systemd-run','--unit=skylon-phase2-rollback','--on-active=15m','/bin/systemctl','stop',*UNITS])
    for unit in UNITS:
        sk.run(['systemctl','start',unit]);invariant(digest,pid)
        assert sk.run(['systemctl','is-active',unit]).strip()=='active'
    bundle={'server':sk.IP,'profiles':profiles,'original_config_sha256':digest,'original_pid_unchanged':True,
        'test_scope':'Local client on server, through loopback VPN inbound; Megafon path not tested','baseline':[]}
    sk.write_json(ROOT/'bundle.json',bundle)
    sk.run(['systemctl','start','skylon-delivery'])
    for p in profiles:
        report('testing phase2',profile=p['number']);p['test']=transfer(p);export(bundle)
        assert p['test']['passed'],f"profile {p['number']} failed"
    report('checking certificate pin')
    bundle['wrong_pin_rejected']=transfer(profiles[0],bad_pin=True).get('certificate_rejected') is True
    assert bundle['wrong_pin_rejected'],'wrong certificate was not rejected'
    report('minute-long phase2 tests')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for p,result in zip(profiles,pool.map(lambda p:transfer(p,True),profiles)):
            p['sustained_test']=result
    assert all(p['sustained_test']['passed'] for p in profiles),'sustained test failed'
    for p in baseline:
        result=transfer(p);bundle['baseline'].append({'number':p['number'],'test':result});assert result['passed']
    invariant(digest,pid)
    for unit in UNITS:sk.run(['systemctl','enable',unit])
    sk.run(['systemctl','stop','skylon-phase2-rollback.timer'])
    sk.write_json(ROOT/'bundle.json',bundle);export(bundle)
    report('complete',passed=len(profiles),sustained_passed=len(profiles),old_service_unchanged=True)

if __name__=='__main__':
    if '--validate-only' in sys.argv:
        path=pathlib.Path(sys.argv[-1]);path.mkdir(mode=0o700,exist_ok=True)
        servers,server,profiles=generate(path,False)
        sk.write_json(path/'extra.json',server)
        for n,c in servers:sk.write_json(path/f'hy-{n}.json',c)
        sk.write_json(path/'profiles.json',profiles)
        print('Generated six isolated validation profiles')
    else:
        try:setup()
        except Exception as e:
            subprocess.run(['systemctl','stop',*UNITS],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            report('failed',error=type(e).__name__);print(type(e).__name__,str(e)[:120]);raise
