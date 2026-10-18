"""LAN companion capability boundary. Transport must provide TLS before accepting tokens."""

import asyncio

import hashlib

import hmac

import ipaddress

import secrets

import time



SCOPES = {'screen', 'pointer', 'keyboard', 'media', 'windows'}





def lan_address(address):

    ip = ipaddress.ip_address(address)

    ranges = ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')

    if ip.version != 4 or not any(ip in ipaddress.ip_network(n) for n in ranges):

        raise ValueError('Choose a specific RFC1918 LAN IPv4 address')

    return str(ip)





class Companion:

    def __init__(self, authority, journal, adapter=None, clock=time.monotonic):

        self.authority, self.journal, self.adapter, self.clock = authority, journal, adapter, clock

        self.pairing = None

        self.sessions = {}

        self.lock = asyncio.Lock()

        self.frame_lock = asyncio.Lock()
        self.share_state = False



    def issue(self, scopes):

        if not isinstance(scopes, list) or not scopes or not set(scopes) <= SCOPES:

            raise ValueError('Select explicit companion permissions')

        code = secrets.token_hex(6).upper()

        self.pairing = {'digest': hashlib.sha256(code.encode()).digest(), 'expires': self.clock() + 120, 'scopes': set(scopes), 'attempts': 0}

        return {'code': code, 'expires_in': 120, 'scopes': scopes}



    def pair(self, code):

        grant = self.pairing

        if not grant or self.clock() >= grant['expires'] or grant['attempts'] >= 5:

            raise PermissionError('Pairing expired; create a new code on the PC')

        grant['attempts'] += 1

        if not isinstance(code, str) or not hmac.compare_digest(hashlib.sha256(code.encode()).digest(), grant['digest']):

            raise PermissionError('Invalid pairing code')

        token = secrets.token_urlsafe(32)

        identity = secrets.token_hex(8)

        self.sessions[hashlib.sha256(token.encode()).hexdigest()] = {'id': identity, 'scopes': grant['scopes'], 'expires': self.clock() + 3600, 'sequence': 0, 'last': float('-inf'), 'mirror_until': 0, 'last_frame': float('-inf')}

        self.pairing = None

        self.journal.record(identity, 'companion_pair', 'completed', {'scopes': sorted(grant['scopes'])})

        return {'token': token, 'id': identity, 'expires_in': 3600, 'scopes': sorted(grant['scopes'])}



    def authenticate(self, token, scope):

        if not isinstance(token, str) or len(token) > 200:

            raise PermissionError('Invalid session')

        session = self.sessions.get(hashlib.sha256(token.encode()).hexdigest())

        if not session or self.clock() >= session['expires'] or scope not in session['scopes']:

            raise PermissionError('Session expired, revoked or permission missing')

        return session



    def revoke(self, identity=None):

        self.sessions = {k: v for k, v in self.sessions.items() if identity is not None and v['id'] != identity}

        self.pairing = None

        self.journal.record(identity or 'all', 'companion_revoke', 'completed')
        self.sharing_changed()



    def disconnect(self, token):

        if not isinstance(token, str) or len(token) > 200:

            raise PermissionError('Invalid session')

        digest = hashlib.sha256(token.encode()).hexdigest()

        session = self.sessions.pop(digest, None)

        if not session:

            raise PermissionError('Session expired or revoked')

        self.journal.record(session['id'], 'companion_disconnect', 'completed')
        self.sharing_changed()

        return {'ok': True}



    async def control(self, token, sequence, action, args):

        mapping = {'move': 'pointer', 'click': 'pointer', 'type': 'keyboard', 'media': 'media', 'screen': 'screen', 'window': 'windows', 'windows': 'windows', 'mirror_start': 'screen', 'mirror_stop': 'screen'}

        if action not in mapping or not isinstance(args, dict):

            raise ValueError('Unsupported control')

        scope = mapping[action]

        async with self.lock:

            session = self.authenticate(token, scope)

            if type(sequence) is not int or sequence != session['sequence'] + 1:

                raise PermissionError('Out-of-order or replayed command')

            if self.clock() - session['last'] < .04:

                raise PermissionError('Control rate limit')

            session['sequence'], session['last'] = sequence, self.clock()

            if not self.adapter:

                raise ValueError('Control adapter is not enabled')

            if action == 'mirror_stop':

                session['mirror_until'] = 0

                return {'ok': True}

            if action == 'mirror_start':

                if args:

                    raise ValueError('Unexpected mirror arguments')

                allowed = await self.authority.request(session['id'], 'companion_mirror', {'view': 'Entire primary screen', 'duration_seconds': 300, 'frame_rate': 2})

                self.authenticate(token, scope)

                if not allowed:

                    return {'denied': True}

                session['mirror_until'] = self.clock() + 300
                self.sharing_changed()
                asyncio.get_running_loop().call_later(300.1, self.sharing_changed)

                self.journal.record(session['id'], 'companion_mirror', 'started')

                return {'ok': True, 'expires_in': 300}

            prepared = self.adapter.prepare(action, args)

            if action not in {'move', 'media', 'windows'}:

                if not await self.authority.request(session['id'], 'companion_' + action, prepared):

                    self.journal.record(session['id'], 'companion_' + action, 'denied')

                    return {'denied': True}

            self.authenticate(token, scope)

            result = await asyncio.to_thread(self.adapter.execute, action, prepared)

            self.journal.record(session['id'], 'companion_' + action, 'completed')

            return result



    def stop_mirroring(self):

        for session in self.sessions.values():

            session['mirror_until'] = 0

        self.journal.record('all', 'companion_mirror', 'stopped')
        self.sharing_changed()



    def sharing_changed(self):
        active = self.mirroring()
        if self.share_state != active:
            self.share_state = active
            events = getattr(self.authority, 'events', None)
            if events:
                events.emit('companion_share', active=active)

    def mirroring(self):

        return any(self.clock() < min(s['expires'], s['mirror_until']) for s in tuple(self.sessions.values()))



    async def frame(self, token):

        session = self.authenticate(token, 'screen')

        if self.clock() >= session['mirror_until']:

            raise PermissionError('Screen sharing is stopped or expired')

        if self.clock() - session['last_frame'] < .45:

            raise ValueError('Wait before requesting another frame')

        session['last_frame'] = self.clock()

        if self.frame_lock.locked():

            raise ValueError('Screen capture is busy')

        async with self.frame_lock:

            frame = await asyncio.to_thread(self.adapter.execute, 'frame', {})

        self.authenticate(token, 'screen')

        if self.clock() >= session['mirror_until']:

            raise PermissionError('Screen sharing stopped during capture')

        return frame





