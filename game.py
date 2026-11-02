"""Pot Climb - Python/Pygame edition.
Modes: Climb Solo, Climb Online (room code), Fight vs Bot, Fight 2 Players (local).
Run:  pip install pygame   then   python game.py
"""
import array, json, math, os, random, socket, sys, threading, time
import pygame
from physics import *

W, H = 1280, 720
S = H / 560.0                       # world -> screen scale
DT = 1 / 120.0


# ------------------------------------------------------------------ sound
class Snd:
    def __init__(s):
        s.ok = False
        try:
            pygame.mixer.init(22050, -16, 1, 512)
            s.tap = s.mk(110, .12, .45, 14)
            s.land = s.mk(55, .25, .7, 8)
            s.win = s.mk(660, .5, .4, 4)
            s.hit = s.mk(200, .2, .7, 10)
            s.ok = True
        except Exception:
            pass

    @staticmethod
    def mk(f, d, v, dec):
        n = int(22050 * d)
        b = array.array("h", [int(32767 * v * math.sin(6.2832 * f * i / 22050) * math.exp(-dec * i / n)) for i in range(n)])
        return pygame.mixer.Sound(buffer=b.tobytes())

    def play(s, name, vol=1.0):
        if s.ok:
            snd = getattr(s, name)
            snd.set_volume(max(0.05, min(1.0, vol)))
            snd.play()


# ------------------------------------------------------------------ network
class Net:
    def __init__(s, host, port, code, name):
        s.args = (host, port, code, name)
        s.others, s.ok, s.retry = {}, False, 0
        s.connect()

    def connect(s):
        try:
            host, port, code, name = s.args
            s.sock = socket.create_connection((host, port), timeout=4)
            s.sock.settimeout(None)
            s.sock.sendall((json.dumps({"t": "join", "code": code}) + "\n").encode())
            s.ok = True
            threading.Thread(target=s.loop, daemon=True).start()
        except Exception:
            s.ok = False

    def loop(s):
        try:
            for line in s.sock.makefile("r"):
                m = json.loads(line)
                if m.get("t") == "s":
                    m["seen"] = time.time()
                    s.others[m["id"]] = m
                elif m.get("t") == "l":
                    s.others.pop(m["id"], None)
        except Exception:
            pass
        s.ok = False

    def send(s, p):
        if not s.ok:
            if time.time() > s.retry:          # auto-reconnect every 3 s
                s.retry = time.time() + 3
                s.connect()
            return
        try:
            m = {"t": "s", "n": p.name, "x": int(p.x), "y": int(p.y), "hx": int(p.hx), "hy": int(p.hy), "m": int(p.best)}
            s.sock.sendall((json.dumps(m) + "\n").encode())
        except Exception:
            s.ok = False

    def close(s):
        try:
            s.sock.close()
        except Exception:
            pass


