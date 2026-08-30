# -*- coding: utf-8 -*-
"""无显示器环境下把各界面渲染成 PNG，用于人工检查 UI。"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "shots")
os.makedirs(OUT, exist_ok=True)

import pygame
import main as M
import render as R
from gamecore import JOKERS, ALL_TAROTS, ALL_PLANETS, Card

pygame.init()
pygame.display.set_mode((1280, 720))

app = M.App()


def save(name):
    app.draw()
    pygame.image.save(app.canvas, os.path.join(OUT, name + ".png"))
    print("  saved", name)


# 1) 标题
app.phase = "title"
app.t = 1.2
save("01_title")

# 2) 盲注选择（小盲注）
app.phase = "blind_select"
app.t = 2.0
save("02_blind_small")

# 3) 盲注选择（首领）
g = app.game
g.blind_index = 2
g._setup_blind()
app.t = 2.0
save("03_blind_boss")

# 4) 战斗（战前选牌）
g.blind_index = 0
g._setup_blind()
g.start_blind()
g.money = 24
g.jokers[0] = JOKERS[0].copy()
g.jokers[1] = JOKERS[14].copy()
g.jokers[2] = JOKERS[25].copy()
g.consumables = [ALL_TAROTS[0], ALL_PLANETS[2]]
app.phase = "play"
app.t = 3.0
g.selected = g.hand[:4]
app.sel_anim = {id(c): 1.0 for c in g.selected}
save("04_play_selected")

# 5) 出牌计分动画中
app.do_play()
for _ in range(26):
    app.update(1 / 60)
save("05_play_scoring")

# 6) 动画结束
for _ in range(120):
    app.update(1 / 60)
save("06_play_after")

# 7) 回合通过结算
g.score = g.target
g.phase = "round_win"
app.phase = "round_win"
g.finish_round()
app.phase = "shop_pending"
app.t = 4.0
save("07_round_win")

# 8) 商店
g.open_shop()
g.money = 28
app.phase = "shop"
app.t = 4.5
save("08_shop")

# 9) 帮助
app.phase = "help"
app.t = 5.0
save("09_help")

# 10) 牌库
app.phase = "deck_view"
save("10_deck")

# 11) 通关结局
g.ante = 8
g.victory = True
g.jokers[3] = JOKERS[38].copy()
g.jokers[4] = JOKERS[30].copy()
app.phase = "game_over"
app.t = 5.5
save("11_win")

# 12) 失败结局
g.victory = False
save("12_lose")

print("输出目录：", OUT)
