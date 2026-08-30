# -*- coding: utf-8 -*-
"""
自测：无需显示器
1) 牌型识别正确性断言
2) 随机策略跑大量对局，检查无异常 / 无死循环 / 数值合理
3) 渲染冒烟：逐个界面渲染一帧
"""
import os
import sys
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from gamecore import (Card, Game, detect_hand, score_play, HT, HAND_TYPES,
                      FINAL_ANTE, JOKERS)


def C(r, s, enh="", ed="", seal=""):
    return Card(r, s, enh, ed, seal)


# ---------------------------------------------------------------- 牌型识别
def test_hands():
    cases = [
        ("high",    [C(14, "S"), C(3, "H"), C(7, "D")]),
        ("pair",    [C(7, "S"), C(7, "H"), C(9, "D")]),
        ("twopair", [C(7, "S"), C(7, "H"), C(9, "D"), C(9, "C")]),
        ("three",   [C(7, "S"), C(7, "H"), C(7, "D"), C(9, "C")]),
        ("straight", [C(5, "S"), C(6, "H"), C(7, "D"), C(8, "C"), C(9, "S")]),
        ("flush",   [C(2, "S"), C(5, "S"), C(9, "S"), C(11, "S"), C(13, "S")]),
        ("full",    [C(7, "S"), C(7, "H"), C(7, "D"), C(9, "C"), C(9, "S")]),
        ("four",    [C(7, "S"), C(7, "H"), C(7, "D"), C(7, "C"), C(9, "S")]),
        ("sflush",  [C(5, "S"), C(6, "S"), C(7, "S"), C(8, "S"), C(9, "S")]),
    ]
    ok = True
    for want, cards in cases:
        got, sc = detect_hand(cards)
        flag = "OK " if got == want else "FAIL"
        if got != want:
            ok = False
        print(f"  [{flag}] 期望 {want:9s} 实得 {got:9s} 计分牌 {len(sc)}")
    # A 低顺
    got, _ = detect_hand([C(14, "S"), C(2, "H"), C(3, "D"), C(4, "C"), C(5, "S")])
    print(f"  [{'OK ' if got == 'straight' else 'FAIL'}] A-2-3-4-5 顺子 -> {got}")
    if got != "straight":
        ok = False
    # 万能牌凑同花
    got, _ = detect_hand([C(2, "S"), C(5, "S"), C(9, "S"), C(11, "S"), C(3, "H", "wild")])
    print(f"  [{'OK ' if got == 'flush' else 'FAIL'}] 万能牌凑同花 -> {got}")
    if got != "flush":
        ok = False
    # 五条（需要复制牌）
    got, _ = detect_hand([C(7, "S"), C(7, "H"), C(7, "D"), C(7, "C"), C(7, "S")])
    print(f"  [{'OK ' if got == 'five' else 'FAIL'}] 五条 -> {got}")
    if got != "five":
        ok = False
    # 石头牌不参与顺子
    got, _ = detect_hand([C(5, "S"), C(6, "H"), C(7, "D"), C(8, "C"), C(2, "S", "stone")])
    print(f"  [{'OK ' if got == 'high' else 'FAIL'}] 石头牌打断顺子 -> {got}")
    return ok


# ---------------------------------------------------------------- 贪心出牌
def best_subset(g):
    """枚举手牌 1~5 张组合，挑估算分最高的（忽略随机型小丑）"""
    from itertools import combinations
    from gamecore import rank_chips
    best, bestscore = None, -1.0
    hand = g.hand
    lim = min(5, len(hand))
    for k in range(1, lim + 1):
        for comb in combinations(hand, k):
            ht, sc = detect_hand(list(comb))
            lv = g.hand_levels.get(ht, 1)
            base_c, base_m = HT[ht].at(lv)
            chip = base_c + sum(50 if x.enh == "stone" else rank_chips(x.rank) for x in sc)
            mult = base_m
            for x in sc:
                if x.enh == "bonus":
                    chip += 30
                elif x.enh == "mult":
                    mult += 4
                elif x.enh == "glass":
                    mult *= 2
            s = chip * mult
            if s > bestscore:
                bestscore, best = s, list(comb)
    return best


