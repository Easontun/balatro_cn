#!/usr/bin/env bash
# 在 WSL Ubuntu 内执行：安装 buildozer 构建链所需系统依赖、Rust、Python 包
# 不使用 set -e：某些可选包在部分镜像源里缺失，不应中断整体安装
export DEBIAN_FRONTEND=noninteractive
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

echo "===== [1/5] apt 更新 ====="
apt-get update -qq

echo "===== [2/5] 核心编译依赖（必须成功） ====="
apt-get install -y --no-install-recommends \
    git zip unzip openjdk-17-jdk python3-pip python3-venv \
    build-essential autoconf automake autopoint libtool pkg-config \
    zlib1g-dev cmake libffi-dev libssl-dev patchelf g++ ca-certificates \
    gettext curl wget lsb-release

echo "===== [3/5] 可选依赖（失败不影响） ====="
# libtinfo5 / libncurses5 在部分镜像源中不稳定，单独安装并容错
apt-get install -y --no-install-recommends libltdl-dev libncurses5-dev \
    libncursesw5-dev libtinfo5 2>&1 | tail -3 || echo "  （可选依赖部分缺失，已跳过）"

echo "===== [4/5] 安装 Rust（p4a 部分 recipe 需要） ====="
if [ ! -d "$HOME/.cargo" ]; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
fi
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

echo "===== [5/5] 安装 buildozer 与 Cython ====="
python3 -m pip install --upgrade pip setuptools wheel 2>&1 | tail -2
# Cython 必须 < 3.0：p4a 的构建脚本与 Cython 3 不兼容
python3 -m pip install --upgrade "Cython<3.0" virtualenv appdirs \
    colorama jinja2 toml packaging 2>&1 | tail -3
python3 -m pip install --upgrade buildozer 2>&1 | tail -3

echo "===== 校验 ====="
buildozer --version 2>&1 | head -3
python3 -c "import Cython; print('Cython', Cython.__version__)" 2>&1
java -version 2>&1 | head -1
echo "===== init 完成 ====="
