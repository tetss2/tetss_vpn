#!/usr/bin/env python3
"""Isolated direct-protocol tests; preserve all existing VPN services and keys."""
import base64, copy, hashlib, json, os, pathlib, secrets, socket, subprocess, time, urllib.parse
import sk, p2
ROOT=pathlib.Path('/root/skylon-phase3')
CONF=pathlib.Path('/etc/skylon-phase3')
UNITS=['skylon-p3-hy27','skylon-p3-hy28','skylon-p3-xray']
PUBLIC_KEY='-----BEGIN PUBLIC KEY-----\nMIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEA3gMwmhBLn+eXxn0O+5MK\nS5KiUzHdqSiqhppI3XI14vrOlg/u01dXye6XEJMVqhjfTyN12YVxfmHbluP97Nq6\nXcQJ3fliMle+mq4oA5p6mgm/ObgWmLHsLHteeZlh0p2aoNTYFzd17/VaYwhP3YGa\ntxUbwQzxKcMGY3zyL91DLyrNlATcY8NBOoJw5qXUrLYSM9IURmn4FvYM264PExcB\nOnU9evtTXENOTapwFCzi8TDgQU2RMNo/HB/crwIZk03xMa1Ns/sSxaUfp/ly21O2\n3fLxxIFqbbCvCG5zGhtAfC/0ALZUhH4uVM0nEB+IJH6TcOq9AK93WGUlSGnWxuzC\nB93B7qAuUkhZIAE9/KJsCy6BjuhJcyN2rWcsbgeRluXAjrGphEqBL62lW4jJAO9y\neHvbRM2UbRO5yCv13HpF5KPImOliH3Hf1HmPybimBzBb5krAqaokRXTQDDhURsoW\n2H71+cFcumyHY8LVlDd7us0VuzgRjIIfj51A2kjq9lRPAgMBAAE=\n-----END PUBLIC KEY-----\n'