# ---------------------------------------------------------------- 随机对局
def random_play(seed, max_steps=6000, greedy=False):
    g = Game(seed)
    rng = random.Random(seed * 31 + 7)
    steps = 0
    while not g.game_over and steps < max_steps:
        steps += 1
        ph = g.phase
        if ph == "blind_select":
            if rng.random() < 0.10 and g.blind_kind != "boss":
                g.skip_blind()
            else:
                g.start_blind()
        elif ph == "play":
            # 随机选 1-5 张出牌或弃牌
            if not g.hand:
                g.phase = "round_lose"
                g.lose_run()
                break
            res = None
            if rng.random() < 0.22 and g.discards_left > 0 and len(g.hand) > 1:
                k = rng.randint(1, min(3, len(g.hand)))
                g.selected = rng.sample(g.hand, k)
                g.discard_selected()
            elif greedy:
                g.selected = best_subset(g) or []
                res = g.play_selected()
                assert res is not None
            else:
                k = rng.randint(1, min(5, len(g.hand)))
                g.selected = rng.sample(g.hand, k)
                res = g.play_selected()
                assert res is not None
            if res is not None:
                assert res.total >= 0, f"负分 {res.total}  seed={seed}"
                assert isinstance(res.total, int), f"分数非整数 {res.total}  seed={seed}"
            if g.phase == "round_win":
                g.finish_round()
                g.open_shop()
            elif g.phase == "round_lose":
                g.lose_run()
                break
        elif ph == "shop":
            # 随机买 / 刷新
            for _ in range(rng.randint(0, 3)):
                if g.shop and g.shop["items"]:
                    idx = rng.randrange(len(g.shop["items"]))
                    g.buy(idx)
            if rng.random() < 0.25:
                g.reroll_shop()
            # 随机用掉消耗牌
            if g.consumables and rng.random() < 0.7:
                ci = rng.randrange(len(g.consumables))
                tg = rng.sample(g.hand, min(2, len(g.hand))) if g.hand else []
                g.use_consumable(ci, tg)
            # 随机卖小丑
            if rng.random() < 0.1:
                owned = [i for i, j in enumerate(g.jokers) if j]
                if owned:
                    g.sell_joker(rng.choice(owned))
            g.advance()
        else:
            g.phase = "blind_select"
    return g, steps


# ---------------------------------------------------------------- 智能 Bot
_XMULT_HOOKS = ("cardist", "tribe", "vampire", "hologram", "thief", "caino",
                "emptyslot", "blackboard", "lasthand", "obelisk", "cavendish",
                "constel", "dna", "blueprint", "yorick", "space", "burnt")


def joker_value(j):
    v = j.mult * 2.0 + j.chips * 0.05
    if j.hook and any(k in j.hook for k in _XMULT_HOOKS):
        v += 60
    if j.hook == "end_money":
        v += 8
    v += {"common": 0, "uncommon": 8, "rare": 18, "legend": 45}.get(j.rarity, 0)
    return v


