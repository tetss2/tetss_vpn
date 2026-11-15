#!/usr/bin/env python3
"""Use the already dual-stack listener; preserve all existing keys and services."""
import copy,json,pathlib,socket,time,urllib.parse
import d4,sk,p2
assert socket.gethostname()=='tetss-prague-test'
before=json.loads((d4.ROOT/'before.json').read_text())
assert d4.snapshot()==before
sk.run(['systemctl','stop','skylon-ipv6-control','skylon-v6-rollback.timer'])
sk.run(['systemctl','reset-failed','skylon-ipv6-control'])
p=copy.deepcopy(next(x for x in json.loads(pathlib.Path('/root/skylon-phase3/bundle.json').read_text())['profiles'] if x['number']==29))
name='Skylon Prague 33 IPv6 Vision 5443'
p.update(number=33,name=name)
p['outbound']['settings']['vnext'][0]['address']=d4.V6
u=urllib.parse.urlsplit(p['uri'])
p['uri']=f'vless://{u.username}@[{d4.V6}]:5443?'+u.query+'#'+urllib.parse.quote(name)
original=sk.client_config
try:
    sk.client_config=lambda profile,port:original(profile,port,loopback=False)
    p['test']=p2.transfer(p);print(json.dumps(p['test']),flush=True)
    assert p['test']['passed']
    p['sustained_test']=p2.transfer(p,True);print(json.dumps(p['sustained_test']),flush=True)
    assert p['sustained_test']['passed']
finally:sk.client_config=original
for result in [p['test'],p['sustained_test']]:result['scope']='server client through assigned IPv6 and existing dual-stack listener; mobile network not tested'
baseline=p2.transfer(next(x for x in json.loads(pathlib.Path('/root/skylon-phase3/bundle.json').read_text())['profiles'] if x['number']==32))
assert baseline['passed'] and d4.snapshot()==before
bundle={'server':sk.IP,'ipv6':d4.V6,'profiles':[p],'original_services_unchanged':True,'baseline32':baseline,'journals':d4.journals(),'created':time.time()}
sk.write_json(d4.ROOT/'bundle.json',bundle);d4.export(bundle)
sk.run(['systemctl','reset-failed','skylon-delivery']);sk.run(['systemctl','start','skylon-delivery'])
sk.run(['systemd-run','--unit=skylon-diag4','--property=RuntimeMaxSec=7500','--property=NoNewPrivileges=yes','--property=CapabilityBoundingSet=CAP_NET_RAW','--property=UMask=0077','/usr/bin/python3','/root/d4.py','monitor'])
print('IPv6 33 passed; existing eight services unchanged; metadata monitor active for two hours',flush=True)
