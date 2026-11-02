"""Pure-Python physics for Pot Climb (no pygame needed, so it can be tested anywhere)."""
import math

G, BR, HR, L = 1900.0, 24.0, 11.0, 120.0
FIN = -4430.0


class Seg:
    """Capsule terrain piece: segment (a,b)-(c,d) with radius r, grip f, ice flag."""
    def __init__(s, a, b, c, d, r, f=.6, ice=0):
        s.a, s.b, s.c, s.d, s.r, s.f, s.ice, s.img = a, b, c, d, r, f, ice, None


def hit(px, py, r, s):
    vx, vy = s.c - s.a, s.d - s.b
    l = vx * vx + vy * vy
    t = ((px - s.a) * vx + (py - s.b) * vy) / l if l else 0.0
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    dx, dy = px - (s.a + vx * t), py - (s.b + vy * t)
    m, d2 = r + s.r, dx * dx + dy * dy
    if d2 >= m * m:
        return None
    if d2 < 1e-6:
        return 0.0, -1.0, m, s
    d = math.sqrt(d2)
    return dx / d, dy / d, m - d, s


def climb_map():
    P = lambda *a: Seg(*a)
    return [
        P(-520, 60, 520, 60, 40), P(-900, -4700, -900, 60, 40), P(900, -4700, 900, 60, 40),
        P(150, -10, 150, -10, 45), P(260, -150, 420, -190, 30), P(-120, -260, -120, -260, 80),
        P(-330, -120, -330, -120, 50), P(30, -420, 250, -400, 28), P(300, -480, 520, -780, 30, .5),
        P(-100, -700, 160, -720, 26, .03, 1), P(-260, -800, -260, -1100, 34), P(-120, -1180, 120, -1220, 26),
        P(200, -1300, 520, -1340, 16, .7), P(360, -1500, 360, -1500, 60), P(560, -1450, 560, -2000, 40),
        P(300, -2100, 450, -2080, 26), P(-200, -2300, 250, -2200, 26, .03, 1), P(-300, -2450, -300, -2450, 50),
        P(-150, -2600, -150, -2600, 50), P(0, -2720, 0, -2720, 50), P(150, -2850, 420, -2900, 28),
        P(-100, -3100, -420, -3100, 22), P(-500, -3200, -500, -3700, 36), P(-300, -3800, 0, -3790, 28),
        P(60, -3900, 400, -4200, 28), P(200, -4400, 600, -4420, 40),
    ]


def arena_map():
    P = lambda *a: Seg(*a)
    return [P(-560, 0, -170, 0, 30), P(170, 0, 560, 0, 30), P(-110, -170, 110, -170, 20),
            P(-430, -260, -300, -260, 18), P(300, -260, 430, -260, 18), P(0, 90, 0, 90, 40, .6)]


class Player:
    def __init__(s, x, y, name="Player", color=(120, 200, 255)):
        s.name, s.color = name, color
        s.spawn = (x, y)
        s.reset()

    def reset(s):
        x, y = s.spawn
        s.x, s.y, s.vx, s.vy = x, y, 0.0, 0.0
        s.hx, s.hy, s.ax, s.ay = x + 80, y - 40, 80.0, -40.0
        s.hpx, s.hpy, s.hvx, s.hvy = s.hx, s.hy, 0.0, 0.0
        s.hc, s.cool, s.best, s.score = False, 0.0, 0.0, 0

    def aim_world(s, wx, wy):
        s.ax, s.ay = wx - s.x, wy - s.y
        s.clamp()

    def aim_polar(s, ang, ln):
        s.ax, s.ay = math.cos(ang) * ln, math.sin(ang) * ln
        s.clamp()

    def clamp(s):
        l = math.hypot(s.ax, s.ay)
        if l < 1:
            s.ax, s.ay = 40.0, 0.0
        elif l > L:
            s.ax, s.ay = s.ax * L / l, s.ay * L / l
        elif l < 40:
            s.ax, s.ay = s.ax * 40 / l, s.ay * 40 / l

    def step(s, dt, T):
        ev = []
        s.cool = max(0.0, s.cool - dt)
        s.hpx, s.hpy = s.hx, s.hy
        s.vy += G * dt
        s.vx *= 1 - .15 * dt
        s.x += s.vx * dt
        s.y += s.vy * dt
        for _ in range(2):
            for sg in T:
                c = hit(s.x, s.y, BR, sg)
                if not c:
                    continue
                nx, ny, pen, _s = c
                s.x += nx * pen
                s.y += ny * pen
                vn = s.vx * nx + s.vy * ny
                if vn < 0:
                    if vn < -600:
                        ev.append(("land", -vn))
                    s.vx -= 1.12 * vn * nx
                    s.vy -= 1.12 * vn * ny
                fr = max(0.0, 1 - sg.f * 9 * dt)
                tx, ty = -ny, nx
                vt = (s.vx * tx + s.vy * ty) * fr
                vn = s.vx * nx + s.vy * ny
                s.vx, s.vy = nx * vn + tx * vt, ny * vn + ty * vt
        tx2, ty2 = s.x + s.ax, s.y + s.ay
        dx, dy = tx2 - s.hx, ty2 - s.hy
        d = math.hypot(dx, dy)
        mv = min(d, 3200 * dt)
        if d > 0:
            s.hx += dx / d * mv
            s.hy += dy / d * mv
        cn = None
        for _ in range(2):
            for sg in T:
                c = hit(s.hx, s.hy, HR, sg)
                if c:
                    s.hx += c[0] * c[2]
                    s.hy += c[1] * c[2]
                    cn = c
        if cn and not s.hc:
            ev.append(("tap", min(1.0, mv / (3200 * dt))))
        s.hc = cn is not None
        if cn:
            ex, ey = tx2 - s.hx, ty2 - s.hy
            en = ex * cn[0] + ey * cn[1]
            if en < 0:
                px, py, g = en * cn[0], en * cn[1], cn[3].f
                px += (ex - px) * g
                py += (ey - py) * g
                mx, my = -px * .35, -py * .35
                s.x += mx
                s.y += my
                s.vx += (mx / dt - s.vx) * .15
                s.vy += (my / dt - s.vy) * .15
        hx, hy = s.hx - s.x, s.hy - s.y
        hd = math.hypot(hx, hy)
        if hd > L * 1.25:
            s.hx, s.hy = s.x + hx / hd * L * 1.25, s.y + hy / hd * L * 1.25
        s.hvx, s.hvy = (s.hx - s.hpx) / dt, (s.hy - s.hpy) / dt
        s.best = max(s.best, -s.y / 40)
        return ev


def strike(a, b):
    """Fighting: a's hammer head hits b's pot. Returns True on a hit."""
    if a.cool > 0 or math.hypot(a.hvx, a.hvy) < 500:
        return False
    if math.hypot(a.hx - b.x, a.hy - b.y) < HR + BR + 4:
        b.vx += a.hvx * .55
        b.vy += a.hvy * .55 - 200
        a.cool = .35
        return True
    return False
