@echo off
chcp 65001 >nul
title 启用 WSL（用于构建 Android APK）
echo ============================================================
echo   启用 WSL —— 构建《诡牌筑局》Android APK 的前置步骤
echo ============================================================
echo.
echo 本脚本会启用两项 Windows 功能：
echo   1. 适用于 Linux 的 Windows 子系统 (WSL)
echo   2. 虚拟机平台 (VirtualMachinePlatform，WSL2 需要)
echo.
echo 完成后需要【重启电脑】一次，之后剩下的构建工作全部自动完成。
echo.
pause

echo.
echo [1/3] 启用 WSL 功能...
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] WSL 功能启用失败，错误码 %ERRORLEVEL%
    echo 请确认你是以【管理员身份】运行的本脚本。
    pause
    exit /b 1
)
echo      完成。

echo.
echo [2/3] 启用虚拟机平台...
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
echo      完成（错误码 %ERRORLEVEL%，已忽略）。

echo.
echo [3/3] 设置 WSL 默认版本为 2...
wsl.exe --set-default-version 2 >nul 2>&1
echo      完成。

echo.
echo ============================================================
echo   成功！请现在【重启电脑】。
echo.
echo   重启后回到 WorkBuddy 对话中说一声"继续"，
echo   我会自动完成：导入 Ubuntu → 安装构建链 →
echo   编译 APK（约 30-60 分钟，全程进度可见）。
echo ============================================================
echo.
pause
