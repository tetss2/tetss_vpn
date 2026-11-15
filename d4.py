#!/usr/bin/env python3
"""IPv6 control and passive transport metadata. No packet contents are retained."""
import base64,copy,hashlib,json,os,pathlib,re,socket,struct,subprocess,sys,time,urllib.parse
import sk,p2,p3
ROOT=pathlib.Path('/root/skylon-phase4')
CONF=pathlib.Path('/etc/skylon-phase4')
V6='2a04:ff07:d9:2069::1'
UNITS=['skylon-test','skylon-extra','skylon-hy-21','skylon-hy-22','skylon-hy-23','skylon-p3-xray','skylon-p3-hy27','skylon-p3-hy28']
PORTS={443,2443,5443,6443,8443,8448,8449,20443,11443}

def export(data):
    from cryptography.hazmat.primitives import serialization,hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    pub=serialization.load_pem_public_key(p3.PUBLIC_KEY.encode());key=os.urandom(32);nonce=os.urandom(12)
    ciphertext=AESGCM(key).encrypt(nonce,json.dumps(data).encode(),b'skylon-phase4')
    wrapped=pub.encrypt(key,padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    temp=sk.WEB/'diag4.tmp'
    sk.write_json(temp,{k:base64.b64encode(v).decode() for k,v in {'key':wrapped,'nonce':nonce,'ciphertext':ciphertext}.items()},False)
    temp.replace(sk.WEB/'diag4.enc.json')

def snapshot():
    files=['/etc/skylon-test/xray.json','/etc/skylon-phase2/extra.json','/etc/skylon-phase3/xray.json']+[f'/etc/skylon-phase2/hy-{n}.json' for n in [21,22,23]]+[f'/etc/skylon-phase3/hy{n}.json' for n in [27,28]]
    return {'hashes':{f:hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest() for f in files},'pids':{u:sk.run(['systemctl','show',u,'-p','MainPID','--value']).strip() for u in UNITS}}

def journals():
    result={}
    for unit in UNITS:
        raw=sk.run(['journalctl','-u',unit,'--since','today','-n','20000','--no-pager','-o','cat'])
        sources={};errors=[]
        for line in raw.splitlines():
            m=re.search(r'from (?:tcp:|udp:)?([0-9.]+):[0-9]+ accepted (tcp|udp):.*?\[([^\]]+)\]',line)
            if m:
                key=m[1]+' '+m[3];row=sources.setdefault(key,{'tcp':0,'udp':0,'first':line[:26],'last':line[:26]})
                row[m[2]]+=1;row['last']=line[:26]
            elif any(s in line.lower() for s in ['error','failed','timeout','reset','panic','killed']):
                clean=re.sub(r'(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?','[address]',line)
                errors.append(clean[:400])
        result[unit]={'accepted_sources':sources,'recent_errors':errors[-20:]}
    return result

def parse_packet(packet):
    if len(packet)<54:return None
    eth=struct.unpack('!H',packet[12:14])[0]
    if eth==0x0800:
        h=14+(packet[14]&15)*4;proto=packet[23]
        src=socket.inet_ntoa(packet[26:30]);dst=socket.inet_ntoa(packet[30:34])
        end=min(len(packet),14+struct.unpack('!H',packet[16:18])[0])
        if struct.unpack('!H',packet[20:22])[0]&0x1fff:return None
    elif eth==0x86dd:
        h=54;proto=packet[20];src=socket.inet_ntop(socket.AF_INET6,packet[22:38]);dst=socket.inet_ntop(socket.AF_INET6,packet[38:54]);end=min(len(packet),54+struct.unpack('!H',packet[18:20])[0])
    else:return None
    if proto not in [6,17] or end<h+8:return None
    sp,dp=struct.unpack('!HH',packet[h:h+4])
    if dst in [sk.IP,V6] and dp in PORTS:direction='in';remote=src;remoteport=sp;localport=dp
    elif src in [sk.IP,V6] and sp in PORTS:direction='out';remote=dst;remoteport=dp;localport=sp
    else:return None
    if remote in [sk.IP,V6,'127.0.0.1','::1']:return None
    flags=0;seq=0;ack=0
    if proto==6:
        if end<h+20:return None
        flags=packet[h+13];seq,ack=struct.unpack('!II',packet[h+4:h+12]);payload=max(0,end-h-((packet[h+12]>>4)*4))
    else:payload=max(0,end-h-8)
    return remote,remoteport,localport,proto,direction,flags,payload,seq,ack

def monitor():
    bundle=json.loads((ROOT/'bundle.json').read_text());start=time.time();end=start+7200
    sock=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(3));sock.settimeout(1)
    flows={};last_write=0
    while time.time()<end:
        try:packet=sock.recv(65535)
        except socket.timeout:packet=b''
        row=parse_packet(packet)
        if row:
            remote,rport,lport,proto,direction,flags,n,seq,ack=row
            key=f'{remote}|{rport}|{lport}|{proto}'
            if key not in flows and len(flows)<5000:
                flows[key]={'remote':remote,'remote_port':rport,'server_port':lport,'protocol':'tcp' if proto==6 else 'udp','first':time.time(),'in_packets':0,'out_packets':0,'in_bytes':0,'out_bytes':0,'in_syn':0,'out_synack':0,'in_rst':0,'out_rst':0,'in_fin':0,'out_fin':0,'out_initial_seq':None,'client_acked_bytes':0}
            if key in flows:
                f=flows[key];f['last']=time.time();f[direction+'_packets']+=1;f[direction+'_bytes']+=n
                if proto==6:
                    if direction=='in' and flags&2 and not flags&16:f['in_syn']+=1
                    if direction=='out' and flags&18==18:f['out_synack']+=1;f['out_initial_seq']=seq
                    if flags&4:f[direction+'_rst']+=1
                    if flags&1:f[direction+'_fin']+=1
                    if direction=='in' and flags&16 and f['out_initial_seq'] is not None:
                        delta=(ack-f['out_initial_seq']-1)&0xffffffff
                        if delta<1000000000:f['client_acked_bytes']=max(f['client_acked_bytes'],delta)
        if time.time()-last_write>=10:
            bundle['monitor']={'start':start,'until':end,'updated':time.time(),'running':True,'flows':list(flows.values()),'scope':'packet headers and byte/flag counters only; no packet payload or requested sites retained'}
            sk.write_json(ROOT/'observations.json',bundle);export(bundle);last_write=time.time()
    bundle['monitor']['running']=False;bundle['monitor']['updated']=time.time();sk.write_json(ROOT/'observations.json',bundle);export(bundle);sock.close()

