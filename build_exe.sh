#!/usr/bin/env bash
# ============================================================
#  重新打包 Windows 单文件 exe
#  在 Git Bash 中运行： bash build_exe.sh
#  注意：--add-data 用分号分隔（Windows 规范），且必须加引号
# ============================================================
set -e

PYI="C:/Users/tuntun/.workbuddy/binaries/python/envs/default/Scripts/pyinstaller.exe"
if [ ! -f "$PYI" ]; then
  PYI="$(command -v pyinstaller || echo pyinstaller)"
fi

rm -rf dist build __pycache__ 2>/dev/null || true
mkdir -p dist

"$PYI" --onefile --windowed --noconfirm --clean \
  --name "诡牌筑局" \
  --add-data "fonts/NotoSansSC-Regular.ttf;fonts" \
  --add-data "fonts/NotoSansSC-Bold.ttf;fonts" \
  --exclude-module numpy \
  --exclude-module matplotlib \
  --exclude-module PIL \
  main.py

echo
echo ">>> 产物：dist/诡牌筑局.exe"
ls -lh dist/*.exe 2>/dev/null || true
