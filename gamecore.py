# -*- coding: utf-8 -*-
"""
诡牌筑局 - 核心逻辑层（不依赖 pygame，便于单元测试与移植）
Roguelike 牌组构筑：用扑克牌型凑分数，用小丑牌搭建连锁倍率。
"""
import random
from collections import Counter

# ---------------------------------------------------------------- 基础常量

SUITS = ["S", "H", "D", "C"]          # 黑桃 红心 方块 梅花
SUIT_CN = {"S": "黑桃", "H": "红心", "D": "方块", "C": "梅花"}
SUIT_SYMBOL = {"S": "\u2660", "H": "\u2665", "D": "\u2666", "C": "\u2663"}
RED_SUITS = {"H", "D"}
BLACK_SUITS = {"S", "C"}

RANK_CN = {2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9",
           10: "10", 11: "J", 12: "Q", 13: "K", 14: "A"}

SUIT_COLOR = {"S": (48, 52, 68), "H": (206, 58, 62), "D": (206, 58, 62), "C": (48, 52, 68)}


def rank_chips(rank: int) -> int:
    """牌面基础筹码"""
    if rank == 14:
        return 11
    if rank in (11, 12, 13):
        return 10
    return rank


# ---------------------------------------------------------------- 卡牌

class Card:
    _uid = 0

    def __init__(self, rank=2, suit="S", enh="", edition="", seal=""):
        self.rank = rank
        self.suit = suit
        self.enh = enh              # 强化：bonus/mult/wild/glass/steel/stone/gold/lucky
        self.edition = edition      # 版本：foil/holo/poly
        self.seal = seal            # 封印：red/blue/purple/gold
        Card._uid += 1
        self.uid = Card._uid

    # -- 显示
    @property
    def rank_str(self):
        return RANK_CN.get(self.rank, "?")

    @property
    def suit_str(self):
        return SUIT_SYMBOL.get(self.suit, "?")

    @property
    def name(self):
        if self.enh == "stone":
            return "石头牌"
        return self.rank_str + self.suit_str

    @property
    def is_red(self):
        return self.suit in RED_SUITS

    @property
    def is_face(self):
        return self.rank in (11, 12, 13)

    def copy(self):
        return Card(self.rank, self.suit, self.enh, self.edition, self.seal)

    def __repr__(self):
        return f"<{self.name}{'/'+self.enh if self.enh else ''}>"


def make_deck(with_stone=False):
    """标准 52 张牌组"""
    d = [Card(r, s) for s in SUITS for r in range(2, 15)]
    return d


# ---------------------------------------------------------------- 牌型

class HandType:
    def __init__(self, key, cn, chips, mult, cg, mg, planet):
        self.key = key
        self.cn = cn
        self.chips = chips
        self.mult = mult
        self.chip_gain = cg
        self.mult_gain = mg
        self.planet = planet

    def at(self, level):
        return (self.chips + (level - 1) * self.chip_gain,
                self.mult + (level - 1) * self.mult_gain)


HAND_TYPES = [
    HandType("five",    "五条",     120, 12, 35, 3, "厄里斯"),
    HandType("sflush",  "同花顺",   100,  8, 30, 3, "海王星"),
    HandType("four",    "四条",      60,  7, 25, 3, "火星"),
    HandType("full",    "葫芦",      40,  4, 20, 2, "木星"),
    HandType("flush",   "同花",      35,  4, 15, 2, "金星"),
    HandType("straight","顺子",      30,  4, 20, 3, "水星"),
    HandType("three",   "三条",      30,  3, 15, 2, "土星"),
    HandType("twopair", "两对",      20,  2, 15, 1, "天王星"),
    HandType("pair",    "对子",      10,  2, 15, 1, "冥王星"),
    HandType("high",    "高牌",       5,  1, 10, 1, "月亮"),
]
HT = {h.key: h for h in HAND_TYPES}
HT_ORDER = [h.key for h in HAND_TYPES]   # 强 -> 弱


def _straight_ranks(ranks):
    """判断一组点数能否组成顺子，返回最大顺子的点数集合或 None"""
    rs = sorted(set(ranks))
    if len(rs) < 5:
        return None
    # A 可作 1
    if 14 in rs:
        rs2 = [1] + rs[:-1]
        if _consecutive(rs2):
            return set(rs2)
    for i in range(len(rs) - 4):
        win = rs[i:i + 5]
        if _consecutive(win):
            return set(win)
    return None


def _consecutive(rs):
    rs = sorted(rs)
    return len(rs) >= 5 and all(rs[i + 1] - rs[i] == 1 for i in range(len(rs) - 1)) and len(rs) == 5


def detect_hand(cards):
    """
    识别牌型。cards: 打出的 1~5 张牌
    返回 (hand_type_key, 参与计分的牌列表)
    """
    if not cards:
        return "high", []
    playable = [c for c in cards if c.enh != "stone"]
    stones = [c for c in cards if c.enh == "stone"]

    n = len(cards)
    ranks = [c.rank for c in playable]
    rc = Counter(ranks)

    # 花色统计：万能牌可充当任意花色
    wilds = [c for c in playable if c.enh == "wild"]
    suit_c = Counter(c.suit for c in playable if c.enh != "wild")

    def flush_suit():
        for s in SUITS:
            if suit_c.get(s, 0) + len(wilds) >= 5:
                return s
        return None

    fs = flush_suit() if n >= 5 else None

    # 顺子（石头牌不参与）
    sr = _straight_ranks(ranks) if n >= 5 else None

    # 五条 / 四条 / 三条 / 对子
    five = [r for r, c in rc.items() if c >= 5]
    four = [r for r, c in rc.items() if c >= 4]
    three = [r for r, c in rc.items() if c >= 3]
    pairs = [r for r, c in rc.items() if c >= 2]

    def pick(rankset, k):
        out = [c for c in playable if c.rank in rankset]
        return out[:k]

    if five:
        return "five", pick({five[0]}, 5)
    if fs and sr:
        sel = [c for c in playable if (c.enh == "wild" or c.rank in sr) and
               (c.enh == "wild" or c.suit == fs)][:5]
        return "sflush", sel
    if four:
        return "four", pick({four[0]}, 4)
    if three and (len(three) >= 2 or len(pairs) >= 2):
        t = sorted(three, key=lambda r: (-rc[r], -r))
        tr = t[0]
        rest = [r for r in pairs if r != tr]
        if rest:
            pr = max(rest)
            return "full", pick({tr}, 3) + pick({pr}, 2)
        return "full", pick({tr}, 3) + pick({t[1]}, 2)
    if fs:
        sel = [c for c in playable if c.enh == "wild" or c.suit == fs][:5]
        return "flush", sel
    if sr:
        sel = [c for c in playable if c.rank in sr][:5]
        return "straight", sel
    if three:
        tr = max(three, key=lambda r: (rc[r], r))
        return "three", pick({tr}, 3)
    if len(pairs) >= 2:
        top = sorted(pairs, key=lambda r: (rc[r], r))[-2:]
        return "twopair", pick({top[0]}, 2) + pick({top[1]}, 2)
    if len(pairs) == 1:
        return "pair", pick({pairs[0]}, 2)

    best = max(playable, key=lambda c: c.rank) if playable else None
    return "high", ([best] if best else [])


