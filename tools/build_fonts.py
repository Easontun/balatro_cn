# -*- coding: utf-8 -*-
"""
把 17MB 的可变字体 NotoSansSC-VF.ttf 裁剪成 ~3MB 的静态小字体：
  - 先按字重实例化（Regular 400 / Bold 700）
  - 再按字符集子集化（GB2312 全部汉字 + 拉丁 + 界面符号）
生成的 fonts/NotoSansSC-Regular.ttf / -Bold.ttf 会被 render.py 优先加载。
"""
import os
import sys
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.path.join(ROOT, "fonts")


def build_charset():
    chars = []
    # 1) ASCII 可打印
    chars += [chr(c) for c in range(0x20, 0x7F)]
    # 2) 拉丁补充 + 常用标点
    chars += [chr(c) for c in range(0xA0, 0x100)]
    # 3) 通用标点 / 货币 / 数学符号 / 箭头 / 几何 / 杂项符号
    for a, b in [(0x2000, 0x206F), (0x20A0, 0x20BF), (0x2100, 0x214F),
                 (0x2190, 0x21FF), (0x2200, 0x22FF), (0x2460, 0x24FF),
                 (0x2500, 0x257F), (0x25A0, 0x25FF), (0x2600, 0x26FF),
                 (0x2700, 0x27BF), (0x2B00, 0x2BFF)]:
        chars += [chr(c) for c in range(a, b + 1)]
    # 4) CJK 标点 / 假名 / 全角
    for a, b in [(0x3000, 0x303F), (0x3040, 0x309F), (0x30A0, 0x30FF),
                 (0xFF00, 0xFFEF)]:
        chars += [chr(c) for c in range(a, b + 1)]
    # 5) GB2312 全部汉字（6763 个，覆盖 99.9% 日常用字）
    n = 0
    for hi in range(0xB0, 0xF8):
        for lo in range(0xA1, 0xFF):
            try:
                ch = bytes([hi, lo]).decode("gb2312")
                chars.append(ch)
                n += 1
            except Exception:
                pass
    print(f"  GB2312 汉字：{n}")
    # 6) 额外常用字（GB2312 未收录的高频字）
    chars += list("〇〇瞭啰嘿喔嗯嘛呗嘞")
    # 7) 代码里出现过的所有字符（保底）
    for f in glob.glob(os.path.join(ROOT, "*.py")):
        with open(f, "r", encoding="utf-8") as fh:
            chars += [c for c in fh.read()]
    return "".join(sorted(set(chars)))


def main():
    src = None
    for cand in ["NotoSansSC-VF.ttf", "NotoSansSC-Regular.ttf", "msyh.ttc"]:
        p = os.path.join(FONTS, cand)
        if os.path.exists(p):
            src = p
            break
    if src is None:
        print("未找到源字体，跳过裁剪（将使用系统字体）")
        return 1

    from fontTools.ttLib import TTFont
    from fontTools import subset
    from fontTools.varLib import instancer

    print(f"源字体：{os.path.basename(src)}  "
          f"{os.path.getsize(src)/1048576:.1f}MB")
    chars = build_charset()
    print(f"目标字符集：{len(set(chars))} 个字形")

    is_var = "fvar" in TTFont(src, lazy=True)
    out_files = []

    for tag, weight in [("Regular", 400), ("Bold", 700)]:
        out = os.path.join(FONTS, f"NotoSansSC-{tag}.ttf")
        tmp_inst = os.path.join(FONTS, f"_inst_{tag}.ttf")
        cur = src
        if is_var:
            f = TTFont(src)
            try:
                instancer.instantiateVariableFont(f, {"wght": weight}, inplace=True,
                                                  updateFontNames=True)
                f.save(tmp_inst)
                cur = tmp_inst
                print(f"  已实例化字重 wght={weight}")
            except Exception as e:
                print(f"  实例化失败（{e}），改用原字体")
                cur = src
        opts = subset.Options()
        opts.layout_features = ["*"]
        opts.notdef_outline = True
        opts.drop_tables += ["DSIG"]
        opts.name_IDs = [1, 2, 3, 4, 6]
        opts.name_legacy = True
        opts.recalc_bounds = True
        fs = subset.load_font(cur, opts)
        subsetter = subset.Subsetter(options=opts)
        subsetter.populate(text=chars)
        subsetter.subset(fs)
        subset.save_font(fs, out, opts)
        try:
            if os.path.exists(tmp_inst):
                os.remove(tmp_inst)
        except Exception:
            pass
        size = os.path.getsize(out) / 1048576
        print(f"  生成 NotoSansSC-{tag}.ttf  {size:.2f}MB")
        out_files.append(out)
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