def smart_shop(g):
    """优先拿乘算小丑 → 星球牌 → 优惠券，金币尽量花在刀刃上"""
    items = g.shop["items"]
    # 1) 小丑：按价值排序
    cand = [(i, it) for i, it in enumerate(items)
            if it["type"] == "joker" and not it["sold"]]
    cand.sort(key=lambda p: -joker_value(p[1]["data"]))
    for i, it in cand:
        if g.money >= it["data"].cost and g.free_joker_slot() is not None:
            g.buy(i)
    # 2) 消耗牌：优先星球牌（升级高频牌型）
    for i, it in enumerate(items):
        if it["sold"] or it["type"] != "consum":
            continue
        c = it["data"]
        if len(g.consumables) >= g.mods["consum_slots"]:
            break
        if c.kind == "planet" and g.money >= 8:
            g.buy(i)
        elif c.kind == "tarot" and g.money >= 12:
            g.buy(i)
    # 3) 用光能用的消耗牌（星球直接吃，塔罗选手牌）
    while g.consumables:
        ci = None
        for i, c in enumerate(g.consumables):
            if c.kind == "planet":
                ci = i
                break
        if ci is None:
            for i, c in enumerate(g.consumables):
                if c.arg and c.arg[0] in ("enh", "suit", "edition", "random_enh"):
                    ci = i
                    break
        if ci is None:
            ci = 0
        tg = []
        if g.consumables[ci].kind == "tarot" and g.hand:
            act = g.consumables[ci].arg[0]
            if act == "destroy":
                break
            tg = sorted(g.hand, key=lambda c: -c.rank)[:2]
        ok, _ = g.use_consumable(ci, tg)
        if not ok:
            break
    # 4) 优惠券：留 10 金币兜底
    for i, it in enumerate(items):
        if it["sold"] or it["type"] != "voucher":
            continue
        if g.money >= it["data"].cost + 10:
            g.buy(i)


def smart_play(seed, max_steps=6000):
    g = Game(seed)
    steps = 0
    while not g.game_over and steps < max_steps:
        steps += 1
        ph = g.phase
        if ph == "blind_select":
            g.start_blind()
        elif ph == "play":
            if not g.hand:
                g.lose_run()
                break
            sel = best_subset(g) or []
            # 牌型太差就弃掉废牌重抽（留至少 1 次出牌）
            ht, _ = detect_hand(sel)
            if (ht in ("high", "pair") and g.discards_left > 0
                    and g.hands_left > 1 and len(g.hand) > 1):
                drop = [c for c in g.hand if c not in sel]
                drop.sort(key=lambda c: c.rank)
                g.selected = drop[:2] or sorted(g.hand, key=lambda c: c.rank)[:2]
                if g.discard_selected():
                    continue
            g.selected = sel
            res = g.play_selected()
            assert res is not None and res.total >= 0
            if g.phase == "round_win":
                g.finish_round()
                g.open_shop()
            elif g.phase == "round_lose":
                g.lose_run()
                break
        elif ph == "shop":
            smart_shop(g)
            g.advance()
        else:
            g.phase = "blind_select"
    return g, steps


def test_smart(n=40):
    wins = 0
    hist = {}
    errs = []
    best = 0
    for s in range(n):
        try:
            g, steps = smart_play(s)
            if steps >= 6000:
                errs.append(f"seed {s}: 步数超限")
            if g.victory:
                wins += 1
            a = min(g.ante, FINAL_ANTE)
            hist[a] = hist.get(a, 0) + 1
            best = max(best, g.score)
        except Exception as e:
            import traceback
            errs.append(f"seed {s}: {type(e).__name__}: {e}\n{traceback.format_exc()}")
    print(f"  [智能Bot] {n} 局：通关 {wins}，最高单关得分 {best:,}")
    print("  关卡分布：" + "  ".join(f"第{k}关:{v}" for k, v in sorted(hist.items())))
    for e in errs[:3]:
        print("  [异常]", e)
    return not errs


def test_runs(n=250, greedy=False):
    wins = losses = 0
    ante_hist = {}
    max_score = 0
    errs = []
    tag = "贪心" if greedy else "随机"
    for s in range(n):
        try:
            g, steps = random_play(s, greedy=greedy)
            if steps >= 6000:
                errs.append(f"seed {s}: 步数超限（疑似死循环）")
            if g.victory:
                wins += 1
            else:
                losses += 1
            a = min(g.ante, FINAL_ANTE)
            ante_hist[a] = ante_hist.get(a, 0) + 1
            max_score = max(max_score, g.score)
        except Exception as e:
            import traceback
            errs.append(f"seed {s}: {type(e).__name__}: {e}\n{traceback.format_exc()}")
    print(f"  [{tag}] {n} 局：通关 {wins}，失败 {losses}，最高单关得分 {max_score:,}")
    print("  关卡分布：" + "  ".join(f"第{k}关:{v}" for k, v in sorted(ante_hist.items())))
    for e in errs[:5]:
        print("  [异常]", e)
    return len(errs) == 0 and wins + losses == n


