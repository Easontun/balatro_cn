# -*- coding: utf-8 -*-
"""
诡牌筑局 —— 类《小丑牌》的 Roguelike 牌组构筑游戏
入口 / 主循环 / 界面状态机
"""
import os
import sys
import math
import random
import pygame

from gamecore import (Game, Card, HT, HAND_TYPES, HT_ORDER, RARITY, FINAL_ANTE)
import render as R
from render import (txt, wrap, rrect, draw_bar, draw_bg, draw_card,
                    draw_joker, draw_joker_card_large, draw_consumable,
                    draw_hud, draw_score_display, draw_button, panel, tooltip,
                    CARD_W, CARD_H, JOKER_W, JOKER_H, CONSUM_W, CONSUM_H,
                    GOLD, GOLD_D, TEXT, SUB, PANEL, PANEL2, LINE, RED, GREEN,
                    BLUE, PURPLE, DARK, Particles, mix, brighten)

W, H = 1280, 720

HAND_Y = 580
PLAY_Y = 452
JOKER_Y = 130
SCORE_Y = 240
CONSUM_X = 66
RIGHT_X = 1214

TITLE = "诡牌筑局"
SUBTITLE = "JOKER'S  GAMBIT"

RAR_CN = {"common": "普通", "uncommon": "罕见", "rare": "稀有", "legend": "传奇"}
SUIT_CN = {"S": "黑桃", "H": "红心", "D": "方块", "C": "梅花"}

ENH_DESC = {
    "bonus": "加成牌：+30 筹码", "mult": "倍率牌：+4 倍率",
    "wild": "万能牌：可作任意花色", "glass": "玻璃牌：x2 倍率，1/4 概率碎裂",
    "steel": "钢铁牌：留在手中时 x1.5 倍率", "stone": "石头牌：无点数，+50 筹码",
    "gold": "黄金牌：回合结束留在手上 +3 金币",
    "lucky": "幸运牌：1/5 +20 倍率，1/15 +20 金币",
}
EDIT_DESC = {"foil": "闪箔：+50 筹码", "holo": "全息：+10 倍率", "poly": "多彩：x1.5 倍率"}
SEAL_DESC = {"red": "红色封印：触发两次", "blue": "蓝色封印：留在手上生成星球牌",
             "purple": "紫色封印：弃掉时生成塔罗牌", "gold": "金色封印：留在手上 +3 金币"}


# ---------------------------------------------------------------- 应用

