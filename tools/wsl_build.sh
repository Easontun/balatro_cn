#!/usr/bin/env bash
# 在 WSL Ubuntu 内执行：把源码拷到 WSL 原生 ext4 文件系统（编译速度远快于 /mnt/c），
# 然后运行 buildozer 构建 APK，日志实时写入 /root/buildozer.log
export DEBIAN_FRONTEND=noninteractive
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

SRC=/mnt/c/Users/tuntun/WorkBuddy/2026-08-30-11-38-15/balatro_cn
DST=/root/balatro_cn

echo "===== [1/3] 拷贝源码到 WSL 原生文件系统 ====="
rm -rf "$DST"
mkdir -p "$DST"
# 用 tar 而非 rsync：tar 是基线工具，必定存在
tar -cf - -C "$SRC" \
    --exclude='./.git' \
    --exclude='./.buildozer' \
    --exclude='./bin' \
    --exclude='./build' \
    --exclude='./dist' \
    --exclude='./__pycache__' \
    --exclude='./.wsl_assets' \
    --exclude='./shots' \
    --exclude='./build_log.txt' \
    --exclude='./.workbuddy' \
    . | tar -xf - -C "$DST"
echo "  已拷贝文件："
find "$DST" -maxdepth 2 -type f | head -20
echo "  字体："
ls -lh "$DST/fonts/" 2>&1

cd "$DST"
echo "===== [2/3] buildozer android debug（日志：/root/buildozer.log） ====="
echo "  首次构建需下载 Android SDK/NDK（约 1.5GB），之后交叉编译，请耐心等待。"
buildozer -v android debug 2>&1 | tee /root/buildozer.log
BUILD_RC=${PIPESTATUS[0]}

echo "===== [3/3] 构建结束（buildozer 退出码=$BUILD_RC） ====="
ls -lh "$DST/bin/" 2>&1 || echo "  bin/ 目录不存在"
if [ $BUILD_RC -ne 0 ]; then
    echo "----- 日志最后 40 行（定位失败原因） -----"
    tail -40 /root/buildozer.log
fi
exit $BUILD_RC
