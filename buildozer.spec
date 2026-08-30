[app]

# 应用名称（显示在安装界面与桌面上）
title = 诡牌筑局

# 包名与域名（只能使用小写字母、数字、下划线）
package.name = jokersgambit
package.domain = org.joker.gambit

# 源码目录：构建时会把这些文件打包进 APK
source.dir = .
source.include_exts = py,png,jpg,jpeg,ttf,otf,json,txt
# 注意：include_patterns 一旦非空，就只有匹配的文件会被纳入构建。
# 因此必须显式包含 *.py，否则游戏源码会被整个排除。
# 17MB 的原始可变字体 NotoSansSC-VF.ttf 未列入，故不会打进 APK。
source.include_patterns = *.py,fonts/NotoSansSC-Regular.ttf,fonts/NotoSansSC-Bold.ttf
source.exclude_patterns = fonts/NotoSansSC-VF.ttf
source.exclude_exts = spec,md,sh,yml,yaml
source.exclude_dirs = dist,build,bin,.buildozer,.github,tools,.workbuddy,__pycache__

# 版本
version = 1.0
numeric_version = 1

# 依赖：pygame-ce 是 pygame 的活跃社区版，API 完全兼容
# 不锁定精确版本：p4a 的 python3 recipe 只接受白名单内的版本号，
# 写错会在解析需求时立刻失败，交给 p4a 使用默认版本最稳。
# pygame-ce 通过自定义 recipe（p4a-recipes/pygame-ce）以 SDL2 方式交叉编译
requirements = python3,pygame-ce
p4a.recipes = p4a-recipes

# 启动入口
# p4a 会寻找该文件并作为 APK 主程序运行
# （main.py 中已做 Android 适配：自动全屏、横屏、返回键、触摸事件去重复）

# 屏幕方向：本游戏按 1280x720 横屏设计
orientation = landscape
fullscreen = 1

# Android 配置
android.api = 35
android.minapi = 26
android.target = 35
android.archs = arm64-v8a
android.permissions =
android.allow_backup = True
android.accept_sdk_license = True

# p4a 分支（master 对高版本 Android API 支持更好）
p4a.branch = master

# 应用图标与启动图（可选，放到项目根目录后取消注释）
# icon.filename = icon.png
# presplash.filename = presplash.png
# presplash.color = #1b0f1e

# 日志
log_level = 2

[buildozer]
# 构建缓存目录，首次构建会下载 Android SDK/NDK（约 1.5GB）
build_dir = ./.buildozer
bin_dir = ./bin
warn_on_root = 1
