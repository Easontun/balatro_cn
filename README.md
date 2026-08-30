# 诡牌筑局 · Joker's Gambit

一款类《小丑牌》（Balatro）的 **Roguelike 牌组构筑**单机游戏：用扑克牌型撬动筹码，
用小丑牌把倍率滚成雪球，撑过 8 关首领盲注。

纯原创代码与美术（程序化绘制，无任何第三方素材），Python + pygame 实现，
已发布 **Windows 单文件 exe** 与 **Android APK** 两条发行链路。

---

## 一、快速开始

| 平台 | 产物 | 说明 |
|---|---|---|
| Windows | `dist/诡牌筑局.exe` | 双击即玩，约 18MB，无需安装 Python |
| Android | `bin/*.apk` | 需构建（见第三节），横屏运行，支持触摸 |

源码直接运行：
```bash
python main.py          # 需要 pip install pygame
python test_logic.py    # 逻辑自测 + 渲染冒烟
```

---

## 二、玩法

**目标**：每关有 3 个盲注（小 / 大 / 首领），每个盲注要求在有限的出牌次数内攒够
目标分数。首领盲注附带负面效果。撑过第 8 关即通关。

**得分公式**
```
得分 = (牌型筹码 + 牌面筹码 + 小丑筹码) × (牌型倍率 + 小丑倍率)
```
乘算（×N）类小丑是滚雪球的核心 —— 全局共 **43 张小丑牌**，分普通 / 罕见 / 稀有 / 传奇四档。

**流程**
```
盲注选择 → 出牌凑分 → 达标领金币 → 商店买小丑/消耗牌 → 下一盲注 → … → 第 8 关
```

**内容量**
- 10 种牌型，每种可用星球牌永久升级等级
- 8 种强化牌（加成 / 倍率 / 万能 / 玻璃 / 钢铁 / 石头 / 黄金 / 幸运）
- 3 种版本（闪箔 / 全息 / 多彩）、4 种封印
- 18 张塔罗牌、10 张星球牌、10 张优惠券（永久增益）
- 11 种首领盲注效果（禁花色、扣出牌、减半分数、失效小丑……）

**操作**

| 操作 | 键位 |
|---|---|
| 选牌 | 鼠标点击 / 数字键 1-9 |
| 出牌 | 空格 / 回车 |
| 弃牌 | D |
| 排序 | S（按点数）、A（按花色） |
| 查看牌库 | Tab |
| 菜单 | Esc |

手机端直接触摸操作，返回键唤出菜单。

---

## 三、构建 APK（三种途径）

Android 打包依赖 Linux 工具链（Android SDK/NDK），**在纯 Windows 上无法直接完成**。
本项目已备好 `buildozer.spec`，任选一条路即可。

### 途径 A：GitHub Actions 云构建（推荐，零本地环境）

1. 把整个项目推到 GitHub 仓库
2. 打标签推送：`git tag v1.0 && git push origin v1.0`
   （或在 GitHub 网页 → Actions →「构建 APK」→ Run workflow 手动触发）
3. 等待约 25~40 分钟，在 Actions 页面的 **Artifacts** 下载 APK

工作流文件：`.github/workflows/build-apk.yml`

### 途径 B：WSL2 / 本地 Ubuntu

```bash
bash build_apk.sh          # debug 版
bash build_apk.sh release  # release 版
```

### 途径 C：任意 Linux 云主机

同途径 B，或直接用 Docker 镜像 `kivy/buildozer`：
```bash
docker run --rm -v "$PWD":/home/user/hostcwd kivy/buildozer \
  android debug
```

**运行调试**（手机 USB 调试连上电脑后）
```bash
adb install -r bin/*.apk
adb logcat | grep python     # 看崩溃日志
```

---

## 四、重新打包 Windows exe

```bash
bash build_exe.sh
```
产物 `dist/诡牌筑局.exe`。

> **中文字体说明**：打包必须自带字体，不能依赖 `SysFont` 自动查找，否则界面全是方块。
> `fonts/` 下的两个字体由 `tools/build_fonts.py` 从系统 `NotoSansSC-VF.ttf` 裁剪而来
> （17MB → 2.4MB，按字重实例化 + GB2312 子集化）。若需新增生僻字，重跑该脚本即可：
> ```bash
> python tools/build_fonts.py
> ```

---

## 五、目录结构

```
balatro_cn/
├─ main.py            入口：主循环、界面状态机、输入路由
├─ gamecore.py        核心逻辑：牌型识别、计分、小丑效果、商店、盲注（不依赖 pygame）
├─ render.py          渲染层：程序化卡牌/小丑/UI，1280x720 逻辑分辨率 + 整体缩放
├─ test_logic.py      自测：牌型断言 + 200 局随机 + 60 局贪心 + 40 局智能Bot + 渲染冒烟
├─ fonts/             裁剪后的中文字体（2.4MB × 2）
├─ tools/build_fonts.py   字体裁剪工具
├─ buildozer.spec     Android 打包配置
├─ build_apk.sh       Linux 一键构建 APK
├─ build_exe.sh       Windows 重新打包 exe
└─ .github/workflows/build-apk.yml   云构建 APK
```

---

## 六、难度与平衡（自测数据）

`test_logic.py` 用三种机器人各跑数百局，验证无异常、无死循环、数值合理：

| Bot | 结果 |
|---|---|
| 随机出牌 | 200 局，绝大多数止步第 1 关 |
| 贪心出牌（选最高分牌型） | 60 局，多数止步第 1~2 关 |
| **智能 Bot**（会弃牌找牌型 + 优先买乘算小丑） | 40 局：**通关 2 局**，中位数第 4~5 关，最高单关 930 万分 |

难度曲线：中位数落在第 4~5 关、通关率约 5%，属于健康的 Roguelike 曲线 ——
真人玩家在熟悉小丑协同后通关率会明显高于 Bot（Bot 不会围绕小丑构筑出牌）。

---

## 七、已知限制

- 未做存档：关闭程序即结束当前 Run（Roguelike 单局制）
- 音效未实现（已预留 `pygame.mixer` 初始化）
- 手机竖屏会留黑边，横屏体验最佳