# ------------------------------------------------------------------ graphics
def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def bake(seg, seed):
    rng = random.Random(seed)
    pad = 16
    x0, y0 = min(seg.a, seg.c) - seg.r - pad, min(seg.b, seg.d) - seg.r - pad
    w, h = abs(seg.c - seg.a) + 2 * seg.r + 2 * pad, abs(seg.d - seg.b) + 2 * seg.r + 2 * pad
    th = math.atan2(seg.d - seg.b, seg.c - seg.a)
    pts = []

    def ring(cx, cy, a0, a1):
        for i in range(13):
            an = a0 + (a1 - a0) * i / 12
            rr = seg.r * (1 + (rng.random() - .5) * .2)
            pts.append((cx + math.cos(an) * rr - x0, cy + math.sin(an) * rr - y0))

    def side(ax, ay, bx, by, an):
        k = int(math.hypot(bx - ax, by - ay) / 40)
        for i in range(1, k + 1):
            t, rr = i / (k + 1), seg.r * (1 + (rng.random() - .5) * .2)
            pts.append((ax + (bx - ax) * t + math.cos(an) * rr - x0, ay + (by - ay) * t + math.sin(an) * rr - y0))

    ring(seg.a, seg.b, th + math.pi / 2, th + math.pi * 1.5)
    side(seg.a, seg.b, seg.c, seg.d, th - math.pi / 2)
    ring(seg.c, seg.d, th - math.pi / 2, th + math.pi / 2)
    side(seg.c, seg.d, seg.a, seg.b, th + math.pi / 2)
    sw, sh = max(2, int(w * S)), max(2, int(h * S))
    sp = [(px * S, py * S) for px, py in pts]
    tex = pygame.Surface((sw, sh), pygame.SRCALPHA)
    c0, c1 = ((228, 246, 252), (111, 166, 192)) if seg.ice else ((168, 154, 134), (77, 67, 56))
    for yy in range(sh):
        pygame.draw.line(tex, lerp(c0, c1, yy / sh), (0, yy), (sw, yy))
    for _ in range(int(w * h / 260)):
        v = rng.randint(0, 40) if rng.random() < .5 else rng.randint(200, 255)
        c = (v, v, v)
        pygame.draw.circle(tex, lerp(lerp(c0, c1, rng.random()), c, .12), (rng.randint(0, sw), rng.randint(0, sh)), rng.randint(1, 4))
    for _ in range(max(2, int(w * h / 9000))):
        cx, cy, pl = rng.random() * sw, rng.random() * sh, []
        for _ in range(5):
            pl.append((cx, cy))
            cx += (rng.random() - .5) * 30
            cy += rng.random() * 22
        pygame.draw.lines(tex, (52, 42, 32), False, pl, 2)
    mask = pygame.Surface((sw, sh), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), sp)
    tex.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    pygame.draw.polygon(tex, (16, 12, 8), sp, 3)
    pygame.draw.lines(tex, (235, 225, 205) if not seg.ice else (255, 255, 255), False, [(a - 3, b - 3) for a, b in sp[: len(sp) // 3]], 2)
    return tex, (x0, y0)


class Cam:
    def __init__(s):
        s.x, s.y = 0.0, -60.0

    def sx(s, x):
        return (x - s.x) * S + W / 2

    def sy(s, y):
        return (y - s.y) * S + H / 2

    def world(s, mx, my):
        return (mx - W / 2) / S + s.x, (my - H / 2) / S + s.y


def sky(al):
    surf = pygame.Surface((1, H))
    top, bot = lerp((150, 172, 190), (60, 70, 105), al), lerp((214, 218, 206), (150, 130, 130), al)
    for y in range(H):
        surf.set_at((0, y), lerp(top, bot, y / H))
    return pygame.transform.scale(surf, (W, H))


SKY = None


def draw_bg(scr, cam, al):
    global SKY
    if SKY is None:
        SKY = [sky(i / 7) for i in range(8)]
    scr.blit(SKY[min(7, max(0, int(al * 7 + .5)))], (0, 0))
    for m in range(6):
        cx = ((m * 290 - cam.x * .08) % 1740) - 150
        cy = H * (.12 + (m % 3) * .1) - cam.y * S * .01
        pygame.draw.ellipse(scr, (232, 236, 238), (cx * 1, cy, 220 * S, 40 * S))
    layers = [(.08, 1.3, (126, 146, 166), 0), (.18, 1.0, (88, 112, 104), 0), (.32, .8, (48, 74, 54), 1)]
    for li, (p, r, c, tr) in enumerate(layers):
        base = H * (.5 + .1 * li) - cam.y * S * .05 * p * 8
        pts = [(0, H)]
        for sx in range(0, W + 20, 16):
            wx = sx / S + cam.x * p
            pts.append((sx, base - (math.sin(wx * .005 + li * 2.3) * 55 + math.sin(wx * .013 + li) * 22 + 70) * S * r))
        pts.append((W, H))
        pygame.draw.polygon(scr, c, pts)
        if tr:
            for sx, y in pts[1:-1:1]:
                if int(sx / 16) % 3:
                    pygame.draw.polygon(scr, (28, 50, 34), [(sx - 7 * S, y + 4), (sx, y - 28 * S), (sx + 7 * S, y + 4)])


def rot(px, py, a, pts):
    ca, sa = math.cos(a), math.sin(a)
    return [(px + x * ca - y * sa, py + x * sa + y * ca) for x, y in pts]


def draw_player(scr, cam, p, font, tint=None):
    px, py, hx, hy = cam.sx(p.x), cam.sy(p.y), cam.sx(p.hx), cam.sy(p.hy)
    a = math.atan2(hy - py, hx - px)
    d = max(1.0, math.hypot(hx - px, hy - py))
    pygame.draw.line(scr, (58, 63, 71), (px, py - 12 * S), (hx, hy), int(7 * S))
    pygame.draw.line(scr, (174, 181, 191), (px, py - 13 * S), (hx, hy - S), int(3 * S))
    k = S
    pygame.draw.polygon(scr, (46, 50, 56), rot(hx, hy, a, [(-2 * k, -20 * k), (18 * k, -20 * k), (18 * k, 20 * k), (-2 * k, 20 * k)]))
    pygame.draw.polygon(scr, (143, 151, 163), rot(hx, hy, a, [(-2 * k, -20 * k), (18 * k, -20 * k), (18 * k, -9 * k), (-2 * k, -9 * k)]))
    pygame.draw.polygon(scr, (90, 97, 107), rot(hx, hy, a, [(16 * k, -8 * k), (38 * k, -2 * k), (16 * k, -2 * k)]))
    skin = (222, 170, 128)
    pygame.draw.ellipse(scr, skin, (px - 13 * k, py - 29 * k, 26 * k, 34 * k))
    pygame.draw.line(scr, (201, 154, 108), (px + 7 * k, py - 20 * k), (px + (hx - px) / d * 26 * k, py - 18 * k + (hy - py) / d * 26 * k), int(7 * k))
    pygame.draw.circle(scr, skin, (px, py - 34 * k), int(9 * k))
    pygame.draw.circle(scr, (42, 28, 16), (px + 3 * k, py - 35 * k), max(1, int(1.6 * k)))
    pts = [(px + BR * k * math.cos(t / 12 * math.pi), py + BR * k * math.sin(t / 12 * math.pi)) for t in range(13)]
    pygame.draw.polygon(scr, (68, 74, 83), pts)
    pygame.draw.polygon(scr, (20, 24, 29), pts, max(2, int(3 * k)))
    pygame.draw.ellipse(scr, (155, 162, 172), (px - (BR + 3) * k, py - 10 * k, (BR + 3) * 2 * k, 10 * k))
    pygame.draw.ellipse(scr, (37, 42, 49), (px - (BR - 3) * k, py - 8 * k, (BR - 3) * 2 * k, 5 * k))
    pygame.draw.ellipse(scr, (130, 138, 148), (px - 14 * k, py + 2 * k, 8 * k, 14 * k))
    col = tint or p.color
    t = font.render(p.name, True, col)
    scr.blit(font.render(p.name, True, (0, 0, 0)), (px - t.get_width() / 2 + 1, py - 62 * k + 1))
    scr.blit(t, (px - t.get_width() / 2, py - 62 * k))


class Fx:
    def __init__(s):
        s.p, s.shake = [], 0.0

    def dust(s, x, y, n):
        for _ in range(n):
            s.p.append([x, y, random.uniform(-80, 80), random.uniform(-120, 0), 1.0])

    def update(s, dt):
        s.shake *= .9
        for q in s.p:
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            q[3] += 400 * dt
            q[4] -= dt * 2
        s.p = [q for q in s.p if q[4] > 0]

    def draw(s, scr, cam):
        for q in s.p:
            c = lerp((60, 55, 50), (205, 190, 165), q[4])
            pygame.draw.circle(scr, c, (cam.sx(q[0]), cam.sy(q[1])), max(1, int((2 + q[4] * 3) * S)))


def draw_terrain(scr, cam, T):
    for i, sg in enumerate(T):
        if sg.img is None:
            sg.img = bake(sg, i + 1)
        tex, (x0, y0) = sg.img
        sx, sy = cam.sx(x0), cam.sy(y0)
        if sx > W or sy > H or sx + tex.get_width() < 0 or sy + tex.get_height() < 0:
            continue
        scr.blit(tex, (sx, sy))


# ------------------------------------------------------------------ helpers
def events_fx(p, ev, fx, snd):
    for k, v in ev:
        if k == "tap":
            fx.dust(p.hx, p.hy, 3 + int(v * 6))
            snd.play("tap", .2 + v)
        elif k == "land":
            fx.shake = max(fx.shake, min(1, v / 1400) * 8)
            fx.dust(p.x, p.y + BR, 8)
            snd.play("land", min(1, v / 1400) + .2)


def prompt(scr, clock, font, title, default=""):
    text = default
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN:
                    return text
                if e.key == pygame.K_ESCAPE:
                    return None
                if e.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                elif e.unicode.isprintable() and len(text) < 24:
                    text += e.unicode
        scr.fill((26, 20, 15))
        scr.blit(font.render(title, True, (243, 236, 224)), (W / 2 - 300, H / 2 - 60))
        scr.blit(font.render(text + "|", True, (255, 207, 138)), (W / 2 - 300, H / 2))
        scr.blit(font.render("Enter = OK    Esc = back", True, (150, 140, 125)), (W / 2 - 300, H / 2 + 60))
        pygame.display.flip()
        clock.tick(30)


def text_c(scr, font, s, y, col=(243, 236, 224)):
    t = font.render(s, True, col)
    scr.blit(t, (W / 2 - t.get_width() / 2, y))


# ------------------------------------------------------------------ modes
def climb(scr, clock, fonts, snd, net=None, code="", name="Player", frames=None):
    f, fb = fonts
    T, fx, cam = climb_map(), Fx(), Cam()
    me = Player(0, -10, name, (255, 220, 120))
    acc, tm, falls, peak, paused, done = 0.0, 0.0, 0, 0.0, False, 0.0
    n = 0
    while True:
        n += 1
        if frames and n > frames:
            return
        dt = min(.05, clock.tick(60) / 1000.0)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return
                if e.key == pygame.K_p:
                    paused = not paused
                if e.key == pygame.K_r:
                    me.reset()
        if not paused:
            tm += dt
            mx, my = pygame.mouse.get_pos()
            wx, wy = cam.world(mx, my)
            me.aim_world(wx, wy)
            acc += dt
            k = 0
            while acc >= DT and k < 6:
                events_fx(me, me.step(DT, T), fx, snd)
                acc -= DT
                k += 1
            if k >= 6:
                acc = 0
            if me.y > 200:
                me.x, me.y, me.vx, me.vy = 0, -10, 0, 0
            ht = max(0, -me.y / 40)
            if ht < peak - 10:
                falls += 1
                peak = ht
            peak = max(peak, ht)
            if me.y < FIN and not done:
                done = tm
                snd.play("win")
            fx.update(dt)
            if net:
                net.send(me)
        cam.x += (me.x - cam.x) * min(1, 6 * dt)
        cam.y += (me.y - 60 - cam.y) * min(1, 6 * dt)
        sx, sy = cam.x, cam.y
        cam.x += random.uniform(-1, 1) * fx.shake / S
        cam.y += random.uniform(-1, 1) * fx.shake / S
        draw_bg(scr, cam, min(1, max(0, -cam.y / 4400)))
        draw_terrain(scr, cam, T)
        pygame.draw.line(scr, (255, 210, 74), (cam.sx(380), cam.sy(FIN)), (cam.sx(380), cam.sy(FIN - 110)), 6)
        pygame.draw.rect(scr, (224, 75, 58), (cam.sx(380), cam.sy(FIN - 110), 60 * S, 36 * S))
        board = [(name + " (you)", me.best)]
        if net:
            now = time.time()
            for oid, o in list(net.others.items()):
                if now - o["seen"] > 6:
                    net.others.pop(oid, None)
                    continue
                g = Player(o["x"], o["y"], o.get("n", "?"), (150, 220, 255))
                g.x, g.y, g.hx, g.hy = o["x"], o["y"], o["hx"], o["hy"]
                draw_player(scr, cam, g, f, (150, 220, 255))
                board.append((g.name, o["m"]))
        draw_player(scr, cam, me, f)
        fx.draw(scr, cam)
        cam.x, cam.y = sx, sy
        scr.blit(fb.render("%d m   %d:%02d   falls %d   best %d m" % (max(0, -me.y / 40), tm // 60, tm % 60, falls, me.best), True, (255, 255, 255)), (16, 12))
        if net:
            st = "ONLINE" if net.ok else "RECONNECTING..."
            scr.blit(f.render("Room %s  %s" % (code, st), True, (140, 255, 160) if net.ok else (255, 180, 90)), (16, 44))
            board.sort(key=lambda r: -r[1])
            for i, (nm, m) in enumerate(board[:6]):
                scr.blit(f.render("%d. %s  %d m" % (i + 1, nm, m), True, (255, 255, 255)), (W - 240, 12 + i * 22))
        if done:
            text_c(scr, fb, "You reached the top!  %d:%02d  %d falls" % (done // 60, done % 60, falls), H * .35, (255, 220, 120))
        if paused:
            text_c(scr, fb, "PAUSED  (P)", H * .4)
        scr.blit(f.render("Mouse = hammer   P pause   R restart   Esc menu", True, (230, 230, 230)), (16, H - 28))
        pygame.display.flip()


def fight(scr, clock, fonts, snd, two_p=False, name="Player", frames=None):
    f, fb = fonts
    T, fx, cam = arena_map(), Fx(), Cam()
    a = Player(-350, -60, name, (255, 220, 120))
    b = Player(350, -60, "Player 2" if two_p else "Bot", (255, 130, 130))
    ang2, len2, acc, t, over, n = math.pi, 100.0, 0.0, 0.0, None, 0
    LAVA = 320
    while True:
        n += 1
        if frames and n > frames:
            return
        dt = min(.05, clock.tick(60) / 1000.0)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return
        if over:
            pass
        else:
            t += dt
            cam.x, cam.y = 0, -100
            mx, my = pygame.mouse.get_pos()
            a.aim_world(*cam.world(mx, my))
            if two_p:
                k = pygame.key.get_pressed()
                ang2 += (k[pygame.K_RIGHT] - k[pygame.K_LEFT]) * 4 * dt
                len2 = max(40, min(L, len2 + (k[pygame.K_DOWN] - k[pygame.K_UP]) * 120 * dt))
                b.aim_polar(ang2, len2)
            else:   # simple bot: sweeps the hammer at the player
                dx, dy = a.x - b.x, a.y - b.y
                sw = math.sin(t * 7) * (1.0 if math.hypot(dx, dy) < 320 else .3)
                ca, sa = math.cos(sw), math.sin(sw)
                b.aim_world(b.x + dx * ca - dy * sa, b.y + dx * sa + dy * ca)
            acc += dt
            k2 = 0
            while acc >= DT and k2 < 6:
                for p in (a, b):
                    events_fx(p, p.step(DT, T), fx, snd)
                if strike(a, b):
                    snd.play("hit")
                    fx.shake = 8
                    fx.dust(b.x, b.y, 10)
                if strike(b, a):
                    snd.play("hit")
                    fx.shake = 8
                    fx.dust(a.x, a.y, 10)
                acc -= DT
                k2 += 1
            if k2 >= 6:
                acc = 0
            for me, other in ((a, b), (b, a)):
                if me.y > LAVA or abs(me.x) > 900:
                    other.score += 1
                    me.reset()
                    me.hx, me.hy = me.x + 80, me.y - 40
                    snd.play("land")
                    if other.score >= 5:
                        over = other.name
                        snd.play("win")
            fx.update(dt)
        draw_bg(scr, cam, .1)
        px = int(cam.sy(LAVA))
        pygame.draw.rect(scr, (210, 70, 20), (0, px, W, H - px))
        for i in range(0, W, 40):
            pygame.draw.circle(scr, (255, 150, 40), (i + int(math.sin(time.time() * 3 + i) * 10), px), 18)
        draw_terrain(scr, cam, T)
        draw_player(scr, cam, a, f)
        draw_player(scr, cam, b, f)
        fx.draw(scr, cam)
        text_c(scr, fb, "%s %d  -  %d %s" % (a.name, a.score, b.score, b.name), 12)
        if over:
            text_c(scr, fb, "%s wins!  (Esc = menu)" % over, H * .4, (255, 220, 120))
        helps = "P1: mouse   P2: arrow keys" if two_p else "Mouse = hammer. Knock the bot into the lava! First to 5."
        scr.blit(f.render(helps, True, (235, 235, 235)), (16, H - 28))
        pygame.display.flip()


def menu(scr, clock, fonts, snd):
    f, fb = fonts
    big = pygame.font.SysFont(None, 96)
    name = "Player%d" % random.randint(10, 99)
    items = ["Climb - Solo", "Climb - Online Room", "Fight vs Bot", "Fight - 2 Players (local)", "Change Name", "Quit"]
    sel = 0
    while True:
        clock.tick(30)
        rects = [pygame.Rect(W / 2 - 230, 250 + i * 62, 460, 50) for i in range(len(items))]
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return
            if e.type == pygame.MOUSEMOTION:
                for i, r in enumerate(rects):
                    if r.collidepoint(e.pos):
                        sel = i
            go = e.type == pygame.MOUSEBUTTONDOWN and rects[sel].collidepoint(e.pos)
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_DOWN:
                    sel = (sel + 1) % len(items)
                if e.key == pygame.K_UP:
                    sel = (sel - 1) % len(items)
                go = e.key == pygame.K_RETURN
            if not go:
                continue
            if sel == 0:
                climb(scr, clock, fonts, snd, name=name)
            elif sel == 1:
                hp = prompt(scr, clock, f, "Server  host:port", "127.0.0.1:8765")
                if hp is None:
                    continue
                code = prompt(scr, clock, f, "Room code (empty = create new)", "")
                if code is None:
                    continue
                code = code.strip() or str(random.randint(100000, 999999))
                host, _, port = hp.partition(":")
                net = Net(host or "127.0.0.1", int(port or 8765), code, name)
                climb(scr, clock, fonts, snd, net=net, code=code, name=name)
                net.close()
            elif sel == 2:
                fight(scr, clock, fonts, snd, False, name)
            elif sel == 3:
                fight(scr, clock, fonts, snd, True, name)
            elif sel == 4:
                nn = prompt(scr, clock, f, "Your name", name)
                name = (nn or name)[:12]
            else:
                return
        draw_bg(scr, Cam(), .0)
        t = big.render("POT CLIMB", True, (30, 22, 14))
        scr.blit(t, (W / 2 - t.get_width() / 2 + 4, 104))
        text_c(scr, big, "POT CLIMB", 100, (243, 236, 224))
        text_c(scr, f, "Name: " + name, 200, (255, 207, 138))
        for i, r in enumerate(rects):
            pygame.draw.rect(scr, (217, 138, 43) if i == sel else (45, 36, 27), r, border_radius=12)
            tt = fb.render(items[i], True, (27, 18, 8) if i == sel else (243, 236, 224))
            scr.blit(tt, (r.centerx - tt.get_width() / 2, r.y + 12))
        pygame.display.flip()


def main():
    pygame.init()
    scr = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Pot Climb")
    clock = pygame.time.Clock()
    fonts = (pygame.font.SysFont(None, 26), pygame.font.SysFont(None, 38))
    snd = Snd()
    if "--selftest" in sys.argv:                  # quick automated smoke test
        climb(scr, clock, fonts, snd, frames=120)
        fight(scr, clock, fonts, snd, False, frames=120)
        fight(scr, clock, fonts, snd, True, frames=120)
        print("selftest ok")
        return
    menu(scr, clock, fonts, snd)
    pygame.quit()


if __name__ == "__main__":
    main()
