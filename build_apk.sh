#!/usr/bin/env bash
# ============================================================
#  在 Linux / WSL2 / 云主机上一键构建 APK
#  用法：  bash build_apk.sh           # 构建 debug 版
#          bash build_apk.sh release   # 构建带签名的 release 版
#  首次运行约 25~40 分钟（需下载 Android SDK/NDK 约 1.5GB）
# ============================================================
set -e
MODE="${1:-debug}"

echo ">>> 1/3 安装系统依赖"
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y --no-install-recommends \
    git zip unzip openjdk-17-jdk-headless \
    autoconf automake libtool pkg-config \
    zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 \
    cmake libffi-dev libssl-dev libltdl-dev \
    libsqlite3-dev libbz2-dev liblzma-dev python3-pip python3-venv
else
  echo "    非 Debian 系发行版，请自行安装 openjdk-17 / build-essential / zlib 开发包"
fi

echo ">>> 2/3 安装 Buildozer"
python3 -m pip install --upgrade pip
python3 -m pip install "cython<3.1" buildozer

echo ">>> 3/3 构建 APK ($MODE)"
if [ "$MODE" = "release" ]; then
  buildozer -v android release
  echo ">>> release 构建完成，请用 apksigner 或 buildozer 的 keystore 配置签名"
else
  yes | buildozer -v android debug
fi

echo
echo ">>> 完成，产物位于 bin/ 目录："
ls -lh bin/*.apk 2>/dev/null || echo "    未找到 apk，请查看上方日志"