# ---------------------------------------------------------------- 计分健全性
def test_scoring():
    g = Game(99)
    g.hand_levels["pair"] = 1
    played = [C(10, "S"), C(10, "H")]
    held = [C(5, "D")]
    res = score_play(g, played, held)
    # 对子 10x2 + 牌面 10+10 = 30 筹码 x 2 倍率 = 60
    expect = (10 + 20) * 2
    ok = res.total == expect
    print(f"  [{'OK ' if ok else 'FAIL'}] 对子10计分 {res.total}（期望 {expect}）")
    # 玻璃牌
    g2 = Game(100)
    p2 = [C(10, "S", "glass"), C(10, "H")]
    r2 = score_play(g2, p2, [])
    ok2 = r2.total == (10 + 20) * 2 * 2
    print(f"  [{'OK ' if ok2 else 'FAIL'}] 玻璃牌 x2 计分 {r2.total}（期望 {ok2 and (10+20)*4}）")
    # 钢铁牌留在手上
    g3 = Game(101)
    r3 = score_play(g3, [C(10, "S"), C(10, "H")], [C(3, "D", "steel")])
    ok3 = r3.total == int((10 + 20) * 2 * 1.5)
    print(f"  [{'OK ' if ok3 else 'FAIL'}] 钢铁牌 x1.5 计分 {r3.total}（期望 {int((10+20)*2*1.5)}）")
    return ok and ok2 and ok3


# ---------------------------------------------------------------- 渲染冒烟
def test_render():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    import main as M
    import render as R
    app = M.App()
    app.game.start_blind()
    app.game.money = 60
    app.game.jokers[0] = JOKERS[0].copy()
    app.game.jokers[1] = JOKERS[20].copy()
    app.game.consumables = []
    from gamecore import ALL_TAROTS, ALL_PLANETS
    app.game.consumables = [ALL_TAROTS[0], ALL_PLANETS[0]]
    phases = ["title", "blind_select", "play", "round_win", "shop_pending",
              "shop", "game_over", "deck_view", "help"]
    fails = []
    for ph in phases:
        try:
            app.phase = ph
            if ph == "play":
                app.game.selected = app.game.hand[:3]
            if ph in ("round_win", "shop_pending"):
                app.game.round_reward = {"base": 5, "hands": 2, "interest": 1, "total": 8}
            if ph == "shop":
                app.game.open_shop()
            app.draw()
        except Exception as e:
            import traceback
            fails.append(f"{ph}: {type(e).__name__}: {e}\n{traceback.format_exc()}")
    # 结束页两种结局
    for victory in (True, False):
        try:
            app.game.victory = victory
            app.phase = "game_over"
            app.draw()
        except Exception as e:
            import traceback
            fails.append(f"game_over({victory}): {e}\n{traceback.format_exc()}")
    # 出牌动画
    try:
        app.phase = "play"
        app.game.selected = app.game.hand[:2]
        app.do_play()
        for _ in range(400):
            app.update(1 / 60)
            app.draw()
    except Exception as e:
        import traceback
        fails.append(f"score_anim: {type(e).__name__}: {e}\n{traceback.format_exc()}")
    print(f"  渲染冒烟：{'全部通过' if not fails else str(len(fails)) + ' 项失败'}")
    for f in fails[:5]:
        print("  [异常]", f)
    return not fails


if __name__ == "__main__":
    print("=== 1. 牌型识别 ===")
    r1 = test_hands()
    print("=== 2. 计分健全性 ===")
    r2 = test_scoring()
    print("=== 3. 模拟对局 ===")
    r3 = test_runs(200)
    r3b = test_runs(60, greedy=True)
    r3c = test_smart(40)
    print("=== 4. 渲染冒烟 ===")
    r4 = test_render()
    print()
    ok = r1 and r2 and r3 and r3b and r3c and r4
    print("结果：" + ("全部通过" if ok else "存在问题"))
    sys.exit(0 if ok else 1)