# ---------------------------------------------------------------- 小丑牌

RARITY = {"common": "普通", "uncommon": "罕见", "rare": "稀有", "legend": "传奇"}
RARITY_COLOR = {"common": (110, 190, 220), "uncommon": (90, 200, 130),
                "rare": (200, 110, 210), "legend": (235, 190, 80)}


class Joker:
    """小丑牌。effect 字段描述静态加成，hook 描述触发式效果"""

    def __init__(self, key, name, desc, cost, rarity,
                 chips=0, mult=0, xmult=0.0, hook=None, arg=None, growth=None):
        self.key = key
        self.name = name
        self.desc = desc
        self.cost = cost
        self.rarity = rarity
        self.chips = chips
        self.mult = mult
        self.xmult = xmult
        self.hook = hook            # 字符串标识，在 score_play 中分派
        self.arg = arg
        self.growth = growth or {}  # 成长型小丑的动态数值
        self.sell_value = max(1, cost // 2)

    def copy(self):
        j = Joker(self.key, self.name, self.desc, self.cost, self.rarity,
                  self.chips, self.mult, self.xmult, self.hook, self.arg,
                  dict(self.growth))
        return j

    def live_desc(self):
        d = self.desc
        for k, v in self.growth.items():
            d = d.replace("{" + k + "}", str(v))
        return d


# ---- 小丑牌图鉴 -------------------------------------------------------
# hook 取值：
#   card_xxx    : 每张计分牌触发
#   hand_xxx    : 打出牌组后触发（通用）
#   end_xxx     : 回合结束结算
JOKERS = [
    # ===== 普通（静态）=====
    Joker("j_greedy",   "贪婪小丑",   "每张打出的方块牌 +3 倍率", 4, "common", hook="card_suit_mult", arg=("D", 3)),
    Joker("j_lustful",  "色欲小丑",   "每张打出的红心牌 +3 倍率", 4, "common", hook="card_suit_mult", arg=("H", 3)),
    Joker("j_wrathful", "暴怒小丑",   "每张打出的黑桃牌 +3 倍率", 4, "common", hook="card_suit_mult", arg=("S", 3)),
    Joker("j_glutton",  "暴食小丑",   "每张打出的梅花牌 +3 倍率", 4, "common", hook="card_suit_mult", arg=("C", 3)),
    Joker("j_crafty",   "狡诈小丑",   "若牌型含顺子 +80 筹码", 4, "common", hook="hand_straight"),
    Joker("j_misprint", "印刷错误",   "随机 +0~23 倍率", 4, "common", hook="hand_random"),
    Joker("j_sly",      "诡诈小丑",   "若牌型含对子 +50 筹码", 4, "common", hook="hand_pair"),
    Joker("j_zany",     "滑稽小丑",   "若牌型含三条 +30 倍率", 4, "common", hook="hand_three"),
    Joker("j_half",     "半成品",     "若牌型为高牌 +20 倍率", 4, "common", hook="hand_high"),
    Joker("j_duo",      "双打小丑",   "若牌型含两对 +40 倍率", 4, "common", hook="hand_twopair"),
    Joker("j_flat",     "平板小丑",   "+4 倍率", 4, "common", mult=4),
    Joker("j_stencil",  "模板小丑",   "每张打出的牌 +10 筹码", 4, "common", hook="card_chips", arg=10),
    Joker("j_banner",   "锦旗",       "每次剩余弃牌 +30 筹码", 4, "common", hook="hand_discards_chips"),
    Joker("j_scary",    "惊悚面孔",   "+30 筹码", 4, "common", chips=30),
    Joker("j_fortune",  "幸运小丑",   "本回合每剩余 1 次出牌 +4 倍率", 4, "common", hook="hand_hands_mult"),
    Joker("j_supernova","超新星",     "本局每打出过一次当前牌型，+1 倍率", 4, "common", hook="hand_nova"),

    # ===== 罕见 =====
    Joker("j_green",    "绿色小丑",   "每次出牌 +1 倍率，弃牌则 -1（当前 {m}）", 5, "uncommon",
          hook="hand_green", growth={"m": 0}),
    Joker("j_red",      "红色小丑",   "+6 倍率", 5, "uncommon", mult=6),
    Joker("j_blue",     "蓝色小丑",   "牌库中每剩 2 张牌 +1 筹码（当前 {c}）", 5, "uncommon", hook="hand_deck_chips"),
    Joker("j_ride",     "巴士之旅",   "每次连续打出人头牌 +1 倍率（当前 {m}）", 5, "uncommon",
          hook="hand_ride", growth={"m": 0}),
    Joker("j_space",    "太空小丑",   "牌型等级提升时 +3 倍率（当前 {m}）", 5, "uncommon", hook="hand_space", growth={"m": 0}),
    Joker("j_egg",      "彩蛋",       "回合结束 +3 金币；每回合售价 +3", 5, "uncommon", hook="end_money", arg=3),
    Joker("j_square",   "方形小丑",   "若恰好打出 4 张牌 +40 筹码", 5, "uncommon", hook="hand_exact4"),
    Joker("j_riffle",   "洗牌手",     "若剩余出牌次数为 0，x3 倍率", 5, "uncommon", hook="hand_lasthand"),
    Joker("j_abstract", "抽象小丑",   "每张小丑牌 +3 倍率", 5, "uncommon", hook="hand_joker_mult", arg=3),
    Joker("j_8ball",    "八号球",     "每次打出点数为 8 的牌 +3 倍率（当前 {m}）", 5, "uncommon", hook="hand_rank8", growth={"m": 0}),
    Joker("j_erosion",  "侵蚀",       "牌库每少 1 张牌（低于52）+4 倍率（当前 {m}）", 5, "uncommon", hook="hand_erosion", growth={"m": 0}),
    Joker("j_ice",      "冰淇淋",     "+100 筹码，每次出牌 -10（当前 {c}）", 5, "uncommon", hook="hand_ice", growth={"c": 100}),
    Joker("j_constel",  "星座",       "每使用一张星球牌 x1.1 倍率（当前 {x}）", 6, "uncommon", hook="hand_constel", growth={"x": 1.0}),
    Joker("j_bull",     "公牛",       "每次出牌 +2 筹码，本回合内累加（当前 {c}）", 6, "uncommon", hook="hand_bull", growth={"c": 0}),

    # ===== 稀有 =====
    Joker("j_blackboard","黑板",      "若手牌全为黑色牌，x3 倍率", 6, "rare", hook="hand_blackboard"),
    Joker("j_vampire",  "吸血鬼",     "每张打出的增强牌 x1.2 倍率（本局累计 {x}）", 7, "rare", hook="hand_vampire", growth={"x": 1.0}),
    Joker("j_obelisk",  "方尖碑",     "本局打出最多的牌型改为 x1 倍率", 7, "rare", hook="hand_obelisk"),
    Joker("j_cavendish","卡文迪什",   "x3 倍率，回合结束有 1/4 概率消失", 7, "rare", hook="hand_cavendish"),
    Joker("j_cardist",  "纸牌大师",   "每张打出的牌 x1.3 倍率", 7, "rare", hook="hand_cardist"),
    Joker("j_hologram", "全息投影",   "每次出牌后 x1.05 倍率（当前 {x}）", 7, "rare", hook="hand_hologram", growth={"x": 1.0}),
    Joker("j_thief",    "窃贼",       "每次弃牌后 x1.25 倍率（当前 {x}）", 7, "rare", hook="hand_thief", growth={"x": 1.0}),
    Joker("j_midas",    "点金手",     "打出的每张人头牌在回合结束时变为金色", 7, "rare", hook="card_goldify"),
    Joker("j_stencilx", "镂空模板",   "每个空的小丑槽 x1.5 倍率", 7, "rare", hook="hand_emptyslot"),
    Joker("j_burnt",    "烧焦小丑",   "牌型等级提升时该牌型 +2 倍率", 7, "rare", hook="hand_burnt", growth={"m": 0}),
    Joker("j_cloud",    "云九",       "持有金币每 5 元 +1 倍率", 7, "rare", hook="hand_money_mult"),

    # ===== 传奇 =====
    Joker("j_tribe",    "部落",       "每张打出的牌 x2 倍率（需 4 张以上同点同花）", 10, "legend", hook="hand_tribe"),
    Joker("j_blueprint","蓝图",       "复制右侧小丑牌的效果", 10, "legend", hook="hand_blueprint"),
    Joker("j_dna",      "双螺旋",     "每次出牌后 +1 手牌上限，x1.5 倍率", 10, "legend", hook="hand_dna"),
    Joker("j_caino",    "该隐之印",   "每销毁一张牌 x1.4 倍率（当前 {x}）", 10, "legend", hook="hand_caino", growth={"x": 1.0}),
    Joker("j_yorick",   "约里克",     "每丢弃 23 张牌 x1.5 倍率（{d}/23）", 10, "legend", hook="hand_yorick", growth={"d": 0}),
]

JOKER_BY_KEY = {j.key: j for j in JOKERS}


def random_joker(rng, exclude_keys=(), rarity=None):
    pool = [j for j in JOKERS if j.key not in exclude_keys]
    if rarity:
        pool = [j for j in pool if j.rarity == rarity]
        if not pool:
            pool = [j for j in JOKERS if j.key not in exclude_keys]
    weights = {"common": 62, "uncommon": 26, "rare": 10, "legend": 2}
    ws = [weights[j.rarity] for j in pool]
    return rng.choices(pool, weights=ws, k=1)[0].copy()


# ---------------------------------------------------------------- 消耗牌

class Consumable:
    def __init__(self, key, name, desc, kind, arg=None):
        self.key = key
        self.name = name
        self.desc = desc
        self.kind = kind          # tarot / planet
        self.arg = arg


def build_tarots():
    t = [
        Consumable("t_emperor", "皇帝", "将最多 2 张牌变为 倍率牌（+4 倍率）", "tarot", ("enh", "mult", 2)),
        Consumable("t_hieroph", "教皇", "将最多 2 张牌变为 加成牌（+30 筹码）", "tarot", ("enh", "bonus", 2)),
        Consumable("t_lovers",  "恋人", "将 1 张牌变为 万能牌（可作任意花色）", "tarot", ("enh", "wild", 1)),
        Consumable("t_chariot", "战车", "将 1 张牌变为 钢铁牌（留在手中时 x1.5）", "tarot", ("enh", "steel", 1)),
        Consumable("t_justice", "正义", "将 1 张牌变为 玻璃牌（x2 倍率，可能碎裂）", "tarot", ("enh", "glass", 1)),
        Consumable("t_devil",   "恶魔", "将 1 张牌变为 黄金牌（回合结束留手上 +3 金币）", "tarot", ("enh", "gold", 1)),
        Consumable("t_tower",   "塔",   "将 1 张牌变为 石头牌（无点数，+50 筹码）", "tarot", ("enh", "stone", 1)),
        Consumable("t_star",    "星星", "将最多 3 张牌转为黑桃", "tarot", ("suit", "S", 3)),
        Consumable("t_moon",    "月亮", "将最多 3 张牌转为梅花", "tarot", ("suit", "C", 3)),
        Consumable("t_sun",     "太阳", "将最多 3 张牌转为红心", "tarot", ("suit", "H", 3)),
        Consumable("t_world",   "世界", "将最多 3 张牌转为方块", "tarot", ("suit", "D", 3)),
        Consumable("t_magician","魔术师","将最多 2 张牌变为 幸运牌", "tarot", ("enh", "lucky", 2)),
        Consumable("t_hanged",  "倒吊人", "销毁最多 2 张选中的牌", "tarot", ("destroy", 2, 2)),
        Consumable("t_death",   "死神", "销毁 1 张牌，将另 1 张变为它的复制", "tarot", ("death", 1, 2)),
        Consumable("t_judgem",  "审判", "随机为 1 张牌添加随机强化", "tarot", ("random_enh", 1, 1)),
        Consumable("t_fool",    "愚人", "随机生成一张塔罗牌到消耗区", "tarot", ("fool", 0, 0)),
        Consumable("t_wheel",   "命运之轮", "1/4 概率为 1 张牌添加闪箔/全息/多彩版本", "tarot", ("edition", 1, 1)),
        Consumable("t_hermit",  "隐者", "立即获得 20 金币", "tarot", ("money", 20, 0)),
    ]
    return t


def build_planets():
    return [Consumable("p_" + h.key, h.planet, f"提升【{h.cn}】牌型 1 个等级", "planet", h.key)
            for h in HAND_TYPES]


ALL_TAROTS = build_tarots()
ALL_PLANETS = build_planets()


def random_consumable(rng, prefer_planet=0.34):
    if rng.random() < prefer_planet:
        return random.choice(ALL_PLANETS)
    return random.choice(ALL_TAROTS)


# ---------------------------------------------------------------- 优惠券

class Voucher:
    def __init__(self, key, name, desc, cost, apply_fn):
        self.key = key
        self.name = name
        self.desc = desc
        self.cost = cost
        self.apply_fn = apply_fn


def _v_hands(g):   g.mods["hands"] += 1
def _v_disc(g):    g.mods["discards"] += 1
def _v_size(g):    g.mods["hand_size"] += 1
def _v_slot(g):    g.mods["joker_slots"] += 1
def _v_money(g):   g.mods["interest_cap"] += 5
def _v_reroll(g):  g.mods["reroll_cost"] = max(1, g.mods["reroll_cost"] - 1)
def _v_slotc(g):   g.mods["consum_slots"] += 1
def _v_shopmul(g): g.mods["joker_mult"] += 4
def _v_shopch(g):  g.mods["joker_chips"] += 20
def _v_sell(g):    g.mods["sell_bonus"] += 2


VOUCHERS = [
    Voucher("v_hands",   "清算",   "每回合出牌次数 +1", 10, _v_hands),
    Voucher("v_disc",    "观测",   "每回合弃牌次数 +1", 10, _v_disc),
    Voucher("v_size",    "涂鸦",   "手牌上限 +1", 10, _v_size),
    Voucher("v_slot",    "马戏团", "小丑牌槽位 +1", 12, _v_slot),
    Voucher("v_money",   "高利贷", "每回合利息上限 +5 金币", 10, _v_money),
    Voucher("v_reroll",  "幻象",   "商店刷新费用 -1 金币", 8, _v_reroll),
    Voucher("v_slotc",   "星图",   "消耗牌槽位 +1", 10, _v_slotc),
    Voucher("v_jmul",    "剪纸",   "所有小丑牌 +4 倍率", 14, _v_shopmul),
    Voucher("v_jchip",   "墨水瓶", "所有小丑牌 +20 筹码", 14, _v_shopch),
    Voucher("v_sell",    "典当行", "出售小丑牌时额外 +2 金币", 8, _v_sell),
]
VOUCHER_BY_KEY = {v.key: v for v in VOUCHERS}


# ---------------------------------------------------------------- Boss 盲注

class Boss:
    def __init__(self, key, name, desc, color):
        self.key = key
        self.name = name
        self.desc = desc
        self.color = color


BOSSES = [
    Boss("b_red",     "深红之心",   "所有红心与方块牌不计分",        (206, 58, 62)),
    Boss("b_blue",    "蔚蓝之铃",   "所有黑桃与梅花牌不计分",        (70, 120, 220)),
    Boss("b_hook",    "翠绿之钩",   "每次出牌后随机弃掉 2 张手牌",    (80, 180, 110)),
    Boss("b_wall",    "琥珀之墙",   "前 2 次出牌最终得分减半",        (220, 170, 60)),
    Boss("b_head",    "苍白之首",   "同花类牌型倍率减半",            (210, 200, 190)),
    Boss("b_club",    "靛蓝之锤",   "所有牌型等级视为 1 级",          (110, 100, 200)),
    Boss("b_needle",  "绯红之针",   "第一次出牌得分减半",            (200, 90, 120)),
    Boss("b_eye",     "紫罗兰之眼", "每回合出牌次数 -1",              (150, 100, 210)),
    Boss("b_serpent", "青碧之蛇",   "每次出牌后手牌上限 -1（最低 3）", (60, 170, 170)),
    Boss("b_pillar",  "玄黑之柱",   "最左侧小丑牌失效",              (70, 70, 90)),
    Boss("b_final",   "虚 空 之 冠", "所有小丑牌效果减半（最终考验）",  (180, 60, 180)),
]
BOSS_BY_KEY = {b.key: b for b in BOSSES}
NORMAL_BOSSES = [b for b in BOSSES if b.key != "b_final"]


# ---------------------------------------------------------------- 计分

ANTE_BASE = [0, 300, 800, 2000, 5000, 11000, 20000, 35000, 50000]
BLIND_MULT = {"small": 1.0, "big": 1.5, "boss": 2.0}
BLIND_CN = {"small": "小盲注", "big": "大盲注", "boss": "首领盲注"}
FINAL_ANTE = 8


class ScoreResult:
    def __init__(self):
        self.hand_type = "high"
        self.hand_cn = "高牌"
        self.steps = []        # (文本, 筹码增量, 倍率增量, x倍率, 颜色)
        self.chips = 0
        self.mult = 0.0
        self.total = 0
        self.scoring = []
        self.money_gain = 0


def score_play(game, played, held):
    """
    完整计分流程。played: 打出的牌（按选择顺序）; held: 留在手中的牌
    返回 ScoreResult
    """
    res = ScoreResult()
    boss = game.boss
    rng = game.rng

    ht_key, scoring = detect_hand(played)
    res.hand_type = ht_key
    res.hand_cn = HT[ht_key].cn
    res.scoring = scoring

    level = 1 if (boss and boss.key == "b_club") else game.hand_levels.get(ht_key, 1)
    bc, bm = HT[ht_key].at(level)
    chips = float(bc)
    mult = float(bm)
    res.steps.append((f"{HT[ht_key].cn} Lv.{level}", bc, bm, 1.0, (235, 220, 160)))

    # 牌型升级小丑（太空/烧焦）在升级时才生效，不在此处累加
    jokers = [j for j in game.jokers if j]
    if boss and boss.key == "b_pillar" and jokers:
        jokers = jokers[1:]
    if boss and boss.key == "b_final":
        jokers = [j for j in jokers]     # 效果减半在下方处理
    weaken = 0.5 if (boss and boss.key == "b_final") else 1.0

    scoring_set = set(id(c) for c in scoring)

    # ---------- 逐张计分 ----------
    for card in played:
        if card.enh == "stone":
            cc = 50.0
            res.steps.append((f"{card.name}", cc, 0, 1.0, (150, 150, 160)))
            chips += cc
            continue

        disabled = False
        if boss and boss.key == "b_red" and card.is_red:
            disabled = True
        if boss and boss.key == "b_blue" and not card.is_red:
            disabled = True

        if disabled:
            res.steps.append((f"{card.name}（被压制）", 0, 0, 1.0, (120, 120, 130)))
        else:
            cc = float(rank_chips(card.rank))
            steps_local = [("牌面", cc, 0, 1.0, (200, 210, 225))]

            # 强化
            if card.enh == "bonus":
                steps_local.append(("加成牌", 30, 0, 1.0, (120, 200, 255)))
            elif card.enh == "mult":
                steps_local.append(("倍率牌", 0, 4, 1.0, (255, 140, 140)))
            elif card.enh == "glass":
                steps_local.append(("玻璃牌", 0, 0, 2.0, (150, 220, 255)))
            elif card.enh == "lucky":
                if rng.random() < 0.2:
                    steps_local.append(("幸运+倍率", 0, 20, 1.0, (255, 215, 90)))
                if rng.random() < 0.067:
                    res.money_gain += 20
                    steps_local.append(("幸运+金币", 0, 0, 1.0, (255, 215, 90)))
            elif card.enh == "gold":
                pass  # 回合结束结算

            # 小丑：逐张触发
            for j in jokers:
                v = _card_joker(j, card, weaken)
                if v:
                    steps_local.append((j.name, v[0], v[1], v[2], RARITY_COLOR[j.rarity]))

            # 版本
            if card.edition == "foil":
                steps_local.append(("闪箔", 50, 0, 1.0, (180, 200, 220)))
            elif card.edition == "holo":
                steps_local.append(("全息", 0, 10, 1.0, (180, 200, 220)))
            elif card.edition == "poly":
                steps_local.append(("多彩", 0, 0, 1.5, (180, 200, 220)))

            for _ in range(2 if card.seal == "red" else 1):
                for (lab, dc, dm, xm, col) in steps_local:
                    chips += dc
                    mult += dm
                    if xm != 1.0:
                        mult *= xm
                    res.steps.append((f"{card.name} · {lab}" if lab != "牌面" else card.name,
                                      dc, dm, xm, col))

        # 点金手
        for j in jokers:
            if j.hook == "card_goldify" and card.is_face:
                card._goldify = True

    # ---------- 手持钢铁牌 ----------
    steel_count = sum(1 for c in held if c.enh == "steel")
    for _ in range(steel_count):
        res.steps.append(("钢铁牌（手牌）", 0, 0, 1.5, (170, 190, 210)))
        mult *= 1.5

    # ---------- 牌组级小丑 ----------
    for j in jokers:
        for step in _hand_joker(j, game, played, held, ht_key, weaken, res):
            if step is None:
                continue
            dc, dm, xm = step[1], step[2], step[3]
            chips += dc
            mult += dm
            if xm != 1.0:
                mult *= xm
            res.steps.append(step)

    # ---------- Boss 修正 ----------
    if boss and boss.key == "b_wall" and game.hands_left >= game.mods["hands"] - 2:
        res.steps.append(("琥珀之墙", 0, 0, 0.5, (220, 170, 60)))
        mult *= 0.5
    if boss and boss.key == "b_needle" and game.hands_used == 0:
        res.steps.append(("绯红之针", 0, 0, 0.5, (200, 90, 120)))
        mult *= 0.5
    if boss and boss.key == "b_head" and ht_key in ("flush", "sflush"):
        res.steps.append(("苍白之首", 0, 0, 0.5, (210, 200, 190)))
        mult *= 0.5

    res.chips = int(round(chips))
    res.mult = round(mult, 2)
    res.total = int(round(chips * mult))

    # 记录牌型使用次数
    game.hand_counts[ht_key] = game.hand_counts.get(ht_key, 0) + 1

    # 成长型小丑结算
    _post_score(game, played, held, ht_key)
    return res


def _card_joker(j, card, weaken=1.0):
    """返回 (筹码增量, 倍率增量, x倍率) 或 None"""
    if j.hook == "card_suit_mult":
        if card.enh == "wild" or card.suit == j.arg[0]:
            return (0, j.arg[1] * weaken, 1.0)
    elif j.hook == "card_chips":
        return (j.arg * weaken, 0, 1.0)
    return None


def _hand_joker(j, game, played, held, ht_key, weaken=1.0, res=None):
    """返回 step 列表 (label, chips, mult, xmult, color)"""
    out = []
    col = RARITY_COLOR[j.rarity]
    rng = game.rng
    m = weaken

    def add(lab, dc=0, dm=0, xm=1.0):
        if dc or dm or xm != 1.0:
            out.append((lab, dc, dm, xm, col))

    h = j.hook
    if h is None:
        if m != 1.0:
            add(j.name, int(j.chips * m), int(j.mult * m), 1 + (j.xmult - 1) * m if j.xmult else 1.0)
        else:
            add(j.name, j.chips, j.mult, j.xmult if j.xmult else 1.0)
        return out

    if h == "hand_straight":
        if ht_key in ("straight", "sflush"):
            add(j.name, 80 * m, 0)
    elif h == "hand_random":
        v = rng.randint(0, 23)
        add(f"{j.name}（{v}）", 0, int(v * m))
    elif h == "hand_pair":
        if ht_key in ("pair", "twopair", "full", "four", "five"):
            add(j.name, int(50 * m), 0)
    elif h == "hand_three":
        if ht_key in ("three", "full", "four", "five"):
            add(j.name, 0, int(30 * m))
    elif h == "hand_high":
        if ht_key == "high":
            add(j.name, 0, int(20 * m))
    elif h == "hand_twopair":
        if ht_key == "twopair":
            add(j.name, 0, int(40 * m))
    elif h == "hand_discards_chips":
        add(j.name, int(30 * game.discards_left * m), 0)
    elif h == "hand_hands_mult":
        add(j.name, 0, int(4 * game.hands_left * m))
    elif h == "hand_nova":
        c = game.hand_counts.get(ht_key, 0)
        add(f"{j.name}（已打出 {c} 次）", 0, int(c * m))
    elif h == "hand_green":
        v = int(j.growth.get("m", 0) * m)
        if v:
            add(j.name, 0, v)
    elif h == "hand_deck_chips":
        v = len(game.deck) // 2
        add(f"{j.name}（牌库 {len(game.deck)}）", int(v * m), 0)
    elif h == "hand_ride":
        v = int(j.growth.get("m", 0) * m)
        if v:
            add(j.name, 0, v)
    elif h == "hand_space":
        v = int(j.growth.get("m", 0) * m)
        if v:
            add(j.name, 0, v)
    elif h == "hand_square" or h == "hand_exact4":
        if len(played) == 4:
            add(j.name, int(40 * m), 0)
    elif h == "hand_lasthand":
        if game.hands_left <= 1:
            add(j.name, 0, 0, 1 + (3 - 1) * m)
    elif h == "hand_joker_mult":
        n = sum(1 for x in game.jokers if x)
        add(j.name, 0, int(n * 3 * m))
    elif h == "hand_rank8":
        v = int(j.growth.get("m", 0) * m)
        if v:
            add(j.name, 0, v)
    elif h == "hand_erosion":
        v = int(j.growth.get("m", 0) * m)
        if v:
            add(j.name, 0, v)
    elif h == "hand_ice":
        v = int(j.growth.get("c", 0) * m)
        if v:
            add(j.name, v, 0)
    elif h == "hand_constel":
        x = j.growth.get("x", 1.0)
        if x > 1.0:
            add(j.name, 0, 0, 1 + (x - 1) * m)
    elif h == "hand_bull":
        v = int(j.growth.get("c", 0) * m)
        if v:
            add(j.name, v, 0)
    elif h == "hand_blackboard":
        if held and all((c.suit in BLACK_SUITS or c.enh == "wild") for c in held):
            add(j.name, 0, 0, 1 + 2 * m)
    elif h == "hand_vampire":
        x = j.growth.get("x", 1.0)
        if x > 1.0:
            add(j.name, 0, 0, 1 + (x - 1) * m)
    elif h == "hand_obelisk":
        if game.hand_counts:
            top = max(game.hand_counts.items(), key=lambda kv: kv[1])[0]
            if ht_key != top:
                add(j.name, 0, 0, 1 + 1 * m)
    elif h == "hand_cavendish":
        add(j.name, 0, 0, 1 + 2 * m)
    elif h == "hand_cardist":
        x = (1.3) ** len(played)
        add(j.name, 0, 0, 1 + (x - 1) * m)
    elif h == "hand_hologram":
        x = j.growth.get("x", 1.0)
        if x > 1.0:
            add(j.name, 0, 0, 1 + (x - 1) * m)
    elif h == "hand_thief":
        x = j.growth.get("x", 1.0)
        if x > 1.0:
            add(j.name, 0, 0, 1 + (x - 1) * m)
    elif h == "hand_emptyslot":
        empty = game.mods["joker_slots"] - sum(1 for x in game.jokers if x)
        if empty > 0:
            add(j.name, 0, 0, 1 + (1.5 ** empty - 1) * m)
    elif h == "hand_burnt":
        v = int(j.growth.get("m", 0) * m)
        if v:
            add(j.name, 0, v)
    elif h == "hand_money_mult":
        v = game.money // 5
        if v:
            add(j.name, 0, int(v * m))
    elif h == "hand_tribe":
        if len(played) >= 4:
            add(j.name, 0, 0, 1 + (2 ** (len(played) - 3) - 1) * m)
    elif h == "hand_blueprint":
        idx = game.jokers.index(j)
        if idx + 1 < len(game.jokers) and game.jokers[idx + 1]:
            other = game.jokers[idx + 1]
            sub = _hand_joker(other, game, played, held, ht_key, m, res)
            for s in sub:
                out.append((f"蓝图→{s[0]}", s[1], s[2], s[3], s[4]))
    elif h == "hand_dna":
        add(j.name, 0, 0, 1 + 0.5 * m)
    elif h == "hand_caino":
        x = j.growth.get("x", 1.0)
        if x > 1.0:
            add(j.name, 0, 0, 1 + (x - 1) * m)
    elif h == "hand_yorick":
        if j.growth.get("d", 0) >= 23:
            add(j.name, 0, 0, 1 + 0.5 * m)
    elif h == "end_money":
        pass
    return out


def _post_score(game, played, held, ht_key):
    """出牌后更新成长型小丑"""
    for j in game.jokers:
        if not j:
            continue
        h = j.hook
        if h == "hand_green":
            j.growth["m"] = j.growth.get("m", 0) + 1
        elif h == "hand_ice":
            j.growth["c"] = max(0, j.growth.get("c", 0) - 10)
            if j.growth["c"] <= 0:
                game.jokers[game.jokers.index(j)] = None
                game.log.append(f"{j.name} 融化了！")
        elif h == "hand_bull":
            j.growth["c"] = j.growth.get("c", 0) + 2
        elif h == "hand_hologram":
            j.growth["x"] = round(j.growth.get("x", 1.0) * 1.05, 3)
        elif h == "hand_ride":
            if all(c.is_face for c in played):
                j.growth["m"] = j.growth.get("m", 0) + 1
            else:
                j.growth["m"] = 0
        elif h == "hand_8ball" or h == "hand_rank8":
            j.growth["m"] = j.growth.get("m", 0) + sum(1 for c in played if c.rank == 8)
        elif h == "hand_erosion":
            j.growth["m"] = max(0, 52 - len(game.full_deck)) * 4
        elif h == "hand_vampire":
            for c in played:
                if c.enh:
                    j.growth["x"] = round(j.growth.get("x", 1.0) * 1.2, 3)
                    c.enh = ""
                    game.log.append(f"吸血鬼吸干了 {c.name}")
        elif h == "hand_dna":
            game.mods["hand_size"] += 1
        elif h == "card_goldify":
            pass


# ---------------------------------------------------------------- 游戏主体

class Game:
    """一整局（Run）的状态"""

    def __init__(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1 << 30)
        self.rng = random.Random(self.seed)
        self.log = []

        self.full_deck = make_deck()
        self.deck = []                       # 抽牌堆
        self.hand = []
        self.discard_pile = []
        self.jokers = [None] * 5
        self.consumables = []
        self.vouchers = set()

        self.mods = {
            "hands": 4,
            "discards": 4,
            "hand_size": 8,
            "joker_slots": 5,
            "consum_slots": 2,
            "interest_cap": 5,
            "reroll_cost": 5,
            "joker_mult": 0,
            "joker_chips": 0,
            "sell_bonus": 0,
        }

        self.hand_levels = {h.key: 1 for h in HAND_TYPES}
        self.hand_counts = {}

        self.money = 4
        self.ante = 1
        self.blind_index = 0                 # 0 小 / 1 大 / 2 首领
        self.blind = None
        self.boss = None
        self.target = 300
        self.score = 0

        self.hands_left = 4
        self.discards_left = 4
        self.hands_used = 0
        self.discards_used = 0

        self.destroyed = 0
        self.phase = "blind_select"
        self.game_over = False
        self.victory = False
        self.shop = None
        self.last_result = None
        self.selected = []
        self.pending_consumable = None
        self.toast = ""
        self.used_bosses = set()

        self._new_blind()

    # ---------- 盲注 ----------
    @property
    def blind_kind(self):
        return ["small", "big", "boss"][self.blind_index]

    def _new_blind(self):
        self.blind_index = 0
        self._setup_blind()

    def _setup_blind(self):
        kind = self.blind_kind
        base = ANTE_BASE[min(self.ante, FINAL_ANTE)]
        self.target = int(base * BLIND_MULT[kind])
        self.blind = {"kind": kind, "name": BLIND_CN[kind], "target": self.target}
        self.boss = None
        if kind == "boss":
            if self.ante >= FINAL_ANTE:
                self.boss = BOSS_BY_KEY["b_final"]
            else:
                pool = [b for b in NORMAL_BOSSES if b.key not in self.used_bosses]
                if not pool:
                    pool = NORMAL_BOSSES
                    self.used_bosses.clear()
                self.boss = self.rng.choice(pool)
                self.used_bosses.add(self.boss.key)
        self.score = 0
        self.phase = "blind_select"

    def start_blind(self):
        """进入一个盲注的战斗"""
        self.deck = list(self.full_deck)
        self.rng.shuffle(self.deck)
        self.hand = []
        self.discard_pile = []
        self.hands_left = self.mods["hands"]
        self.discards_left = self.mods["discards"]
        self.hands_used = 0
        self.discards_used = 0
        if self.boss and self.boss.key == "b_eye":
            self.hands_left = max(1, self.hands_left - 1)
        self.selected = []
        self.phase = "play"
        self.draw_to(self.mods["hand_size"])

    def draw_to(self, n):
        while len(self.hand) < n and self.deck:
            self.hand.append(self.deck.pop())
        if not self.deck and len(self.hand) < n:
            if self.discard_pile:
                self.deck = self.discard_pile
                self.rng.shuffle(self.deck)
                self.discard_pile = []
                while len(self.hand) < n and self.deck:
                    self.hand.append(self.deck.pop())

    # ---------- 操作 ----------
    def toggle_select(self, idx):
        if not (0 <= idx < len(self.hand)):
            return
        card = self.hand[idx]
        if card in self.selected:
            self.selected.remove(card)
        else:
            if len(self.selected) >= 5:
                return
            self.selected.append(card)

    def sort_hand(self, mode="rank"):
        suit_order = {"S": 0, "H": 1, "D": 2, "C": 3}
        if mode == "rank":
            self.hand.sort(key=lambda c: (-c.rank, suit_order[c.suit]))
        else:
            self.hand.sort(key=lambda c: (suit_order[c.suit], -c.rank))

    def play_selected(self):
        if not self.selected or self.hands_left <= 0:
            return None
        played = list(self.selected)
        held = [c for c in self.hand if c not in played]
        self.hand = held
        res = score_play(self, played, held)

        self.score += res.total
        self.money += res.money_gain
        self.hands_left -= 1
        self.hands_used += 1
        self.selected = []

        # 玻璃牌碎裂
        for c in played:
            if c.enh == "glass" and self.rng.random() < 0.25:
                c.destroyed_flag = True
                self.full_deck = [x for x in self.full_deck if x is not c]
                self.log.append(f"{c.name} 碎裂了")
                for j in self.jokers:
                    if j and j.hook == "hand_caino":
                        j.growth["x"] = round(j.growth.get("x", 1.0) * 1.4, 3)
                self.destroyed += 1
            else:
                self.discard_pile.append(c)

        # Boss 效果
        if self.boss:
            if self.boss.key == "b_hook":
                dump = min(2, len(self.hand))
                for _ in range(dump):
                    if self.hand:
                        c = self.rng.choice(self.hand)
                        self.hand.remove(c)
                        self.discard_pile.append(c)
            elif self.boss.key == "b_serpent":
                self.mods["hand_size"] = max(3, self.mods["hand_size"] - 1)

        self.draw_to(self.mods["hand_size"])
        res.played_cards = played
        self.last_result = res
        if self.score >= self.target:
            self.phase = "round_win"
        elif self.hands_left <= 0:
            self.phase = "round_lose"
        return res

    def discard_selected(self):
        if not self.selected or self.discards_left <= 0:
            return False
        for c in self.selected:
            if c in self.hand:
                self.hand.remove(c)
            self.discard_pile.append(c)
            for j in self.jokers:
                if j and j.hook == "hand_yorick":
                    j.growth["d"] = j.growth.get("d", 0) + 1
                if j and j.hook == "hand_thief":
                    j.growth["x"] = round(j.growth.get("x", 1.0) * 1.25, 3)
        self.discards_left -= 1
        self.discards_used += 1
        # 绿色小丑弃牌减益
        for j in self.jokers:
            if j and j.hook == "hand_green":
                j.growth["m"] = max(0, j.growth.get("m", 0) - 1)
        self.selected = []
        self.draw_to(self.mods["hand_size"])
        return True

    # ---------- 回合结算 ----------
    def finish_round(self):
        """回合结束（达标或失败），发放金币"""
        gain = 0
        # 手持黄金牌
        for c in self.hand:
            if c.enh == "gold":
                gain += 3
            if getattr(c, "_goldify", False):
                c.enh = "gold"
                c._goldify = False
        # 小丑收益
        for j in self.jokers:
            if j and j.hook == "end_money":
                gain += 3
        # 基础奖励 + 剩余出牌 + 利息
        base = {"small": 3, "big": 4, "boss": 5}[self.blind_kind] + self.ante
        interest = min(self.money // 5, self.mods["interest_cap"])
        gain += base + self.hands_left + interest
        self.money += gain
        self.last_gain = gain
        self.round_reward = {
            "base": base, "hands": self.hands_left,
            "interest": interest, "total": gain,
        }
        return gain

    def advance(self):
        """通过当前盲注，进入下一个"""
        self.blind_index += 1
        if self.blind_index > 2:
            self.ante += 1
            if self.ante > FINAL_ANTE:
                self.victory = True
                self.game_over = True
                self.phase = "game_over"
                return
            self.blind_index = 0
        self._setup_blind()

    def lose_run(self):
        self.game_over = True
        self.phase = "game_over"

    # ---------- 商店 ----------
    def open_shop(self):
        self.phase = "shop"
        self.shop = self.roll_shop()

    def roll_shop(self):
        owned = [j.key for j in self.jokers if j]
        joker_slots = 2 if self.ante < 4 else 3
        items = []
        for _ in range(joker_slots):
            items.append({"type": "joker", "data": random_joker(self.rng, owned), "sold": False})
        for _ in range(2):
            items.append({"type": "consum", "data": random_consumable(self.rng), "sold": False})
        avail = [v for v in VOUCHERS if v.key not in self.vouchers]
        if avail:
            items.append({"type": "voucher", "data": self.rng.choice(avail), "sold": False})
        return {"items": items, "reroll": self.mods["reroll_cost"]}

    def reroll_shop(self):
        cost = self.mods["reroll_cost"]
        if self.money < cost:
            return False
        self.money -= cost
        self.shop = self.roll_shop()
        self.shop["reroll"] = cost + 1
        return True

    def buy(self, idx):
        if not self.shop or idx >= len(self.shop["items"]):
            return False
        it = self.shop["items"][idx]
        if it["sold"]:
            return False
        d = it["data"]
        if it["type"] == "joker":
            if self.money < d.cost:
                self.toast = "金币不足"
                return False
            slot = self.free_joker_slot()
            if slot is None:
                self.toast = "小丑牌栏已满"
                return False
            self.money -= d.cost
            self.jokers[slot] = d
            it["sold"] = True
            self.toast = f"获得 {d.name}"
            return True
        if it["type"] == "consum":
            cost = 4 if d.kind == "tarot" else 4
            if self.money < cost:
                self.toast = "金币不足"
                return False
            if len(self.consumables) >= self.mods["consum_slots"]:
                self.toast = "消耗牌栏已满"
                return False
            self.money -= cost
            self.consumables.append(d)
            it["sold"] = True
            self.toast = f"获得 {d.name}"
            return True
        if it["type"] == "voucher":
            if self.money < d.cost:
                self.toast = "金币不足"
                return False
            self.money -= d.cost
            self.vouchers.add(d.key)
            d.apply_fn(self)
            it["sold"] = True
            self.toast = f"已购买 {d.name}"
            return True
        return False

    def free_joker_slot(self):
        for i in range(self.mods["joker_slots"]):
            if i >= len(self.jokers):
                self.jokers.append(None)
            if self.jokers[i] is None:
                return i
        return None

    def sell_joker(self, idx):
        j = self.jokers[idx]
        if not j:
            return False
        val = j.sell_value + self.mods["sell_bonus"]
        self.money += val
        self.jokers[idx] = None
        self.toast = f"卖出 {j.name} +{val}"
        return True

    def use_consumable(self, idx, targets):
        """targets: 选中的手牌 Card 列表"""
        if not (0 <= idx < len(self.consumables)):
            return False, "无效"
        c = self.consumables[idx]
        kind, arg = c.kind, c.arg
        if kind == "planet":
            key = c.arg
            self.hand_levels[key] = self.hand_levels.get(key, 1) + 1
            for j in self.jokers:
                if j and j.hook == "hand_space":
                    j.growth["m"] = j.growth.get("m", 0) + 3
                if j and j.hook == "hand_burnt":
                    j.growth["m"] = j.growth.get("m", 0) + 2
                if j and j.hook == "hand_constel":
                    j.growth["x"] = round(j.growth.get("x", 1.0) * 1.1, 3)
            self.consumables.pop(idx)
            self.toast = f"{HT[key].cn} 提升至 Lv.{self.hand_levels[key]}"
            return True, self.toast

        act, val, n = arg
        if act == "money":
            self.money += val
            self.consumables.pop(idx)
            self.toast = f"获得 {val} 金币"
            return True, self.toast
        if act == "fool":
            if len(self.consumables) < self.mods["consum_slots"] + 1:
                self.consumables.insert(idx, random.choice(ALL_TAROTS))
            self.consumables.pop(idx + 1)
            self.toast = "变出了一张新的塔罗牌"
            return True, self.toast

        if len(targets) < 1 and act not in ("random_enh",):
            return False, "请先选择手牌"

        if act == "enh":
            for tc in targets[:n]:
                tc.enh = val
            self.consumables.pop(idx)
            self.toast = f"强化了 {min(len(targets), n)} 张牌"
            return True, self.toast
        if act == "suit":
            for tc in targets[:n]:
                tc.suit = val
            self.consumables.pop(idx)
            self.toast = f"转换了 {min(len(targets), n)} 张牌的花色"
            return True, self.toast
        if act == "edition":
            ok = False
            for tc in targets[:n]:
                if self.rng.random() < 0.25:
                    tc.edition = self.rng.choice(["foil", "holo", "poly"])
                    ok = True
            self.consumables.pop(idx)
            self.toast = "命运之轮转动……" + ("成功了！" if ok else "什么也没发生")
            return True, self.toast
        if act == "random_enh":
            if not self.full_deck:
                return False, "没有牌可强化"
            tc = self.rng.choice(self.full_deck) if not targets else targets[0]
            tc.enh = self.rng.choice(["bonus", "mult", "wild", "glass", "steel", "lucky", "gold"])
            self.consumables.pop(idx)
            self.toast = f"{tc.name} 获得了强化"
            return True, self.toast
        if act == "destroy":
            for tc in targets[:n]:
                if tc in self.full_deck:
                    self.full_deck.remove(tc)
                if tc in self.hand:
                    self.hand.remove(tc)
                self.destroyed += 1
                for j in self.jokers:
                    if j and j.hook == "hand_caino":
                        j.growth["x"] = round(j.growth.get("x", 1.0) * 1.4, 3)
            self.consumables.pop(idx)
            self.toast = f"销毁了 {min(len(targets), n)} 张牌"
            return True, self.toast
        if act == "death":
            if len(targets) < 2:
                return False, "需要选择 2 张牌"
            src, dst = targets[0], targets[1]
            dst.rank, dst.suit = src.rank, src.suit
            if dst in self.full_deck:
                self.full_deck.remove(dst)
            if dst in self.hand:
                self.hand.remove(dst)
            self.destroyed += 1
            for j in self.jokers:
                if j and j.hook == "hand_caino":
                    j.growth["x"] = round(j.growth.get("x", 1.0) * 1.4, 3)
            self.consumables.pop(idx)
            self.toast = f"{dst.name} 变成了 {src.name}"
            return True, self.toast
        return False, "无法使用"

    # ---------- 跳过盲注 ----------
    def skip_blind(self):
        """跳过当前（小/大）盲注换取奖励；首领盲注不可跳过"""
        if self.blind_kind == "boss":
            return None
        r = self.rng.random()
        money_gain = 3 + self.ante
        self.money += money_gain
        reward = {"type": "money", "name": f"+{money_gain} 金币", "money": money_gain}
        if r < 0.35 and len(self.consumables) < self.mods["consum_slots"]:
            c = random_consumable(self.rng)
            self.consumables.append(c)
            reward = {"type": "consum", "name": c.name, "desc": c.desc, "money": money_gain}
        elif r < 0.6:
            slot = self.free_joker_slot()
            if slot is not None and self.ante >= 2:
                j = random_joker(self.rng, [x.key for x in self.jokers if x])
                self.jokers[slot] = j
                reward = {"type": "joker", "name": j.name, "desc": j.live_desc(), "money": money_gain}
        self.blind_index += 1
        if self.blind_index > 2:
            self.ante += 1
            self.blind_index = 0
            if self.ante > FINAL_ANTE:
                self.victory = True
                self.game_over = True
                self.phase = "game_over"
                return reward
        self._setup_blind()
        self.phase = "shop"
        return reward

    # ---------- 辅助 ----------
    def preview_hand(self):
        """预览当前选中牌的牌型与基础分（不含随机）"""
        if not self.selected:
            return None
        k, sc = detect_hand(self.selected)
        lv = 1 if (self.boss and self.boss.key == "b_club") else self.hand_levels.get(k, 1)
        c, m = HT[k].at(lv)
        return {"key": k, "cn": HT[k].cn, "lv": lv, "chips": c, "mult": m}

    def total_joker_bonus(self):
        chips = self.mods["joker_chips"]
        mult = self.mods["joker_mult"]
        return chips, mult

    def deck_size(self):
        return len(self.full_deck)
