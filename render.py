# -*- coding: utf-8 -*-
"""
诡牌筑局 - 渲染层
逻辑分辨率 1280x720，整体缩放适配任意窗口 / 手机横屏。
"""
import os
import sys
import math
import pygame

from gamecore import (SUIT_SYMBOL, SUIT_COLOR, RARITY_COLOR, HT, HAND_TYPES,
                      BLIND_CN, FINAL_ANTE)

# ---------------------------------------------------------------- 资源路径

def resource_path(rel):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel)


FONT_CANDIDATES = [
    "fonts/NotoSansSC-Regular.ttf",
    "fonts/NotoSansSC-Bold.ttf",
    "fonts/NotoSansSC-VF.ttf",
    "fonts/Deng.ttf",
    "fonts/msyh.ttc",
    "fonts/simhei.ttf",
]

_fonts_cache = {}
_font_bold_cache = {}


def _load(size, bold=False):
    cache = _font_bold_cache if bold else _fonts_cache
    if size in cache:
        return cache[size]
    if bold:
        order = ["fonts/NotoSansSC-Bold.ttf"] + [p for p in FONT_CANDIDATES if "Bold" not in p]
    else:
        order = ["fonts/NotoSansSC-Regular.ttf"] + [p for p in FONT_CANDIDATES if "Regular" not in p]
    f = None
    for rel in order:
        p = resource_path(rel)
        if os.path.exists(p):
            try:
                f = pygame.font.Font(p, size)
                break
            except Exception:
                continue
    if f is None:
        f = pygame.font.Font(None, size)
    cache[size] = f
    return f


def F(size, bold=False):
    return _load(size, bold)


def txt(surf, s, size, color, x, y, align="left", bold=False, alpha=None, shadow=False):
    f = F(size, bold)
    if alpha is not None and alpha < 255:
        img = f.render(str(s), True, color)
        img.set_alpha(alpha)
    else:
        img = f.render(str(s), True, color)
    r = img.get_rect()
    if align == "center":
        r.midtop = (int(x), int(y))
    elif align == "right":
        r.topright = (int(x), int(y))
    else:
        r.topleft = (int(x), int(y))
    if shadow:
        sh = f.render(str(s), True, (0, 0, 0))
        surf.blit(sh, (r.x + 2, r.y + 2))
    surf.blit(img, r)
    return r


def wrap(s, size, max_w, bold=False):
    """中文按字符换行"""
    f = F(size, bold)
    lines, cur = [], ""
    for ch in str(s):
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        t = cur + ch
        if f.size(t)[0] > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def blit_lines(surf, lines, size, color, x, y, lh=None, align="left", bold=False):
    lh = lh or int(size * 1.35)
    for i, ln in enumerate(lines):
        txt(surf, ln, size, color, x, y + i * lh, align, bold)
    return y + len(lines) * lh


# ---------------------------------------------------------------- 主题

BG_TOP = (58, 26, 46)
BG_BOT = (16, 10, 22)
PANEL = (44, 25, 42)
PANEL2 = (58, 33, 54)
LINE = (96, 62, 92)
GOLD = (245, 197, 66)
GOLD_D = (180, 138, 40)
TEXT = (243, 238, 230)
SUB = (176, 160, 178)
RED = (226, 76, 76)
GREEN = (96, 206, 128)
BLUE = (96, 170, 240)
PURPLE = (186, 112, 226)
DARK = (24, 14, 24)

CARD_W, CARD_H = 96, 136
JOKER_W, JOKER_H = 92, 124
CONSUM_W, CONSUM_H = 76, 104


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def brighten(c, k=1.25):
    return tuple(min(255, int(v * k)) for v in c)


# ---------------------------------------------------------------- 图元

