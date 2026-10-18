import asyncio
from types import SimpleNamespace
import pytest
from kairo.companion import Companion
from kairo.companion_setup import prepare

def fixture():
    now=[0]
    async def approve(*args): return True
    adapter=SimpleNamespace(prepare=lambda a,b:b,execute=lambda a,b:{'image':'fixture','mime':'image/jpeg'})
    c=Companion(SimpleNamespace(request=approve),SimpleNamespace(record=lambda *a:None),adapter,lambda:now[0])
    token=c.pair(c.issue(['screen','windows'])['code'])['token']
    return c,token,now

def test_mirroring_requires_approval_expires_and_can_stop():
    async def run():
        c,token,now=fixture()
        with pytest.raises(PermissionError): await c.frame(token)
        await c.control(token,1,'mirror_start',{})
        assert c.mirroring()
        assert (await c.frame(token))['mime']=='image/jpeg'
        with pytest.raises(ValueError): await c.frame(token)
        now[0]=301
        with pytest.raises(PermissionError): await c.frame(token)
        assert not c.mirroring()
        await c.control(token,2,'mirror_start',{})
        c.stop_mirroring()
        with pytest.raises(PermissionError): await c.frame(token)
    asyncio.run(run())

def test_mirror_denial_and_revoke_during_approval():
    async def run():
        c,token,now=fixture()
        async def deny(*args):return False
        c.authority.request=deny
        assert (await c.control(token,1,'mirror_start',{}))['denied']
        assert not c.mirroring()
        async def revoke(*args):
            c.revoke()
            return True
        c.authority.request=revoke
        now[0]=1
        with pytest.raises(PermissionError):await c.control(token,2,'mirror_start',{})
        assert not c.mirroring()
    asyncio.run(run())

def test_revocation_during_frame_does_not_return_image():
    async def run():
        c,token,_=fixture()
        await c.control(token,1,'mirror_start',{})
        def execute(*args):
            c.revoke()
            return {'image':'private'}
        c.adapter.execute=execute
        with pytest.raises(PermissionError):await c.frame(token)
    asyncio.run(run())

def test_phone_disconnect_revokes_token():
    c,token,_=fixture()
    c.disconnect(token)
    with pytest.raises(PermissionError):c.authenticate(token,'screen')

def test_window_change_requires_approval_and_scope():
    async def run():
        c,token,_=fixture()
        asked=[]
        async def approve(*args):
            asked.append(args)
            return True
        c.authority.request=approve
        await c.control(token,1,'window',{'hwnd':123,'operation':'close'})
        assert asked[0][1]=='companion_window'
        c2,_,_=fixture()
        t=c2.pair(c2.issue(['pointer'])['code'])['token']
        with pytest.raises(PermissionError):await c2.control(t,1,'windows',{})
    asyncio.run(run())

def test_tls_setup_reuses_ca_and_contains_correct_ip(tmp_path,monkeypatch):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    import ipaddress
    monkeypatch.setattr('kairo.companion_setup.local_addresses',lambda:['192.168.1.50'])
    data=prepare(tmp_path,'192.168.1.50')
    leaf=x509.load_pem_x509_certificate(open(data['certfile'],'rb').read())
    assert ipaddress.ip_address('192.168.1.50') in leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.IPAddress)
    assert prepare(tmp_path,'192.168.1.50')['fingerprint']==data['fingerprint']
    with pytest.raises(ValueError):prepare(tmp_path,'8.8.8.8')

def test_tls_transport_pairs_and_serves_approved_frames(tmp_path,monkeypatch):
    import json
    import ssl
    import socket
    import threading
    import urllib.request
    import urllib.error
    from kairo.companion_server import start_companion
    monkeypatch.setattr('kairo.companion_setup.local_addresses',lambda:['127.0.0.1'])
    monkeypatch.setattr('kairo.companion_server.lan_address',lambda address:address)
    config=prepare(tmp_path,'127.0.0.1')
    c,_,now=fixture()
    paircode=c.issue(['screen'])['code']
    loop=asyncio.new_event_loop()
    thread=threading.Thread(target=loop.run_forever,daemon=True);thread.start()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=start_companion(c,loop,'127.0.0.1',port,config['certfile'],config['keyfile'])
    context=ssl.create_default_context(cadata=ssl.DER_cert_to_PEM_cert(open(config['trust_file'],'rb').read()))
    url='https://127.0.0.1:'+str(port)
    def post(path,data,token=''):
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+token
        request=urllib.request.Request(url+path,json.dumps(data).encode(),headers)
        with urllib.request.urlopen(request,context=context,timeout=5) as response:return json.load(response)
    try:
        with urllib.request.urlopen(url,context=context,timeout=5) as response:
            assert b'Start live view' in response.read()
        with pytest.raises(urllib.error.HTTPError):post('/frame',{})
        token=post('/pair',{'code':paircode})['token']
        assert post('/control',{'sequence':1,'action':'mirror_start','args':{}},token)['ok']
        assert post('/frame',{},token)['image']=='fixture'
        post('/disconnect',{},token)
        with pytest.raises(urllib.error.HTTPError):post('/frame',{},token)
    finally:
        server.shutdown();server.server_close();loop.call_soon_threadsafe(loop.stop);thread.join();loop.close()