def setup():
    assert os.geteuid()==0 and socket.gethostname()=='tetss-prague-test'
    assert V6 in sk.run(['hostname','-I']).split(),'IPv6 is not assigned'
    assert not ROOT.exists() and not CONF.exists(),'phase4 exists; do not recreate'
    before=snapshot();assert all(int(x)>0 for x in before['pids'].values())
    ROOT.mkdir(mode=0o700);CONF.mkdir(mode=0o700);sk.write_json(ROOT/'before.json',before)
    old=json.loads(pathlib.Path('/etc/skylon-phase3/xray.json').read_text())
    inbound=copy.deepcopy(next(i for i in old['inbounds'] if i['port']==5443));inbound.update(listen=V6,port=443,tag='phase4-ipv6')
    inbound['streamSettings']['sockopt']['V6Only']=True
    server=copy.deepcopy(old);server['inbounds']=[inbound];sk.write_json(CONF/'xray.json',server)
    sk.run([p2.XR,'run','-test','-c',str(CONF/'xray.json')])
    p=copy.deepcopy(next(p for p in json.loads(pathlib.Path('/root/skylon-phase3/bundle.json').read_text())['profiles'] if p['number']==29))
    name='Skylon Prague 33 IPv6 Vision 443';p.update(number=33,name=name,port=443)
    p['outbound']['settings']['vnext'][0].update(address=V6,port=443)
    u=urllib.parse.urlsplit(p['uri']);p['uri']=f'vless://{u.username}@[{V6}]:443?'+u.query+'#'+urllib.parse.quote(name)
    unit=f'''[Unit]
Description=Skylon IPv6 direct control profile 33
After=network-online.target
[Service]
DynamicUser=yes
LoadCredential=config.json:{CONF}/xray.json
ExecStart={p2.XR} run -c %d/config.json
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
MemoryMax=160M
Restart=on-failure
[Install]
WantedBy=multi-user.target
'''
    pathlib.Path('/etc/systemd/system/skylon-ipv6-control.service').write_text(unit)
    sk.run(['systemctl','daemon-reload']);sk.run(['systemd-run','--unit=skylon-v6-rollback','--on-active=15m','/bin/systemctl','stop','skylon-ipv6-control'])
    sk.run(['systemctl','start','skylon-ipv6-control'])
    original=sk.client_config
    try:
        sk.client_config=lambda profile,port:original(profile,port,loopback=False)
        p['test']=p2.transfer(p);assert p['test']['passed'],'IPv6 control transfer failed'
        p['sustained_test']=p2.transfer(p,True);assert p['sustained_test']['passed']
    finally:sk.client_config=original
    baseline=p2.transfer(next(p for p in json.loads(pathlib.Path('/root/skylon-phase3/bundle.json').read_text())['profiles'] if p['number']==32));assert baseline['passed']
    assert snapshot()==before,'original services changed'
    bundle={'server':sk.IP,'ipv6':V6,'profiles':[p],'original_services_unchanged':True,'baseline32':baseline,'journals':journals(),'created':time.time()}
    sk.write_json(ROOT/'bundle.json',bundle);export(bundle)
    sk.run(['systemctl','enable','skylon-ipv6-control']);sk.run(['systemctl','stop','skylon-v6-rollback.timer'])
    sk.run(['systemctl','reset-failed','skylon-delivery']);sk.run(['systemctl','start','skylon-delivery'])
    sk.run(['systemd-run','--unit=skylon-diag4','--property=RuntimeMaxSec=7500','--property=NoNewPrivileges=yes','--property=CapabilityBoundingSet=CAP_NET_RAW','--property=UMask=0077','/usr/bin/python3','/root/d4.py','monitor'])
    print('IPv6 profile 33 validated; passive metadata monitor active for two hours',flush=True)

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='monitor':monitor()
    else:
        try:setup()
        except Exception:
            subprocess.run(['systemctl','stop','skylon-ipv6-control'],capture_output=True);raise