def rrect(surf, rect, color, radius=12, width=0, bcolor=None, shadow=True):
    r = pygame.Rect(rect)
    if shadow and width == 0:
        s = pygame.Surface((r.w + 8, r.h + 8), pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 90), (4, 5, r.w, r.h), border_radius=radius)
        surf.blit(s, (r.x - 4, r.y - 1))
    pygame.draw.rect(surf, color, r, border_radius=radius)
    if width and bcolor:
        pygame.draw.rect(surf, bcolor, r, width, border_radius=radius)
    return r


def vgradient(surf, top, bottom):
    h = surf.get_height()
    w = surf.get_width()
    for i in range(h):
        t = i / max(1, h - 1)
        pygame.draw.line(surf, mix(top, bottom, t), (0, i), (w, i))


_bg_cache = {}


def draw_bg(surf, t=0.0):
    key = surf.get_size()
    if key not in _bg_cache:
        bg = pygame.Surface(key)
        vgradient(bg, BG_TOP, BG_BOT)
        # 放射光晕
        glow = pygame.Surface(key, pygame.SRCALPHA)
        cx, cy = key[0] // 2, int(key[1] * 0.42)
        for i in range(90):
            rr = 12 + i * 9
            a = max(0, 16 - i // 6)
            pygame.draw.circle(glow, (255, 150, 90, a), (cx, cy), rr, 1)
        bg.blit(glow, (0, 0))
        # 织纹
        tex = pygame.Surface(key, pygame.SRCALPHA)
        for y in range(0, key[1], 4):
            pygame.draw.line(tex, (255, 255, 255, 5), (0, y), (key[0], y))
        bg.blit(tex, (0, 0))
        _bg_cache[key] = bg
    surf.blit(_bg_cache[key], (0, 0))
    # 呼吸光斑
    pulse = 0.5 + 0.5 * math.sin(t * 1.2)
    gs = pygame.Surface((420, 420), pygame.SRCALPHA)
    pygame.draw.circle(gs, (255, 120, 80, int(10 + 8 * pulse)),
                       (210, 210), 210)
    surf.blit(gs, (key[0] // 2 - 210, int(key[1] * 0.42) - 210),
              special_flags=pygame.BLEND_RGB_ADD)


def draw_button(surf, rect, label, enabled=True, hover=False, size=22,
                color=None, text_color=None, sub=None, hotkey=None):
    r = pygame.Rect(rect)
    base = color or PANEL2
    if not enabled:
        base = (52, 40, 52)
        tc = (120, 108, 122)
    else:
        tc = text_color or TEXT
        if hover:
            base = brighten(base, 1.35)
    rrect(surf, r, base, radius=10, width=2,
          bcolor=GOLD if (hover and enabled) else LINE)
    cy = r.centery - (7 if sub else 0)
    txt(surf, label, size, tc, r.centerx, cy - size * 0.6, "center", True)
    if sub:
        txt(surf, sub, size - 6, SUB, r.centerx, cy + 8, "center")
    if hotkey:
        hks = max(9, min(12, size - 11))
        # 只在按钮右侧够宽时显示，避免截断
        if hks * len(hotkey) * 0.55 < r.w * 0.34:
            txt(surf, hotkey, hks, GOLD_D, r.right - 7, r.top + 3, "right", True)
    return r


def draw_bar(surf, rect, frac, color, bg=(30, 18, 30), label=""):
    r = pygame.Rect(rect)
    rrect(surf, r, bg, radius=8)
    inner = pygame.Rect(r.x + 2, r.y + 2, max(0, int((r.w - 4) * min(1, max(0, frac)))), r.h - 4)
    if inner.w > 0:
        pygame.draw.rect(surf, color, inner, border_radius=7)
        hl = pygame.Surface((inner.w, max(1, inner.h // 2)), pygame.SRCALPHA)
        hl.fill((255, 255, 255, 34))
        surf.blit(hl, (inner.x, inner.y))
    if label:
        txt(surf, label, 13, TEXT, r.centerx, r.centery - 8, "center", True)


# ---------------------------------------------------------------- 扑克牌

def card_face_color(card):
    if card.enh == "stone":
        return (128, 130, 138), (108, 110, 118)
    if card.enh == "glass":
        return (200, 232, 245), (168, 208, 228)
    if card.enh == "steel":
        return (196, 202, 214), (160, 168, 182)
    if card.enh == "gold":
        return (250, 232, 168), (226, 196, 106)
    return (250, 246, 236), (226, 219, 204)


def draw_card(surf, card, x, y, w=CARD_W, h=CARD_H, selected=False,
              hover=False, dim=False, scale=1.0, angle=0, t=0.0):
    """x,y 为卡牌中心"""
    w, h = int(w * scale), int(h * scale)
    surf_big = pygame.Surface((w + 24, h + 30), pygame.SRCALPHA)
    local = (12, 12)
    r = pygame.Rect(local[0], local[1], w, h)

    c1, c2 = card_face_color(card)
    # 阴影
    pygame.draw.rect(surf_big, (0, 0, 0, 110), (local[0] + 3, local[1] + 6, w, h), border_radius=10)

    # 选中/悬停外发光
    if selected:
        for i in range(3):
            a = 60 - i * 16
            pygame.draw.rect(surf_big, (255, 210, 90, a),
                             (local[0] - 4 - i * 3, local[1] - 4 - i * 3, w + 8 + i * 6, h + 8 + i * 6),
                             border_radius=12 + i * 2)
    elif hover:
        pygame.draw.rect(surf_big, (255, 255, 255, 40),
                         (local[0] - 4, local[1] - 4, w + 8, h + 8), border_radius=12)

    # 卡面渐变
    face = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(h):
        tt = i / max(1, h - 1)
        pygame.draw.line(face, mix(c1, c2, tt), (0, i), (w, i))
    surf_big.blit(face, local)

    # 内边框
    pygame.draw.rect(surf_big, (255, 255, 255, 150), r, 2, border_radius=9)
    pygame.draw.rect(surf_big, (70, 50, 60, 120), r, 1, border_radius=9)

    pad = int(8 * scale)
    # 花色与点数
    if card.enh == "stone":
        txt(surf_big, "\u26f0", int(h * 0.42), (70, 70, 78), local[0] + w // 2,
            local[1] + h // 2 - int(h * 0.26), "center", True)
        txt(surf_big, "石头", int(15 * scale), (70, 70, 78), local[0] + w // 2,
            local[1] + h - int(34 * scale), "center", True)
    else:
        col = SUIT_COLOR[card.suit]
        sym = SUIT_SYMBOL[card.suit]
        rk = card.rank_str
        txt(surf_big, rk, int(30 * scale), col, local[0] + pad, local[1] + pad - 4, "left", True)
        txt(surf_big, sym, int(20 * scale), col, local[0] + pad, local[1] + pad + int(28 * scale), "left", True)
        # 中央大花色
        txt(surf_big, sym, int(h * 0.44), col, local[0] + w // 2, local[1] + h // 2 - int(h * 0.26), "center", True)
        # 右下旋转标记
        small = F(int(18 * scale), True).render(rk + sym, True, col)
        small = pygame.transform.rotate(small, 180)
        surf_big.blit(small, (local[0] + w - pad - small.get_width(),
                              local[1] + h - pad - small.get_height()))
        # 万能牌标志
        if card.enh == "wild":
            txt(surf_big, "\u2727", int(24 * scale), (150, 90, 220),
                local[0] + w // 2, local[1] + h // 2 + int(6 * scale), "center", True)

    # 版本特效
    if card.edition == "foil":
        ov = pygame.Surface((w, h), pygame.SRCALPHA)
        k = int((math.sin(t * 2 + card.uid) * 0.5 + 0.5) * 90)
        ov.fill((140, 160, 200, 40 + k // 4))
        surf_big.blit(ov, local, special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.rect(surf_big, (180, 200, 235), r, 2, border_radius=9)
    elif card.edition == "holo":
        ov = pygame.Surface((w, h), pygame.SRCALPHA)
        ph = (math.sin(t * 2.4 + card.uid) * 0.5 + 0.5)
        for i in range(h):
            v = int(90 * (0.5 + 0.5 * math.sin(i / 14.0 + t * 3 + card.uid)))
            pygame.draw.line(ov, (255, 120, 200, v), (0, i), (w, i))
        surf_big.blit(ov, local, special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.rect(surf_big, (255, 160, 230), r, 2, border_radius=9)
    elif card.edition == "poly":
        ov = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(h):
            v = i / max(1, h - 1)
            pygame.draw.line(ov, (int(255 * (0.4 + 0.6 * v)), int(120 + 100 * (1 - v)),
                                  int(200 + 55 * v), 60), (0, i), (w, i))
        surf_big.blit(ov, local, special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.rect(surf_big, (250, 120, 240), r, 3, border_radius=9)

    # 强化角标
    enh_map = {"bonus": ("\u2795", BLUE), "mult": ("\u2716", RED),
               "glass": ("\u25c7", (120, 210, 240)), "steel": ("\u25a0", (150, 160, 175)),
               "gold": ("\u2605", (240, 200, 90)), "lucky": ("\u2733", (120, 220, 160)),
               "stone": ("\u26f0", (110, 112, 120))}
    if card.enh in enh_map:
        s, cc = enh_map[card.enh]
        rr = pygame.Rect(local[0] + w - int(26 * scale), local[1] + 4, int(22 * scale), int(22 * scale))
        pygame.draw.circle(surf_big, (30, 18, 30, 220), rr.center, int(12 * scale))
        pygame.draw.circle(surf_big, cc, rr.center, int(12 * scale), 2)
        txt(surf_big, s, int(15 * scale), cc, rr.centerx, rr.centery - int(9 * scale), "center", True)

    # 封印
    seal_map = {"red": (226, 76, 76), "blue": (80, 150, 240),
                "purple": (180, 100, 230), "gold": (240, 200, 90)}
    if card.seal in seal_map:
        pygame.draw.circle(surf_big, seal_map[card.seal],
                           (local[0] + int(14 * scale), local[1] + h - int(14 * scale)), int(8 * scale))
        pygame.draw.circle(surf_big, (255, 255, 255, 180),
                           (local[0] + int(12 * scale), local[1] + h - int(16 * scale)), int(3 * scale))

    if dim:
        d = pygame.Surface((w, h), pygame.SRCALPHA)
        d.fill((20, 10, 20, 140))
        surf_big.blit(d, local)

    if angle:
        surf_big = pygame.transform.rotate(surf_big, angle)
    surf.blit(surf_big, (int(x) - surf_big.get_width() // 2, int(y) - surf_big.get_height() // 2))
    return pygame.Rect(int(x) - w // 2, int(y) - h // 2, w, h)


def draw_card_back(surf, x, y, w=60, h=84, t=0.0):
    r = pygame.Rect(int(x - w / 2), int(y - h / 2), w, h)
    rrect(surf, r, (108, 46, 74), radius=8, width=2, bcolor=(180, 90, 120))
    inner = r.inflate(-10, -10)
    pygame.draw.rect(surf, (78, 32, 54), inner, border_radius=6)
    for i in range(0, inner.h, 6):
        pygame.draw.line(surf, (140, 62, 96), (inner.x, inner.y + i),
                         (inner.right, inner.y + i + 4), 1)
    txt(surf, "\u2663", int(h * 0.3), GOLD, r.centerx, r.centery - int(h * 0.18), "center", True)
    return r


# ---------------------------------------------------------------- 小丑牌

def draw_joker_face(surf, cx, cy, r, color, t=0.0, seed=0):
    """程序化小丑头像"""
    # 帽子
    hat = brighten(color, 0.8)
    pts = [(cx - r * 0.95, cy - r * 0.45), (cx + r * 0.95, cy - r * 0.45), (cx, cy - r * 1.65)]
    pygame.draw.polygon(surf, hat, pts)
    pygame.draw.polygon(surf, brighten(hat, 1.2), pts, 2)
    bob = math.sin(t * 2.4 + seed) * r * 0.05
    pygame.draw.circle(surf, GOLD, (int(cx), int(cy - r * 1.72 + bob)), int(r * 0.2))
    pygame.draw.circle(surf, (255, 255, 255, 120), (int(cx - r * 0.06), int(cy - r * 1.78 + bob)), int(r * 0.07))
    # 脸
    pygame.draw.circle(surf, (245, 236, 224), (cx, cy + r * 0.05), r)
    pygame.draw.circle(surf, mix(color, (255, 255, 255), 0.3), (cx, cy + r * 0.05), r, 3)
    # 头发
    for s in (-1, 1):
        pygame.draw.circle(surf, color, (int(cx + s * r * 0.82), int(cy + r * 0.02)), int(r * 0.30))
        pygame.draw.circle(surf, color, (int(cx + s * r * 0.72), int(cy - r * 0.30)), int(r * 0.26))
    # 眼睛
    for s in (-1, 1):
        ex = cx + s * r * 0.32
        ey = cy - r * 0.02
        pygame.draw.ellipse(surf, (255, 255, 255), (ex - r * 0.17, ey - r * 0.22, r * 0.34, r * 0.42))
        pygame.draw.circle(surf, (30, 22, 30), (int(ex), int(ey)), int(r * 0.11))
        pygame.draw.circle(surf, (255, 255, 255), (int(ex + r * 0.05), int(ey - r * 0.05)), int(r * 0.04))
    # 鼻子
    pygame.draw.circle(surf, (226, 76, 76), (int(cx), int(cy + r * 0.24)), int(r * 0.17))
    pygame.draw.circle(surf, (255, 140, 140), (int(cx - r * 0.05), int(cy + r * 0.19)), int(r * 0.05))
    # 笑
    pygame.draw.arc(surf, (180, 50, 60), (cx - r * 0.42, cy + r * 0.24, r * 0.84, r * 0.5),
                    math.pi * 0.15, math.pi * 0.85, max(2, int(r * 0.09)))
    # 领结
    bc = brighten(color, 0.7)
    pygame.draw.polygon(surf, bc, [(cx, cy + r * 0.95), (cx - r * 0.42, cy + r * 0.72),
                                   (cx - r * 0.42, cy + r * 1.18)])
    pygame.draw.polygon(surf, bc, [(cx, cy + r * 0.95), (cx + r * 0.42, cy + r * 0.72),
                                   (cx + r * 0.42, cy + r * 1.18)])
    pygame.draw.circle(surf, GOLD, (int(cx), int(cy + r * 0.95)), int(r * 0.11))


def draw_joker(surf, joker, x, y, w=JOKER_W, h=JOKER_H, hover=False, t=0.0,
               selected=False, dim=False, small=False):
    r = pygame.Rect(int(x - w / 2), int(y - h / 2), w, h)
    if joker is None:
        pygame.draw.rect(surf, (36, 22, 36), r, border_radius=10)
        pygame.draw.rect(surf, (70, 44, 66), r, 2, border_radius=10)
        txt(surf, "+", 26, (90, 64, 86), r.centerx, r.centery - 14, "center", True)
        return r

    col = RARITY_COLOR[joker.rarity]
    body = mix((46, 26, 46), col, 0.14)
    if hover:
        body = brighten(body, 1.4)
    rrect(surf, r, body, radius=10, width=3 if selected else 2,
          bcolor=GOLD if selected else col)

    # 内部底
    inner = pygame.Rect(r.x + 5, r.y + 5, r.w - 10, int(r.h * 0.62))
    g = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
    for i in range(inner.h):
        tt = i / max(1, inner.h - 1)
        pygame.draw.line(g, mix(col, (30, 18, 30), 0.25 + tt * 0.55), (0, i), (inner.w, i))
    surf.blit(g, inner.topleft)

    draw_joker_face(surf, inner.centerx, inner.centery, int(min(inner.w, inner.h) * 0.30),
                    col, t, joker.key.__hash__() % 100 / 10.0)

    # 名称
    nm = joker.name
    sz = 13 if len(nm) <= 5 else 11
    txt(surf, nm, sz, TEXT, r.centerx, r.y + r.h - 30, "center", True)
    # 稀有度点
    for i, rr_ in enumerate(["common", "uncommon", "rare", "legend"]):
        c = GOLD if rr_ == joker.rarity else (70, 50, 70)
        pygame.draw.circle(surf, c, (r.x + 12 + i * 11, r.y + r.h - 9), 3)

    if dim:
        d = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        d.fill((20, 10, 20, 150))
        surf.blit(d, r.topleft)
        txt(surf, "失 效", 14, (230, 90, 90), r.centerx, r.centery - 9, "center", True)
    return r


def draw_joker_card_large(surf, joker, x, y, w=190, h=250, hover=False, t=0.0, price=None):
    """商店/详情用大卡"""
    r = pygame.Rect(int(x - w / 2), int(y - h / 2), w, h)
    col = RARITY_COLOR[joker.rarity]
    body = mix((40, 22, 40), col, 0.16)
    if hover:
        body = brighten(body, 1.35)
    rrect(surf, r, body, radius=14, width=3, bcolor=GOLD if hover else col)

    inner = pygame.Rect(r.x + 10, r.y + 10, r.w - 20, int(r.h * 0.5))
    g = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
    for i in range(inner.h):
        tt = i / max(1, inner.h - 1)
        pygame.draw.line(g, mix(col, (28, 16, 28), 0.2 + tt * 0.6), (0, i), (inner.w, i))
    surf.blit(g, inner.topleft)
    draw_joker_face(surf, inner.centerx, inner.centery, int(min(inner.w, inner.h) * 0.31), col, t, 3)

    yy = inner.bottom + 10
    txt(surf, joker.name, 20, TEXT, r.centerx, yy, "center", True)
    yy += 26
    txt(surf, _rar_cn(joker.rarity), 13, col, r.centerx, yy, "center")
    yy += 22
    lines = wrap(joker.live_desc(), 14, r.w - 24)
    for i, ln in enumerate(lines[:4]):
        txt(surf, ln, 14, (220, 214, 226), r.centerx, yy + i * 19, "center")
    if price is not None:
        pr = pygame.Rect(r.centerx - 34, r.bottom - 40, 68, 30)
        rrect(surf, pr, GOLD_D, radius=15)
        txt(surf, f"${price}", 17, (40, 26, 10), pr.centerx, pr.centery - 10, "center", True)
    return r


def _rar_cn(r):
    return {"common": "普通", "uncommon": "罕见", "rare": "稀有", "legend": "传奇"}[r]


# ---------------------------------------------------------------- 消耗牌

def draw_consumable(surf, c, x, y, w=CONSUM_W, h=CONSUM_H, hover=False, t=0.0,
                    selected=False, price=None):
    r = pygame.Rect(int(x - w / 2), int(y - h / 2), w, h)
    if c is None:
        pygame.draw.rect(surf, (34, 20, 36), r, border_radius=9)
        pygame.draw.rect(surf, (66, 42, 66), r, 2, border_radius=9)
        return r
    base = (56, 34, 96) if c.kind == "tarot" else (26, 56, 96)
    acol = (200, 160, 250) if c.kind == "tarot" else (120, 200, 250)
    if hover:
        base = brighten(base, 1.35)
    rrect(surf, r, base, radius=9, width=3 if selected else 2, bcolor=GOLD if selected else acol)
    ic = pygame.Rect(r.x + 8, r.y + 8, r.w - 16, int(r.h * 0.52))
    pygame.draw.rect(surf, mix(base, (255, 255, 255), 0.14), ic, border_radius=7)
    sym = "\u2726" if c.kind == "tarot" else "\u2643"
    txt(surf, sym, int(ic.h * 0.55), acol, ic.centerx, ic.centery - int(ic.h * 0.32), "center", True)
    txt(surf, c.name, 13 if len(c.name) <= 4 else 11, TEXT, r.centerx, r.y + r.h - 28, "center", True)
    txt(surf, "塔罗" if c.kind == "tarot" else "星球", 10, acol, r.centerx, r.y + r.h - 13, "center")
    if price is not None:
        pr = pygame.Rect(r.centerx - 24, r.bottom - 16, 48, 20)
        rrect(surf, pr, GOLD_D, radius=10)
        txt(surf, f"${price}", 13, (40, 26, 10), pr.centerx, pr.centery - 8, "center", True)
    return r


# ---------------------------------------------------------------- HUD

def draw_hud(surf, game, t):
    # 顶栏
    bar = pygame.Rect(0, 0, 1280, 62)
    g = pygame.Surface((1280, 62), pygame.SRCALPHA)
    for i in range(62):
        tt = i / 61
        pygame.draw.line(g, (28 + int(18 * tt), 14, 30), (0, i), (1280, i))
    surf.blit(g, (0, 0))
    pygame.draw.line(surf, LINE, (0, 62), (1280, 62), 2)

    # 左：关卡 / 盲注
    txt(surf, f"第 {game.ante} / {FINAL_ANTE} 关", 15, SUB, 16, 8)
    kind = game.blind["kind"]
    kc = {"small": (120, 200, 240), "big": (240, 150, 90), "boss": (240, 90, 90)}[kind]
    txt(surf, game.blind["name"], 22, kc, 16, 26, "left", True)
    if game.boss:
        txt(surf, game.boss.name, 14, game.boss.color, 120, 31, "left", True)

    # 中：分数进度
    cx = 640
    frac = min(1.0, game.score / max(1, game.target))
    bw, bh = 380, 20
    bx, by = cx - bw // 2, 14
    rrect(surf, (bx - 3, by - 3, bw + 6, bh + 6), (24, 12, 24), radius=11)
    draw_bar(surf, (bx, by, bw, bh), frac, mix(GREEN, GOLD, frac))
    txt(surf, f"{game.score:,}", 20, TEXT, bx - 10, by - 4, "right", True)
    txt(surf, f"/ {game.target:,}", 16, SUB, bx + bw + 10, by, "left", True)
    txt(surf, "目标分数", 11, SUB, cx, by + bh + 2, "center")

    # 右：金币 / 次数
    rx = 1264
    mc = (250, 235, 245)
    rrect(surf, (rx - 108, 10, 108, 42), (56, 32, 20), radius=10, width=2, bcolor=GOLD_D)
    txt(surf, "\u25cf", 18, GOLD, rx - 92, 22)
    txt(surf, f"{game.money}", 24, GOLD, rx - 12, 18, "right", True)
    txt(surf, "金币", 11, SUB, rx - 12, 40, "right")

    # 出牌 / 弃牌
    x = rx - 130
    for i, (lab, val, col) in enumerate([("出牌", game.hands_left, BLUE),
                                         ("弃牌", game.discards_left, RED)]):
        bx2 = x - i * 108
        rrect(surf, (bx2 - 96, 10, 92, 42), (36, 22, 38), radius=10, width=2, bcolor=mix(col, (0, 0, 0), 0.45))
        txt(surf, lab, 12, SUB, bx2 - 88, 20)
        txt(surf, str(val), 24, col, bx2 - 12, 16, "right", True)

    # Boss 提示条
    if game.boss:
        bw2 = 470
        rrect(surf, (640 - bw2 // 2, 66, bw2, 26), (40, 20, 34), radius=8,
              width=1, bcolor=game.boss.color)
        txt(surf, "首领效果：" + game.boss.desc, 13, game.boss.color, 640, 72, "center", True)


# ---------------------------------------------------------------- 计分显示

def draw_score_display(surf, chips, mult, x, y, t, pulse=0.0, big=False):
    """筹码 × 倍率 大字"""
    w = 300 if not big else 380
    h = 74 if not big else 92
    r = pygame.Rect(x - w // 2, y - h // 2, w, h)
    rrect(surf, r, (26, 14, 26), radius=12, width=2, bcolor=(110, 72, 96))
    sc = 1.0 + pulse * 0.16
    txt(surf, f"{int(chips):,}", int(34 * sc), (110, 190, 240), r.x + 18, y - 22, "left", True, shadow=True)
    txt(surf, "\u00d7", int(26 * sc), SUB, r.centerx + 6, y - 16, "center", True)
    ms = f"{mult:.1f}" if mult != int(mult) else f"{int(mult)}"
    txt(surf, ms, int(34 * sc), (240, 96, 96), r.right - 18, y - 22, "right", True, shadow=True)
    txt(surf, "筹码", 12, (110, 150, 190), r.x + 20, y + 16)
    txt(surf, "倍率", 12, (190, 110, 110), r.right - 20, y + 16, "right")
    return r


def draw_score_popup(surf, x, y, text, color, life):
    """分数飘字"""
    a = int(255 * min(1, life * 2))
    sc = 1.0 + (1 - min(1, life)) * 0.5
    f = F(int(30 * sc), True)
    img = f.render(text, True, color)
    img.set_alpha(a)
    r = img.get_rect(center=(int(x), int(y - (1 - life) * 40)))
    surf.blit(img, r)


# ---------------------------------------------------------------- 粒子

class Particles:
    def __init__(self):
        self.items = []

    def burst(self, x, y, color, n=14, speed=3.0, size=5):
        import random as _r
        for _ in range(n):
            a = _r.uniform(0, math.tau)
            sp = _r.uniform(0.4, 1.0) * speed
            self.items.append({
                "x": x, "y": y,
                "vx": math.cos(a) * sp, "vy": math.sin(a) * sp - 1.2,
                "life": 1.0, "color": color, "size": _r.randint(3, size + 3),
            })

    def update(self, dt):
        for p in self.items:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.16
            p["life"] -= dt * 1.6
        self.items = [p for p in self.items if p["life"] > 0]

    def draw(self, surf):
        for p in self.items:
            a = int(255 * max(0, min(1, p["life"])))
            s = pygame.Surface((p["size"], p["size"]), pygame.SRCALPHA)
            pygame.draw.circle(s, p["color"] + (a,), (p["size"] // 2, p["size"] // 2), p["size"] // 2)
            surf.blit(s, (int(p["x"]), int(p["y"])))


# ---------------------------------------------------------------- 通用面板

def panel(surf, rect, title=None, color=None, alpha=225):
    r = pygame.Rect(rect)
    s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (color or PANEL) + (alpha,), (0, 0, r.w, r.h), border_radius=16)
    pygame.draw.rect(s, LINE + (alpha,), (0, 0, r.w, r.h), 2, border_radius=16)
    surf.blit(s, r.topleft)
    if title:
        txt(surf, title, 20, GOLD, r.centerx, r.y + 14, "center", True)
        pygame.draw.line(surf, LINE, (r.x + 20, r.y + 44), (r.right - 20, r.y + 44), 2)
    return r


def tooltip(surf, lines, x, y, max_w=300):
    size = 14
    wrapped = []
    for ln in lines:
        wrapped += wrap(ln, size, max_w - 24)
    h = len(wrapped) * 20 + 18
    w = max_w
    x = min(max(10, x), 1280 - w - 10)
    y = min(max(10, y), 720 - h - 10)
    panel(surf, (x, y, w, h), alpha=245)
    for i, ln in enumerate(wrapped):
        txt(surf, ln, size, TEXT, x + 12, y + 9 + i * 20)
