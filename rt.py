#!/usr/bin/env python3
"""Retest existing Skylon credentials with a checksum-verified public download."""
import concurrent.futures, hashlib, json, os, pathlib, socket, subprocess, time
import sk

SIZE = 16754078

def test(profile, sustained=False):
    port=18100+profile['number']+(100 if sustained else 0)
    cf=sk.ROOT/f'retest-{port}.json'; logpath=sk.ROOT/f'retest-{port}.log'
    target=sk.ROOT/f'download-{port}.zip'
    sk.write_json(cf,sk.client_config(profile,port))
    log=logpath.open('w')
    proc=subprocess.Popen(['/usr/local/bin/skylon-xray','run','-c',str(cf)],stdout=log,stderr=log)
    try:
        for _ in range(40):
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.3): break
            except OSError: time.sleep(.1)
        cmd=['curl','--silent','--show-error','--fail','--location','--connect-timeout','15','--max-time','140',
             '--proxy',f'socks5h://127.0.0.1:{port}','--output',str(target),
             '--write-out','%{http_code} %{size_download} %{time_total}',sk.XRAY_URL]
        if sustained: cmd[1:1]=['--limit-rate','256k']
        t=time.time(); r=subprocess.run(cmd,capture_output=True,text=True,timeout=150)
        fields=r.stdout.strip().split(); size=target.stat().st_size if target.exists() else 0
        digest=hashlib.sha256(target.read_bytes()).hexdigest() if size else ''
        return {'passed':r.returncode==0 and size==SIZE and digest==sk.XRAY_SHA256,
            'bytes':size,'sha256_match':digest==sk.XRAY_SHA256,'seconds':round(time.time()-t,2),
            'http':fields[0] if fields else None,'curl_exit':r.returncode,'error':r.stderr[:300],
            'scope':'server loopback VPN client -> VPN inbound -> public HTTPS download',
            'source':'official Xray v26.11.9 release archive','sustained':sustained}
    except Exception as e: return {'passed':False,'error':type(e).__name__,'scope':'server loopback'}
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait()
        log.close(); cf.unlink(missing_ok=True); target.unlink(missing_ok=True)

assert os.geteuid()==0 and socket.gethostname()=='tetss-prague-test'
assert sk.IP in sk.run(['hostname','-I']).split()
bundle=json.loads((sk.ROOT/'bundle.json').read_text())
assert bundle['server']==sk.IP and len(bundle['profiles'])==20
sk.run(['systemctl','stop','skylon-setup-rollback.timer'])
sk.run(['systemctl','start','skylon-test.service'])
for p in bundle['profiles']:
    sk.status('retesting verified file',profile=p['number'],total=20)
    p['previous_test']=p.get('test'); p['test']=test(p)
    if not p['test']['passed']:
        p['first_attempt']=p['test']; p['test']=test(p)
    sk.encrypt_bundle(bundle)
chosen=[p for p in bundle['profiles'] if p['number'] in [1,5,10,13,18] and p['test']['passed']]
sk.status('sustained tests',count=len(chosen))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    for p,result in zip(chosen,pool.map(lambda p:test(p,True),chosen)):
        p['sustained_test']=result
sk.write_json(sk.ROOT/'bundle.json',bundle); sk.encrypt_bundle(bundle)
passed=sum(p['test']['passed'] for p in bundle['profiles'])
assert sk.run(['systemctl','is-active','skylon-test.service']).strip()=='active'
sk.status('complete',passed=passed,total=20,sustained_passed=sum(p['sustained_test']['passed'] for p in chosen))
print('Retest complete; credentials unchanged.',flush=True)