class WindowsControls:

    def target(self):

        import win32gui

        import win32process

        hwnd = win32gui.GetForegroundWindow()

        title = win32gui.GetWindowText(hwnd)

        if not title or title.startswith('KAIRO'):

            raise ValueError('Focus the intended application on the PC first')

        return {'hwnd': hwnd, 'pid': win32process.GetWindowThreadProcessId(hwnd)[1], 'title': title}



    def prepare(self, action, args):

        if action == 'move' and set(args) == {'dx', 'dy'} and all(type(x) is int and abs(x) <= 200 for x in args.values()):

            return dict(args)

        if action == 'click' and args == {'button': 'left'}:

            import win32gui

            target = self.target()

            x, y = win32gui.GetCursorPos()

            if win32gui.GetAncestor(win32gui.WindowFromPoint((x, y)), 2) != target['hwnd']:

                raise ValueError('Pointer must be inside the focused target window')

            return {**args, 'x': x, 'y': y, 'target': target}

        if action == 'type' and set(args) == {'text'} and isinstance(args['text'], str) and 0 < len(args['text']) <= 500 and all(32 <= ord(x) < 127 for x in args['text']):

            return {**args, 'target': self.target()}

        if action == 'media' and set(args) == {'key'} and args['key'] in {'volumeup', 'volumedown', 'volumemute', 'playpause', 'nexttrack', 'prevtrack'}:

            return dict(args)

        if action == 'windows' and not args:

            return {}

        if action == 'window' and set(args) == {'hwnd', 'operation'} and type(args['hwnd']) is int and args['operation'] in {'focus', 'minimize', 'maximize', 'close'}:

            windows = self.execute('windows', {})['windows']

            target = next((w for w in windows if w['hwnd'] == args['hwnd']), None)

            if not target:

                raise ValueError('Window is no longer available')

            return {**args, 'target': target}

        if action == 'screen' and not args:

            return {}

        raise ValueError('Control is unavailable or arguments are invalid; choose a supported control')



    def execute(self, action, args):

        import pyautogui

        if action in {'click', 'type', 'window'}:

            import win32gui

            import win32process

            target = args['target']

            hwnd = target['hwnd']

            if not win32gui.IsWindow(hwnd) or win32process.GetWindowThreadProcessId(hwnd)[1] != target['pid'] or win32gui.GetWindowText(hwnd) != target['title']:

                raise ValueError('Approved target window changed; action cancelled')

            if action != 'window':

                win32gui.SetForegroundWindow(hwnd)

            if action != 'window' and win32gui.GetForegroundWindow() != hwnd:

                raise ValueError('Could not restore approved target window')

        if action == 'windows':

            import win32gui

            import win32process

            windows = []

            def collect(hwnd, _):

                title = win32gui.GetWindowText(hwnd)

                if win32gui.IsWindowVisible(hwnd) and title and not title.startswith('KAIRO'):

                    windows.append({'hwnd': hwnd, 'title': title[:200], 'pid': win32process.GetWindowThreadProcessId(hwnd)[1]})

            win32gui.EnumWindows(collect, None)

            return {'windows': windows[:60]}

        if action == 'window':

            import win32con

            if args['operation'] == 'close':

                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

            elif args['operation'] == 'minimize':

                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

            else:

                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE if args['operation'] == 'maximize' else win32con.SW_RESTORE)

                win32gui.SetForegroundWindow(hwnd)

            return {'ok': True}

        if action == 'move':

            pyautogui.moveRel(args['dx'], args['dy'])

        elif action == 'click':

            if win32gui.GetAncestor(win32gui.WindowFromPoint((args['x'], args['y'])), 2) != args['target']['hwnd']:

                raise ValueError('Approved click target moved or became covered')

            pyautogui.click(args['x'], args['y'], button='left')

        elif action == 'type':

            pyautogui.write(args['text'], interval=.01)

        elif action == 'media':

            pyautogui.press(args['key'])

        elif action in {'screen', 'frame'}:

            import base64

            import io

            buffer = io.BytesIO()

            shot = pyautogui.screenshot()
            if action == 'frame':
                from PIL import ImageDraw
                x, y = pyautogui.position()
                ImageDraw.Draw(shot).polygon([(x,y),(x+4,y+18),(x+8,y+12),(x+16,y+11)], fill='white', outline='black')

            shot.thumbnail((1280, 720))

            shot.convert('RGB').save(buffer, format='JPEG', quality=65)

            return {'image': base64.b64encode(buffer.getvalue()).decode(), 'mime': 'image/jpeg'}

        return {'ok': True}