def export(data):
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    pub=serialization.load_pem_public_key(PUBLIC_KEY.encode()); key=os.urandom(32); nonce=os.urandom(12)
    cipher=AESGCM(key).encrypt(nonce,json.dumps(data).encode(),b'skylon-phase3')
    wrapped=pub.encrypt(key,padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    sk.write_json(sk.WEB/'phase3.enc.json',{k:base64.b64encode(v).decode() for k,v in {'key':wrapped,'nonce':nonce,'ciphertext':cipher}.items()},False)

def status(phase,**kw):
    print(phase,flush=True)
    sk.write_json(sk.WEB/'phase3-status.json',{'phase':phase,'time':int(time.time()),**kw},False)

def snapshot():
    files=['/etc/skylon-test/xray.json','/etc/skylon-phase2/extra.json']+[f'/etc/skylon-phase2/hy-{n}.json' for n in [21,22,23]]
    units=['skylon-test','skylon-extra','skylon-hy-21','skylon-hy-22','skylon-hy-23']
    return {'hashes':{f:hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest() for f in files},
            'pids':{u:sk.run(['systemctl','show',u,'-p','MainPID','--value']).strip() for u in units}}

def diagnostics():
    lines=sk.run(['journalctl','-u','skylon-test','-u','skylon-extra','-u','skylon-hy-21','-u','skylon-hy-22','-u','skylon-hy-23','--since','6 hours ago','--no-pager','-o','cat']).lower()
    return {'log_keyword_counts':{k:lines.count(k) for k in ['timeout','reset by peer','broken pipe','handshake','out of memory','failed','error']},
            'memory':sk.run(['free','-m']), 'units':{u:sk.run(['systemctl','is-active',u]).strip() for u in snapshot()['pids']}}

def generate():
    servers,seed,profiles=p2.generate(CONF)
    hy=[];result=[]
    for src,n,port in [(1,27,443),(0,28,8443)]:
        cfg=copy.deepcopy(servers[src][1]);p=copy.deepcopy(profiles[src]); old=p['port']
        cfg['listen']=f'0.0.0.0:{port}'
        cfg['tls']={'cert':f'/run/credentials/skylon-p3-hy{n}.service/cert.pem','key':f'/run/credentials/skylon-p3-hy{n}.service/key.pem'}
        name=f'Skylon Prague {n} HY2 '+('Salamander' if src else 'QUIC')+f' UDP{port}'
        p.update(number=n,port=port,name=name)
        p['client']['server']=f'127.0.0.1:{port}'
        p['uri']=p['uri'].split('#')[0].replace(f':{old}/',f':{port}/')+'#'+urllib.parse.quote(name)
        result.append(p);hy.append((n,cfg))
    server,templates=sk.make_configs();inbounds=[]
    for n,port,kind in [(29,5443,'vision'),(30,6443,'packet-up'),(31,6443,'stream-up'),(32,2443,'trojan')]:
        p=copy.deepcopy(templates[6]); inbound=copy.deepcopy(next(i for i in server['inbounds'] if i['port']==2087))
        inbound['port']=port; inbound['tag']=f'phase3-{n}'
        inbound['streamSettings']['sockopt']={'tcpMaxSeg':1200,'tcpKeepAliveIdle':30,'tcpKeepAliveInterval':10}
        p.update(number=n,port=port,name=f'Skylon Prague {n} {kind} MSS1200 {port}')
        out=p['outbound'];out['settings']['vnext'][0]['port']=port
        u=urllib.parse.urlsplit(p['uri']);q=dict(urllib.parse.parse_qsl(u.query));auth=u.username;scheme='vless'
        if kind in ['packet-up','stream-up']:
            inbound['settings']['clients'][0].pop('flow',None);inbound['streamSettings']['network']='xhttp'
            inbound['streamSettings']['xhttpSettings']={'path':'/p3','mode':'auto'}
            out['settings']['vnext'][0]['users'][0].pop('flow',None);out['streamSettings']['network']='xhttp'
            out['streamSettings']['xhttpSettings']={'path':'/p3','mode':kind}
            p.update(transport='xhttp',flow='',mode=kind);q.pop('flow',None);q.update(type='xhttp',path='/p3',mode=kind)
        elif kind=='trojan':
            auth=secrets.token_urlsafe(24);scheme='trojan';p.update(protocol='Trojan',flow='')
            inbound['protocol']='trojan';inbound['settings']={'clients':[{'password':auth}]}
            out['protocol']='trojan';out['settings']={'servers':[{'address':sk.IP,'port':port,'password':auth}]}
            q.pop('encryption',None);q.pop('flow',None)
        p['uri']=scheme+'://'+auth+'@'+sk.IP+':'+str(port)+'?'+urllib.parse.urlencode(q)+'#'+urllib.parse.quote(p['name'])
        result.append(p)
        if n!=31:inbounds.append(inbound)
    server['inbounds']=inbounds
    return hy,server,result

def main():
    assert os.geteuid()==0 and socket.gethostname()=='tetss-prague-test'
    assert sk.IP in sk.run(['hostname','-I']).split()
    assert not ROOT.exists() and not CONF.exists(),'phase3 already exists; preserve keys'
    before=snapshot(); diag=diagnostics()
    ROOT.mkdir(mode=0o700);CONF.mkdir(mode=0o700)
    sk.write_json(ROOT/'before.json',before)
    for f in before['hashes']:
        dst=ROOT/(str(f).strip('/').replace('/','_')+'.backup');dst.write_bytes(pathlib.Path(f).read_bytes());dst.chmod(0o600)
    listeners=sk.run(['ss','-H','-lntup'])
    for port,proto in [(443,'udp'),(8443,'udp'),(5443,'tcp'),(6443,'tcp'),(2443,'tcp')]:
        assert not any(line.startswith(proto) and f':{port} ' in line for line in listeners.splitlines()),f'occupied {proto}/{port}'
    hy,server,profiles=generate();sk.write_json(CONF/'xray.json',server)
    sk.run([p2.XR,'run','-test','-c',str(CONF/'xray.json')])
    for p in profiles:
        if p['protocol']!='Hysteria2':
            sk.write_json(ROOT/'validate.json',sk.client_config(p,19000+p['number']));sk.run([p2.XR,'run','-test','-c',str(ROOT/'validate.json')])
    (ROOT/'validate.json').unlink(missing_ok=True)
    common='''Restart=on-failure
RestartSec=3
DynamicUser=yes
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
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
    for n,cfg in hy:
        sk.write_json(CONF/f'hy{n}.json',cfg)
        pathlib.Path(f'/etc/systemd/system/skylon-p3-hy{n}.service').write_text(f'''[Unit]
Description=Skylon phase3 HY2 {n}
After=network-online.target
[Service]
LoadCredential=config.json:{CONF}/hy{n}.json
LoadCredential=cert.pem:{CONF}/cert.pem
LoadCredential=key.pem:{CONF}/key.pem
ExecStart={p2.HY} server -c %d/config.json
'''+common)
    pathlib.Path('/etc/systemd/system/skylon-p3-xray.service').write_text(f'''[Unit]
Description=Skylon phase3 MSS1200 direct tests
After=network-online.target
[Service]
LoadCredential=config.json:{CONF}/xray.json
ExecStart={p2.XR} run -c %d/config.json
'''+common)
    sk.run(['systemctl','daemon-reload']);sk.run(['systemd-run','--unit=skylon-p3-rollback','--on-active=15m','/bin/systemctl','stop',*UNITS])
    sk.run(['systemctl','start',*UNITS]);assert snapshot()==before
    bundle={'server':sk.IP,'profiles':profiles,'diagnostics':diag,'scope':'server loopback only, not Megafon','baseline':[]}
    sk.write_json(ROOT/'bundle.json',bundle);export(bundle)
    sk.run(['systemctl','reset-failed','skylon-delivery']);sk.run(['systemctl','start','skylon-delivery'])
    for p in profiles:
        status('testing',profile=p['number']);p['test']=p2.transfer(p);export(bundle)
        assert p['test']['passed'],f'profile {p["number"]} failed'
    import concurrent.futures
    status('minute-long transfer tests')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for p,r in zip(profiles,pool.map(lambda p:p2.transfer(p,True),profiles)):p['sustained_test']=r
    assert all(p['sustained_test']['passed'] for p in profiles),'sustained test failed'
    originals=json.loads((sk.ROOT/'bundle.json').read_text())['profiles']
    for p in originals:
        if p['number'] in [7,14,18]:
            r=p2.transfer(p);bundle['baseline'].append({'number':p['number'],'test':r});assert r['passed']
    assert snapshot()==before,'original services changed'
    bundle['old_configs_and_pids_unchanged']=True
    sk.run(['systemctl','enable',*UNITS]);sk.run(['systemctl','stop','skylon-p3-rollback.timer'])
    sk.write_json(ROOT/'bundle.json',bundle);export(bundle);status('complete',passed=len(profiles))

if __name__=='__main__':
    try:main()
    except Exception as e:
        subprocess.run(['systemctl','stop',*UNITS],capture_output=True)
        status('failed',error=type(e).__name__);print(str(e)[:150]);raise