class App:
    def __init__(self):
        # Android：不让触摸再合成一次鼠标事件（否则点击会触发两遍）
        if os.environ.get("ANDROID_ARGUMENT") or os.path.exists("/system/bin/app_process"):
            os.environ.setdefault("SDL_MOUSE_TOUCH_EVENTS", "0")
            os.environ.setdefault("SDL_ANDROID_TRAP_BACK_BUTTON", "1")
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass
        # 高 DPI 感知（修复 125%/150% 缩放屏上鼠标错位）
        if sys.platform.startswith("win"):
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    import ctypes
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass

        self.android = bool(os.environ.get("ANDROID_ARGUMENT")) or \
            os.path.exists("/system/bin/app_process")
        flags = (pygame.FULLSCREEN | pygame.SCALED) if self.android else (pygame.RESIZABLE | pygame.DOUBLEBUF)
        self.screen = pygame.display.set_mode((W, H), flags)
        pygame.display.set_caption(TITLE)
        try:
            icon = pygame.Surface((64, 64), pygame.SRCALPHA)
            R.draw_joker_face(icon, 32, 30, 22, (186, 112, 226), 0, 1)
            pygame.display.set_icon(icon)
        except Exception:
            pass

        self.canvas = pygame.Surface((W, H)).convert()
        self._scaled_surf = None
        self.scale = 1.0
        self.off = (0, 0)
        self._resize(self.screen.get_size())

        self.clock = pygame.time.Clock()
        self.t = 0.0
        self.game = None
        self.phase = "title"
        self.prev_phase = "title"
        self.buttons = []
        self._btn_id = 0
        self.last_id = -1
        self.hover_id = -1
        self.hover_action = None
        self.mouse_logic = (0, 0)
        self.tooltip_data = None
        self.particles = Particles()
        self.fps = 60

        self.sel_anim = {}
        self.score_anim = None
        self.display_score = 0
        self.popups = []
        self.using_consumable = None
        self.consum_targets = []
        self.hand_flash = 0.0
        self.msg = ""
        self.msg_life = 0.0

        self.last_reward = None
        self.confirm_sell = None
        self.deck_scroll = 0
        self.win_time = 0.0

        rr = random.Random(7)
        self.floaters = []
        for i in range(14):
            c = Card(rr.randint(2, 14), rr.choice(["S", "H", "D", "C"]))
            self.floaters.append({
                "card": c, "x": rr.uniform(0, W), "y": rr.uniform(-H, H),
                "sp": rr.uniform(18, 46), "rot": rr.uniform(-16, 16),
                "vr": rr.uniform(-14, 14), "sc": rr.uniform(0.45, 0.85),
            })
        self.new_run()

    # ---------- 缩放 ----------
    def _resize(self, size):
        sw, sh = max(320, size[0]), max(240, size[1])
        s = min(sw / W, sh / H)
        self.scale = s
        self.scaled_size = (max(1, int(W * s)), max(1, int(H * s)))
        self.off = ((sw - self.scaled_size[0]) // 2, (sh - self.scaled_size[1]) // 2)
        if self._scaled_surf is None or self._scaled_surf.get_size() != self.scaled_size:
            self._scaled_surf = pygame.Surface(self.scaled_size).convert()

    def to_logic(self, pos):
        return ((pos[0] - self.off[0]) / self.scale, (pos[1] - self.off[1]) / self.scale)

    # ---------- 按钮注册 ----------
    def reserve(self, rect, action, data=None, tip=None, tipw=300):
        self._btn_id += 1
        b = {"id": self._btn_id, "rect": pygame.Rect(rect), "action": action,
             "data": data, "tip": tip, "tipw": tipw}
        self.buttons.append(b)
        return b["id"]

    def add(self, rect, action, data=None, tip=None, tipw=300):
        bid = self.reserve(rect, action, data, tip, tipw)
        self.last_id = bid
        return bid

    def hov(self, bid=None):
        return self.hover_id == (self.last_id if bid is None else bid)

    def say(self, s):
        self.msg = s
        self.msg_life = 2.2

    # ---------- 运行 ----------
    def new_run(self, seed=None):
        self.game = Game(seed)
        self.display_score = 0
        self.score_anim = None
        self.popups = []
        self.using_consumable = None
        self.consum_targets = []
        self.last_reward = None
        self.confirm_sell = None
        self.sel_anim = {}
        self.msg = ""
        self.phase = "blind_select"

    def run(self):
        while True:
            dt = min(0.05, self.clock.tick(self.fps) / 1000.0)
            self.t += dt
            if not self.handle_events():
                break
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit(0)

    # ---------- 事件 ----------
    def _update_hover(self):
        self.hover_id = -1
        self.hover_action = None
        sw, sh = self.screen.get_size()
        mp = pygame.mouse.get_pos()
        self.mouse_logic = self.to_logic(mp)
        for b in reversed(self.buttons):
            if b["rect"].collidepoint(self.mouse_logic):
                self.hover_id = b["id"]
                self.hover_action = b["action"]
                break

    def handle_events(self):
        self._update_hover()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            elif ev.type == pygame.VIDEORESIZE and not self.android:
                self._resize((ev.w, ev.h))
            elif ev.type == pygame.KEYDOWN:
                if not self.on_key(ev.key):
                    return False
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                lp = self.to_logic(ev.pos)
                if ev.button == 1:
                    self.on_click(lp)
                elif ev.button == 3:
                    self.cancel_consumable()
                elif ev.button in (4, 5):
                    self.on_scroll(-1 if ev.button == 4 else 1)
            elif ev.type == pygame.FINGERDOWN:
                sw, sh = self.screen.get_size()
                self.on_click(self.to_logic((ev.x * sw, ev.y * sh)))
        return True

    def on_scroll(self, d):
        if self.phase == "deck_view":
            self.deck_scroll = max(0, self.deck_scroll - d * 60)

    def on_click(self, pos):
        b = None
        for btn in reversed(self.buttons):
            if btn["rect"].collidepoint(pos):
                b = btn
                break
        if b:
            if self.score_anim is not None:
                return
            self.dispatch(b["action"], b)
            return
        if self.phase == "title":
            self.new_run()
            self.phase = "blind_select"

    def cancel_consumable(self):
        if self.using_consumable is not None:
            self.using_consumable = None
            self.consum_targets = []
            self.game.selected = []

    def dispatch(self, act, b=None):
        g = self.game
        d = b["data"] if b else None
        if act == "start":
            self.new_run()
        elif act == "help":
            self.prev_phase = self.phase
            self.phase = "help"
        elif act == "quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif act == "resume":
            self.phase = self.prev_phase
        elif act == "to_title":
            self.phase = "title"
        elif act == "new_run":
            self.new_run()
        elif act == "pause_btn":
            self.prev_phase = "play" if self.phase in ("play",) else self.phase
            self.phase = "pause"
        elif act == "fight":
            g.start_blind()
            self.phase = "play"
            self.score_anim = None
            self.sel_anim = {}
            self.using_consumable = None
            self.consum_targets = []
        elif act == "skip":
            self.last_reward = g.skip_blind()
            if not g.game_over:
                g.open_shop()
                self.phase = "shop"
            else:
                self.phase = "game_over"
        elif act == "hand_card":
            self.on_hand_card(d)
        elif act == "play_hand":
            self.do_play()
        elif act == "discard":
            self.do_discard()
        elif act == "sort_rank":
            g.sort_hand("rank")
        elif act == "sort_suit":
            g.sort_hand("suit")
        elif act == "deck_view":
            self.prev_phase = "play" if self.phase != "deck_view" else self.prev_phase
            self.phase = "deck_view"
            self.deck_scroll = 0
        elif act == "close":
            self.phase = self.prev_phase
        elif act == "use_consum":
            self.using_consumable = d
            self.consum_targets = []
            g.selected = []
            if self.consum_need() == 0:
                self.apply_consumable()
        elif act == "consum_confirm":
            self.apply_consumable()
        elif act == "consum_cancel":
            self.cancel_consumable()
        elif act == "buy":
            if g.buy(d):
                self.say(g.toast)
            else:
                self.say(g.toast or "无法购买")
            g.toast = ""
        elif act == "reroll":
            if g.reroll_shop():
                self.say("商店已刷新")
            else:
                self.say("金币不足，无法刷新")
        elif act == "sell_joker":
            if self.confirm_sell == d:
                g.sell_joker(d)
                self.say(g.toast)
                g.toast = ""
                self.confirm_sell = None
            else:
                self.confirm_sell = d
        elif act == "next_blind":
            g.advance()
            if g.game_over:
                self.phase = "game_over"
            else:
                self.phase = "blind_select"
        elif act == "round_win":
            g.finish_round()
            self.phase = "shop_pending"
        elif act == "to_shop":
            g.open_shop()
            self.phase = "shop"
            self.confirm_sell = None

    def on_hand_card(self, idx):
        g = self.game
        if idx >= len(g.hand):
            return
        c = g.hand[idx]
        if self.using_consumable is not None:
            if c in self.consum_targets:
                self.consum_targets.remove(c)
            else:
                need = self.consum_need()
                if need and len(self.consum_targets) >= need:
                    self.consum_targets.pop(0)
                self.consum_targets.append(c)
        else:
            g.toggle_select(idx)

    def on_key(self, key):
        g = self.game
        if key in (pygame.K_ESCAPE, getattr(pygame, "K_AC_BACK", 1073742096)):
            if self.phase == "title":
                return False
            if self.phase in ("help", "deck_view"):
                self.phase = self.prev_phase
            elif self.phase == "pause":
                self.phase = self.prev_phase
            elif self.phase == "play" and self.using_consumable is not None:
                self.cancel_consumable()
            else:
                self.prev_phase = self.phase
                self.phase = "pause"
            return True
        if key == pygame.K_F11:
            self.android = False
            self.fullscreen_toggle()
            return True

        if self.phase == "title":
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.new_run()
        elif self.phase == "play":
            if self.score_anim is not None:
                return True
            if pygame.K_1 <= key <= pygame.K_9:
                self.on_hand_card(key - pygame.K_1)
            elif key in (pygame.K_SPACE, pygame.K_RETURN):
                self.do_play()
            elif key == pygame.K_d:
                self.do_discard()
            elif key == pygame.K_s:
                g.sort_hand("rank")
            elif key == pygame.K_a:
                g.sort_hand("suit")
            elif key == pygame.K_TAB:
                self.prev_phase = "play"
                self.phase = "deck_view"
                self.deck_scroll = 0
        elif self.phase == "blind_select":
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                self.dispatch("fight")
            elif key == pygame.K_s:
                self.dispatch("skip")
        elif self.phase == "shop":
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                self.dispatch("next_blind")
            elif key == pygame.K_r:
                self.dispatch("reroll")
        elif self.phase == "shop_pending":
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                self.dispatch("to_shop")
        elif self.phase == "round_win":
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                self.dispatch("round_win")
        elif self.phase == "game_over":
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                self.new_run()
        return True

    def fullscreen_toggle(self):
        cur = bool(self.screen.get_flags() & pygame.FULLSCREEN)
        if cur:
            self.screen = pygame.display.set_mode((W, H), pygame.RESIZABLE | pygame.DOUBLEBUF)
        else:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self._resize(self.screen.get_size())

    # ---------- 逻辑 ----------
    def consum_need(self):
        if self.using_consumable is None:
            return None
        c = self.game.consumables[self.using_consumable]
        if c.kind == "planet":
            return 0
        act, val, n = c.arg
        if act in ("money", "fool", "random_enh"):
            return 0
        return n

    def apply_consumable(self):
        g = self.game
        ok, m = g.use_consumable(self.using_consumable, list(self.consum_targets))
        self.say(m)
        self.using_consumable = None
        self.consum_targets = []
        g.selected = []
        if ok:
            self.particles.burst(640, 400, (200, 160, 250), 18)

    def do_play(self):
        g = self.game
        if self.score_anim is not None or not g.selected or g.hands_left <= 0:
            return
        res = g.play_selected()
        if res is None:
            return
        self.score_anim = {
            "steps": res.steps, "i": 0, "timer": 0.0,
            "chips": 0.0, "mult": 0.0, "res": res,
            "done": False, "wait": 0.0,
        }
        self.hand_flash = 1.0

    def do_discard(self):
        g = self.game
        if self.score_anim is not None or not g.selected or g.discards_left <= 0:
            return
        if g.discard_selected():
            self.particles.burst(640, HAND_Y, (200, 120, 120), 10)

    def update_score_anim(self, dt):
        sa = self.score_anim
        if sa is None:
            return
        if not sa["done"]:
            sa["timer"] += dt
            interval = 0.05 if len(sa["steps"]) < 28 else 0.026
            while sa["timer"] >= interval and sa["i"] < len(sa["steps"]):
                sa["timer"] -= interval
                _, dc, dm, xm, _c = sa["steps"][sa["i"]]
                sa["chips"] += dc
                sa["mult"] += dm
                if xm != 1.0:
                    sa["mult"] *= xm
                sa["i"] += 1
            if sa["i"] >= len(sa["steps"]):
                sa["done"] = True
                res = sa["res"]
                self.particles.burst(640, PLAY_Y, GOLD, 26, 4.2, 7)
                self.popups.append({"text": f"+{res.total:,}", "life": 1.0,
                                    "x": 640, "y": SCORE_Y - 30,
                                    "color": GOLD if res.total >= self.game.target * 0.4 else TEXT})
        else:
            sa["wait"] += dt
            if sa["wait"] > 0.8:
                g = self.game
                self.score_anim = None
                if g.phase == "round_win":
                    self.phase = "round_win"
                    self.win_time = 0.0
                    self.particles.burst(640, 360, (120, 230, 150), 40, 6, 8)
                elif g.phase == "round_lose":
                    g.lose_run()
                    self.phase = "game_over"

    def update(self, dt):
        self.particles.update(dt)
        for p in self.popups:
            p["life"] -= dt * 0.9
        self.popups = [p for p in self.popups if p["life"] > 0]
        self.hand_flash = max(0, self.hand_flash - dt * 2)
        if self.msg_life > 0:
            self.msg_life -= dt
            if self.msg_life <= 0:
                self.msg = ""

        if self.phase == "title":
            for f in self.floaters:
                f["y"] += f["sp"] * dt
                f["rot"] += f["vr"] * dt
                if f["y"] > H + 110:
                    f["y"] = -110
                    f["x"] = random.uniform(0, W)
            return

        g = self.game
        if self.phase == "play":
            self.update_score_anim(dt)
            if self.score_anim is None:
                self.display_score += (g.score - self.display_score) * min(1, dt * 9)
                if abs(g.score - self.display_score) < 1:
                    self.display_score = g.score
            sel = set(id(c) for c in g.selected)
            for c in g.hand:
                cur = self.sel_anim.get(id(c), 0.0)
                tgt = 1.0 if id(c) in sel else 0.0
                self.sel_anim[id(c)] = cur + (tgt - cur) * min(1, dt * 14)
        elif self.phase in ("round_win", "shop_pending", "game_over"):
            self.win_time += dt
            self.display_score += (g.score - self.display_score) * min(1, dt * 9)

    # ---------- 绘制调度 ----------
    def draw(self):
        c = self.canvas
        draw_bg(c, self.t)
        self.buttons = []
        self.tooltip_data = None
        self.last_id = -1

        ph = self.phase
        if ph == "title":
            self.draw_title()
        elif ph == "blind_select":
            self.draw_blind_select()
        elif ph == "play":
            self.draw_play()
        elif ph in ("round_win", "shop_pending"):
            self.draw_round_win()
        elif ph == "shop":
            self.draw_shop()
        elif ph == "game_over":
            self.draw_game_over()
        elif ph == "deck_view":
            self.draw_deck_view()
        elif ph == "help":
            self.draw_help()
        elif ph == "pause":
            self.draw_pause()

        self.particles.draw(c)
        for p in self.popups:
            R.draw_score_popup(c, p["x"], p["y"], p["text"], p["color"], p["life"])

        # 悬浮提示
        if self.hover_id >= 0:
            for b in self.buttons:
                if b["id"] == self.hover_id and b.get("tip"):
                    self.tooltip_data = {"pos": self.mouse_logic, "lines": b["tip"],
                                         "w": b.get("tipw", 300)}
                    break
        if self.tooltip_data:
            mx, my = self.tooltip_data["pos"]
            tooltip(c, self.tooltip_data["lines"], mx + 18, my + 18, self.tooltip_data["w"])

        if self.msg:
            a = min(1.0, self.msg_life / 0.5)
            tw = max(240, int(len(self.msg) * 15) + 60)
            r = pygame.Rect(640 - tw // 2, 676, tw, 34)
            s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            pygame.draw.rect(s, (24, 12, 24, int(230 * a)), (0, 0, r.w, r.h), border_radius=17)
            pygame.draw.rect(s, GOLD + (int(200 * a),), (0, 0, r.w, r.h), 2, border_radius=17)
            c.blit(s, r.topleft)
            txt(c, self.msg, 17, GOLD, 640, r.y + 7, "center", True)

        self.screen.fill((0, 0, 0))
        pygame.transform.scale(c, self.scaled_size, self._scaled_surf)
        self.screen.blit(self._scaled_surf, self.off)
        pygame.display.flip()

    # ---------- 标题 ----------
    def draw_title(self):
        c = self.canvas
        for f in self.floaters:
            draw_card(c, f["card"], f["x"], f["y"], scale=f["sc"],
                      angle=f["rot"], dim=True, t=self.t)
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((12, 6, 14, 155))
        c.blit(veil, (0, 0))

        pulse = 0.5 + 0.5 * math.sin(self.t * 1.6)
        y = 148
        n = len(TITLE)
        for i, ch in enumerate(TITLE):
            off = math.sin(self.t * 2 + i * 0.5) * 4
            col = mix(GOLD, (255, 242, 200), 0.25 + 0.45 * pulse)
            txt(c, ch, 78, col, 640 - (n - 1) * 43 + i * 86, y + off, "center", True, shadow=True)
        txt(c, SUBTITLE, 20, SUB, 640, y + 96, "center", True)
        txt(c, "用牌型撬动筹码，用小丑滚起倍率 —— 撑过 8 关首领盲注",
            16, (200, 190, 205), 640, y + 130, "center")

        bw, bh = 264, 58
        bx = 640 - bw // 2
        bid = self.add((bx, 382, bw, bh), "start")
        draw_button(c, (bx, 382, bw, bh), "开始游戏", True, self.hov(bid), 24,
                    color=(72, 34, 62), hotkey="Enter")
        bid = self.add((bx, 454, bw, 52), "help")
        draw_button(c, (bx, 454, bw, 52), "玩法说明", True, self.hov(bid), 21)
        bid = self.add((bx, 520, bw, 44), "quit")
        draw_button(c, (bx, 520, bw, 44), "退出", True, self.hov(bid), 19)

        txt(c, "提示：点击画面任意处也能开始", 13, (150, 138, 158), 640, 604, "center")
        txt(c, "v1.0 · 单机 Roguelike 牌组构筑 · 键盘 1-9 选牌 / 空格出牌",
            13, (130, 118, 140), 640, 636, "center")

    # ---------- 盲注选择 ----------
    def draw_blind_select(self):
        c = self.canvas
        g = self.game
        draw_hud(c, g, self.t)
        panel(c, (330, 170, 620, 400), "即 将 面 临")

        kind = g.blind["kind"]
        kc = {"small": (120, 200, 240), "big": (240, 160, 90), "boss": (240, 90, 90)}[kind]
        txt(c, g.blind["name"], 40, kc, 640, 228, "center", True, shadow=True)
        txt(c, f"目标  {g.target:,}", 30, GOLD, 640, 288, "center", True)
        txt(c, f"第 {g.ante} 关 · 共 {FINAL_ANTE} 关", 15, SUB, 640, 326, "center")

        if g.boss:
            rrect(c, (400, 352, 480, 96), (52, 24, 44), radius=12, width=2, bcolor=g.boss.color)
            txt(c, g.boss.name, 24, g.boss.color, 640, 362, "center", True)
            for i, ln in enumerate(wrap(g.boss.desc, 15, 440)):
                txt(c, ln, 15, TEXT, 640, 396 + i * 21, "center")
        else:
            txt(c, "无特殊效果", 16, SUB, 640, 380, "center")
            txt(c, f"你有 {g.mods['hands']} 次出牌 / {g.mods['discards']} 次弃牌 / "
                   f"手牌上限 {g.mods['hand_size']}", 15, (170, 200, 220), 640, 412, "center")

        bw, bh = 232, 56
        bid = self.add((640 - bw - 14, 494, bw, bh), "fight")
        draw_button(c, (640 - bw - 14, 494, bw, bh), "出  战", True, self.hov(bid), 24,
                    color=(46, 82, 54), hotkey="空格")
        can = g.blind_kind != "boss"
        bid = self.add((640 + 14, 494, bw, bh), "skip")
        draw_button(c, (640 + 14, 494, bw, bh), "跳过" if can else "不可跳过", can,
                    self.hov(bid) and can, 24, color=(78, 46, 46), hotkey="S")
        txt(c, "跳过可直接领取金币与随机奖励，但会失去本关收入", 13, SUB, 640, 558, "center")

        # 侧边小丑速览
        self.draw_joker_strip(640, 640, 0.62)

    def draw_joker_strip(self, cx, cy, sc=1.0):
        c = self.canvas
        g = self.game
        owned = [j for j in g.jokers if j]
        if not owned:
            return
        w, h = int(JOKER_W * sc), int(JOKER_H * sc)
        gap = w + 8
        total = gap * len(owned) - 8
        x0 = cx - total / 2 + w / 2
        for i, j in enumerate(owned):
            draw_joker(c, j, x0 + i * gap, cy, w, h, t=self.t)

    # ---------- 战斗 ----------
    def draw_play(self):
        c = self.canvas
        g = self.game
        draw_hud(c, g, self.t)

        # 小丑行
        slots = max(g.mods["joker_slots"], 5)
        gap = min(102, int(560 / max(1, slots)))
        total = gap * (slots - 1) + JOKER_W
        x0 = 640 - total / 2 + JOKER_W / 2
        for i in range(slots):
            j = g.jokers[i] if i < len(g.jokers) else None
            x = x0 + i * gap
            disabled = bool(g.boss and g.boss.key == "b_pillar" and i == 0 and j)
            r = draw_joker(c, j, x, JOKER_Y, t=self.t, dim=disabled)
            if j:
                bid = self.add(r, "joker_info", i,
                               tip=[f"【{j.name}】", j.live_desc(),
                                    f"稀有度：{RAR_CN[j.rarity]}"])
                if self.hov(bid):
                    pygame.draw.rect(c, GOLD, r, 3, border_radius=10)

        # 计分显示
        sa = self.score_anim
        if sa is not None:
            chips, mult = sa["chips"], sa["mult"]
            pulse = 0.0 if not sa["done"] else max(0, 1 - sa["wait"] * 2)
        else:
            pv = g.preview_hand()
            chips, mult = 0, 0
            if pv:
                chips, mult = float(pv["chips"]), float(pv["mult"])
                for j in g.jokers:
                    if j:
                        chips += j.chips
                        mult += j.mult
                chips += g.mods["joker_chips"]
                mult += g.mods["joker_mult"]
            pulse = 0.0
        draw_score_display(c, chips, mult, 640, SCORE_Y, self.t, pulse)

        if sa is not None:
            txt(c, sa["res"].hand_cn, 17, GOLD, 640, SCORE_Y + 44, "center", True)
        elif g.selected:
            pv = g.preview_hand()
            if pv:
                txt(c, f"{pv['cn']}   Lv.{pv['lv']}", 17, GOLD, 640, SCORE_Y + 44, "center", True)

        self.draw_play_zone()
        self.draw_hand()
        self.draw_consum_column()
        self.draw_action_buttons()

        if self.using_consumable is not None:
            need = self.consum_need()
            cc = g.consumables[self.using_consumable]
            rrect(c, (330, 468, 620, 40), (50, 28, 74), radius=10, width=2, bcolor=PURPLE)
            hint = f"使用【{cc.name}】"
            if need:
                hint += f"：选择 {need} 张牌（已选 {len(self.consum_targets)}）"
            txt(c, hint, 16, TEXT, 640, 477, "center", True)
            bid = self.add((640 + 210, 472, 100, 32), "consum_confirm")
            draw_button(c, (640 + 210, 472, 100, 32), "确定", True, self.hov(bid), 15)
            bid = self.add((640 + 316, 472, 100, 32), "consum_cancel")
            draw_button(c, (640 + 316, 472, 100, 32), "取消", True, self.hov(bid), 15)

    def draw_play_zone(self):
        c = self.canvas
        g = self.game
        sa = self.score_anim
        cards = list(getattr(sa["res"], "played_cards", [])) if sa else list(g.selected)
        if not cards:
            txt(c, "（选中的牌会出现在这里）", 15, (110, 96, 112), 640, PLAY_Y - 8, "center")
            return
        gap = 112
        total = gap * (len(cards) - 1) + CARD_W
        x0 = 640 - total / 2 + CARD_W / 2
        for i, card in enumerate(cards):
            draw_card(c, card, x0 + i * gap, PLAY_Y, selected=(card in g.selected),
                      t=self.t, scale=1.06 if sa else 1.0)

    def draw_hand(self):
        c = self.canvas
        g = self.game
        hand = g.hand
        if not hand:
            txt(c, "（手牌已空）", 15, (110, 96, 112), 640, HAND_Y - 8, "center")
            return
        n = len(hand)
        gap = min(106, int((950 - CARD_W) / max(1, n - 1))) if n > 1 else 0
        total = CARD_W + gap * (n - 1)
        x0 = 640 - total / 2 + CARD_W / 2
        for i, card in enumerate(hand):
            x = x0 + i * gap
            up = self.sel_anim.get(id(card), 0.0)
            marked = card in self.consum_targets
            y = HAND_Y - up * 22 - (22 if marked else 0)
            r = draw_card(c, card, x, y, selected=(card in g.selected) or marked,
                          t=self.t, scale=1.0 + up * 0.06)
            tip = [card.name] + ([ENH_DESC.get(card.enh, "")]
                                 if card.enh else []) + \
                  ([EDIT_DESC.get(card.edition, "")] if card.edition else []) + \
                  ([SEAL_DESC.get(card.seal, "")] if card.seal else [])
            tip = [t for t in tip if t] or [card.name, "普通牌"]
            self.add(r, "hand_card", i, tip=tip, tipw=250)
            if i < 9:
                txt(c, str(i + 1), 12, GOLD if card in g.selected else (118, 106, 122),
                    x - CARD_W // 2 + 6, HAND_Y + CARD_H // 2 - 20)

    def draw_consum_column(self):
        c = self.canvas
        g = self.game
        txt(c, "消耗牌", 13, SUB, CONSUM_X, 116, "center")
        for i in range(g.mods["consum_slots"]):
            y = 146 + i * (CONSUM_H + 14)
            cc = g.consumables[i] if i < len(g.consumables) else None
            bid = self.reserve((CONSUM_X - CONSUM_W // 2, y - CONSUM_H // 2,
                                CONSUM_W, CONSUM_H), "use_consum", i,
                               tip=[f"【{cc.name}】", cc.desc] if cc else None)
            draw_consumable(c, cc, CONSUM_X, y, t=self.t,
                            hover=self.hov(bid), selected=(self.using_consumable == i))

    def draw_action_buttons(self):
        c = self.canvas
        g = self.game
        bx = RIGHT_X - 92
        busy = self.score_anim is not None

        can_play = (not busy) and bool(g.selected) and g.hands_left > 0
        bid = self.add((bx, 498, 184, 54), "play_hand")
        draw_button(c, (bx, 498, 184, 54), "出  牌", can_play, self.hov(bid) and can_play,
                    24, color=(52, 92, 66))

        can_disc = (not busy) and bool(g.selected) and g.discards_left > 0
        bid = self.add((bx, 560, 184, 46), "discard")
        draw_button(c, (bx, 560, 184, 46), "弃  牌", can_disc, self.hov(bid) and can_disc,
                    20, color=(96, 50, 54))

        bid = self.add((bx, 614, 88, 40), "sort_rank")
        draw_button(c, (bx, 614, 88, 40), "按点数", True, self.hov(bid), 16)
        bid = self.add((bx + 96, 614, 88, 40), "sort_suit")
        draw_button(c, (bx + 96, 614, 88, 40), "按花色", True, self.hov(bid), 16)
        bid = self.add((bx, 662, 184, 38), "deck_view")
        draw_button(c, (bx, 662, 184, 38), f"查看牌库 ({len(g.full_deck)})", True,
                    self.hov(bid), 16)

        txt(c, f"抽牌堆 {len(g.deck)}", 14, SUB, CONSUM_X, 636, "center")
        txt(c, f"弃牌堆 {len(g.discard_pile)}", 13, (140, 128, 146), CONSUM_X, 658, "center")
        txt(c, f"手牌 {len(g.hand)}/{g.mods['hand_size']}", 13, (140, 128, 146),
            CONSUM_X, 680, "center")

        bid = self.add((RIGHT_X - 60, 116, 120, 34), "pause_btn")
        draw_button(c, (RIGHT_X - 60, 116, 120, 34), "菜单 (Esc)", True, self.hov(bid), 15)

    # ---------- 回合通过 ----------
    def draw_round_win(self):
        c = self.canvas
        g = self.game
        self.draw_play()
        self.buttons = []
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((8, 4, 10, 175))
        c.blit(veil, (0, 0))

        p = panel(c, (378, 132, 524, 456), "盲 注 通 过")
        yy = p.y + 68
        txt(c, g.blind["name"], 26, GOLD, 640, yy, "center", True)
        yy += 40
        txt(c, "最终得分", 15, SUB, 640, yy, "center")
        txt(c, f"{g.score:,}", 44, GREEN, 640, yy + 18, "center", True, shadow=True)
        yy += 74
        txt(c, f"目标  {g.target:,}", 16, SUB, 640, yy, "center")
        yy += 32

        rew = getattr(g, "round_reward", None)
        if self.phase == "shop_pending" and rew:
            rrect(c, (p.x + 58, yy, 408, 148), (34, 20, 34), radius=12, width=1, bcolor=LINE)
            rows = [("盲注奖励", rew["base"]), ("剩余出牌", rew["hands"]),
                    ("存款利息", rew["interest"])]
            for i, (k, v) in enumerate(rows):
                txt(c, k, 16, SUB, p.x + 88, yy + 14 + i * 30)
                txt(c, f"+{v}", 18, GOLD, p.x + 436, yy + 12 + i * 30, "right", True)
            pygame.draw.line(c, LINE, (p.x + 88, yy + 104), (p.x + 436, yy + 104), 1)
            txt(c, "合计", 18, TEXT, p.x + 88, yy + 112)
            txt(c, f"+{rew['total']}", 24, GOLD, p.x + 436, yy + 106, "right", True)
            bid = self.add((640 - 112, p.bottom - 72, 224, 54), "to_shop")
            draw_button(c, (640 - 112, p.bottom - 72, 224, 54), "进入商店", True,
                        self.hov(bid), 22, color=(72, 40, 86), hotkey="空格")
        else:
            bid = self.add((640 - 112, p.bottom - 72, 224, 54), "round_win")
            draw_button(c, (640 - 112, p.bottom - 72, 224, 54), "领取奖励", True,
                        self.hov(bid), 22, color=(72, 40, 86), hotkey="空格")

    # ---------- 商店 ----------
    def draw_shop(self):
        c = self.canvas
        g = self.game
        if g.shop is None:
            g.open_shop()

        bar = pygame.Surface((W, 54), pygame.SRCALPHA)
        for i in range(54):
            pygame.draw.line(bar, (34 + int(14 * i / 53), 18, 40), (0, i), (W, i))
        c.blit(bar, (0, 0))
        pygame.draw.line(c, LINE, (0, 54), (W, 54), 2)
        txt(c, "商  店", 26, GOLD, 24, 12, "left", True)
        txt(c, f"第 {g.ante} 关 · 下一个：{g.blind['name']}  目标 {g.target:,}",
            15, SUB, 152, 20)
        rrect(c, (W - 190, 10, 170, 36), (56, 32, 20), radius=10, width=2, bcolor=GOLD_D)
        txt(c, "\u25cf", 18, GOLD, W - 172, 16)
        txt(c, f"{g.money}", 24, GOLD, W - 20, 12, "right", True)

        items = g.shop["items"]
        jx = [300, 520, 740]
        ci = 0
        jj = 0
        for idx, it in enumerate(items):
            if it["type"] == "joker" and jj < 3:
                x = jx[jj]
                jj += 1
                if it["sold"]:
                    r = (x - 95, 85, 190, 250)
                    rrect(c, r, (34, 22, 34), radius=14, width=2, bcolor=(70, 50, 70))
                    txt(c, "已售出", 20, (110, 96, 112), x, 200, "center", True)
                    continue
                bid = self.reserve((x - 95, 85, 190, 250), "buy", idx)
                draw_joker_card_large(c, it["data"], x, 210,
                                      hover=self.hov(bid), t=self.t, price=it["data"].cost)
            elif it["type"] == "consum":
                x = 906 + ci * 98
                ci += 1
                if it["sold"]:
                    r = (x - 38, 113, 76, 104)
                    rrect(c, r, (34, 22, 34), radius=9, width=2, bcolor=(70, 50, 70))
                    txt(c, "已售出", 12, (110, 96, 112), x, 155, "center", True)
                    continue
                bid = self.reserve((x - 38, 113, 76, 104), "buy", idx,
                                   tip=[f"【{it['data'].name}】", it["data"].desc])
                draw_consumable(c, it["data"], x, 165, hover=self.hov(bid), price=4)
                txt(c, it["data"].name, 13, TEXT, x, 223, "center", True)
            elif it["type"] == "voucher":
                x = 1132
                if it["sold"]:
                    r = (x - 72, 113, 144, 104)
                    rrect(c, r, (34, 22, 34), radius=10, width=2, bcolor=(70, 50, 70))
                    txt(c, "已购买", 15, (110, 96, 112), x, 155, "center", True)
                    continue
                v = it["data"]
                bid = self.reserve((x - 72, 113, 144, 104), "buy", idx)
                hv = self.hov(bid)
                r = (x - 72, 113, 144, 104)
                rrect(c, r, brighten((58, 40, 30), 1.32 if hv else 1.0), radius=10,
                      width=2, bcolor=GOLD if hv else GOLD_D)
                txt(c, "\u25c6", 28, GOLD, x, 125, "center", True)
                txt(c, v.name, 16, TEXT, x, 165, "center", True)
                for i, ln in enumerate(wrap(v.desc, 12, 130)):
                    txt(c, ln, 12, (210, 200, 190), x, 187 + i * 16, "center")
                pr = (x - 24, 191, 48, 20)
                rrect(c, pr, GOLD_D, radius=10)
                txt(c, f"${v.cost}", 13, (40, 26, 10), x, pr[1] + 2, "center", True)
                txt(c, "优惠券", 13, SUB, x, 233, "center")

        txt(c, "小 丑 牌", 13, SUB, 520, 340, "center")
        txt(c, "消 耗 牌", 13, SUB, 955, 245, "center")

        # 自己的小丑
        txt(c, "你的小丑牌（点击两次出售）", 14, SUB, 640, 350, "center")
        slots = max(g.mods["joker_slots"], 5)
        gap = min(102, int(560 / max(1, slots)))
        total = gap * (slots - 1) + JOKER_W
        x0 = 640 - total / 2 + JOKER_W / 2
        for i in range(slots):
            j = g.jokers[i] if i < len(g.jokers) else None
            x = x0 + i * gap
            bid = None
            if j:
                bid = self.reserve((x - JOKER_W // 2, 430 - JOKER_H // 2, JOKER_W, JOKER_H),
                                   "sell_joker", i,
                                   tip=[f"【{j.name}】", j.live_desc(),
                                        f"售价 ${j.sell_value + g.mods['sell_bonus']}"])
            draw_joker(c, j, x, 430, t=self.t, hover=(self.hov(bid) if bid else False),
                       selected=(self.confirm_sell == i))
            if j and self.confirm_sell == i:
                txt(c, "再点一次确认", 12, RED, x, 500, "center", True)

        # 自己的消耗牌
        txt(c, "携带的消耗牌", 13, SUB, 362, 500, "center")
        for i in range(g.mods["consum_slots"]):
            x = 320 + i * 88
            cc = g.consumables[i] if i < len(g.consumables) else None
            draw_consumable(c, cc, x, 560, 64, 88, t=self.t)

        bid = self.add((40, 660, 200, 54), "reroll")
        draw_button(c, (40, 660, 200, 54), f"刷新 (${g.shop['reroll']})",
                    g.money >= g.shop["reroll"], self.hov(bid), 20, hotkey="R")

        bid = self.add((W - 280, 660, 240, 54), "next_blind")
        draw_button(c, (W - 280, 660, 240, 54), f"前往 {g.blind['name']}", True,
                    self.hov(bid), 22, color=(72, 40, 86), hotkey="空格")

        self.draw_hand_levels_mini(300, 610, 660)

    def draw_hand_levels_mini(self, x, y, w):
        c = self.canvas
        g = self.game
        items = list(reversed(HAND_TYPES))
        colw = w // 5
        for i, ht in enumerate(items):
            cx = x + (i % 5) * colw
            cy = y + (i // 5) * 25
            lv = g.hand_levels.get(ht.key, 1)
            cc, mm = ht.at(lv)
            col = (150, 140, 155) if lv == 1 else GOLD
            txt(c, f"{ht.cn} Lv{lv}", 12, col, cx, cy, "left")
            txt(c, f"{cc}x{mm}", 12, (168, 162, 178), cx + colw - 10, cy, "right")

    # ---------- 牌库 ----------
    def draw_deck_view(self):
        c = self.canvas
        g = self.game
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((8, 4, 10, 205))
        c.blit(veil, (0, 0))
        p = panel(c, (80, 56, W - 160, H - 112), "牌  库  一  览")
        deck = g.full_deck
        txt(c, f"共 {len(deck)} 张牌", 16, SUB, p.x + 26, p.y + 58)

        from collections import Counter
        sc = Counter(cd.suit for cd in deck)
        ec = Counter(cd.enh for cd in deck if cd.enh)
        edc = Counter(cd.edition for cd in deck if cd.edition)
        yy = p.y + 84
        sx = p.x + 26
        for s in ["S", "H", "D", "C"]:
            col = (226, 96, 96) if s in ("H", "D") else (205, 210, 225)
            txt(c, f"{SUIT_CN[s]} {sc.get(s, 0)}", 14, col, sx, yy)
            sx += 108
        enh_names = {"bonus": "加成", "mult": "倍率", "wild": "万能", "glass": "玻璃",
                     "steel": "钢铁", "stone": "石头", "gold": "黄金", "lucky": "幸运"}
        etxt = "强化：" + ("、".join(f"{enh_names.get(k, k)}x{v}" for k, v in ec.items())
                          if ec else "无")
        edtxt = "版本：" + ("、".join(f"{k}x{v}" for k, v in edc.items()) if edc else "无")
        txt(c, etxt, 14, (200, 190, 210), p.x + 26, yy + 24)
        txt(c, edtxt, 14, (200, 190, 210), p.x + 300, yy + 24)

        gy = yy + 56
        per = 13
        cw, ch = 78, 108
        top = p.y + 52
        bot = p.bottom - 66
        for i, cd in enumerate(deck):
            row, col = divmod(i, per)
            cx = p.x + 26 + col * (cw + 6) + cw // 2
            cy = gy + row * (ch + 8) + ch // 2 - int(self.deck_scroll)
            if cy - ch // 2 < top or cy + ch // 2 > bot:
                continue
            draw_card(c, cd, cx, cy, w=cw, h=ch, t=self.t)

        bid = self.add((640 - 90, p.bottom - 58, 180, 44), "close")
        draw_button(c, (640 - 90, p.bottom - 58, 180, 44), "返回", True, self.hov(bid),
                    20, hotkey="Esc")

    # ---------- 帮助 ----------
    def draw_help(self):
        c = self.canvas
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((8, 4, 10, 212))
        c.blit(veil, (0, 0))
        p = panel(c, (90, 36, W - 180, H - 72), "玩  法  说  明")

        left = [
            ("【目标】", 1),
            ("每关有 3 个盲注：小盲注 → 大盲注 → 首领盲注。", 0),
            ("每个盲注要求在有限出牌次数内累计达到目标分数。", 0),
            ("首领盲注带有负面效果，撑过第 8 关即通关。", 0),
            ("", 0),
            ("【得分公式】", 1),
            ("得分 = (牌型筹码 + 牌面筹码 + 小丑筹码) × (牌型倍率 + 小丑倍率)", 0),
            ("乘算（xN）类小丑是滚雪球的核心，遇到务必优先拿下。", 0),
            ("", 0),
            ("【流程】", 1),
            ("出战 → 出牌凑分 → 达标领金币 → 商店买小丑/消耗牌 → 下一盲注", 0),
            ("跳过小/大盲注可领金币与随机奖励，但会损失本关收入。", 0),
            ("", 0),
            ("【资源】", 1),
            ("金币来源：盲注奖励、剩余出牌次数、存款利息（每 5 金币 +1，有上限）。", 0),
            ("星球牌永久提升牌型等级；塔罗牌改造手牌；优惠券提供永久增益。", 0),
            ("", 0),
            ("【操作】", 1),
            ("点击手牌选中（最多 5 张），空格出牌，D 弃牌，S/A 排序，Tab 牌库。", 0),
            ("手机端：直接触摸操作，横屏体验最佳。", 0),
        ]
        yy = p.y + 60
        for ln, is_head in left:
            if is_head:
                txt(c, ln, 17, GOLD, p.x + 28, yy, "left", True)
                yy += 26
            else:
                txt(c, ln, 14, (216, 210, 224), p.x + 28, yy)
                yy += 21

        tx = p.x + 640
        txt(c, "【牌型等级表】", 17, GOLD, tx, p.y + 60, "left", True)
        yy = p.y + 94
        txt(c, "牌型", 13, SUB, tx, yy)
        txt(c, "基础", 13, SUB, tx + 96, yy)
        txt(c, "每级提升", 13, SUB, tx + 176, yy)
        txt(c, "当前", 13, SUB, tx + 286, yy)
        yy += 22
        for ht in HAND_TYPES:
            cc, mm = ht.at(1)
            owned = self.game.hand_levels.get(ht.key, 1) if self.game else 1
            col = (150, 142, 158) if owned == 1 else GOLD
            txt(c, ht.cn, 14, TEXT, tx, yy)
            txt(c, f"{cc} x {mm}", 14, (120, 190, 240), tx + 96, yy)
            txt(c, f"+{ht.chip_gain} / +{ht.mult_gain}", 13, (230, 140, 140), tx + 176, yy)
            txt(c, f"Lv{owned}", 13, col, tx + 286, yy)
            yy += 23

        bid = self.add((640 - 90, p.bottom - 58, 180, 44), "close")
        draw_button(c, (640 - 90, p.bottom - 58, 180, 44), "返回", True, self.hov(bid),
                    20, hotkey="Esc")

    # ---------- 暂停 ----------
    def draw_pause(self):
        c = self.canvas
        if self.prev_phase == "play":
            self.draw_play()
            self.buttons = []
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((8, 4, 10, 185))
        c.blit(veil, (0, 0))
        p = panel(c, (490, 196, 300, 328), "暂  停")
        bid = self.add((p.x + 40, p.y + 68, 220, 50), "resume")
        draw_button(c, (p.x + 40, p.y + 68, 220, 50), "继续游戏", True, self.hov(bid), 20)
        bid = self.add((p.x + 40, p.y + 130, 220, 50), "help")
        draw_button(c, (p.x + 40, p.y + 130, 220, 50), "玩法说明", True, self.hov(bid), 20)
        bid = self.add((p.x + 40, p.y + 192, 220, 50), "new_run")
        draw_button(c, (p.x + 40, p.y + 192, 220, 50), "重开一局", True, self.hov(bid), 20)
        bid = self.add((p.x + 40, p.y + 254, 220, 46), "to_title")
        draw_button(c, (p.x + 40, p.y + 254, 220, 46), "返回标题", True, self.hov(bid), 18)

    # ---------- 结束 ----------
    def draw_game_over(self):
        c = self.canvas
        g = self.game
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((8, 4, 10, 205))
        c.blit(veil, (0, 0))
        win = g.victory
        col = (120, 230, 150) if win else (230, 90, 90)
        p = panel(c, (338, 84, 604, 552), "通   关   !" if win else "游 戏 结 束")

        txt(c, "虚 空 之 冠 已 被 击 碎" if win else "分数不足，构筑崩盘",
            20, col, 640, p.y + 66, "center", True)
        txt(c, f"抵达  第 {min(g.ante, FINAL_ANTE)} / {FINAL_ANTE} 关", 22, TEXT,
            640, p.y + 104, "center", True)
        txt(c, f"最后一关  {g.score:,} / {g.target:,}", 17, SUB, 640, p.y + 138, "center")

        yy = p.y + 178
        rrect(c, (p.x + 58, yy, 488, 128), (34, 20, 34), radius=12, width=1, bcolor=LINE)
        stats = [("剩余金币", g.money), ("牌库张数", len(g.full_deck)),
                 ("销毁牌数", g.destroyed), ("优惠券", len(g.vouchers))]
        for i, (k, v) in enumerate(stats):
            cx = p.x + 58 + (i % 2) * 250
            cy = yy + 20 + (i // 2) * 58
            txt(c, k, 15, SUB, cx + 22, cy)
            txt(c, str(v), 24, GOLD, cx + 226, cy - 6, "right", True)

        yy += 146
        txt(c, "最终构筑", 15, SUB, 640, yy, "center")
        owned = [j for j in g.jokers if j]
        if not owned:
            txt(c, "（空）", 15, (130, 118, 136), 640, yy + 26, "center")
        else:
            gap = min(102, int(520 / max(1, len(owned))))
            total = gap * (len(owned) - 1) + JOKER_W
            x0 = 640 - total / 2 + JOKER_W / 2
            for i, j in enumerate(owned):
                draw_joker(c, j, x0 + i * gap, yy + 78, t=self.t)

        bid = self.add((640 - 232, p.bottom - 74, 224, 54), "new_run")
        draw_button(c, (640 - 232, p.bottom - 74, 224, 54), "再来一局", True,
                    self.hov(bid), 22, color=(72, 40, 86), hotkey="空格")
        bid = self.add((640 + 8, p.bottom - 74, 224, 54), "to_title")
        draw_button(c, (640 + 8, p.bottom - 74, 224, 54), "返回标题", True,
                    self.hov(bid), 22)


def main():
    App().run()


if __name__ == "__main__":
    main()
