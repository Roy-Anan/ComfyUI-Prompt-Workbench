@echo off
chcp 65001 >nul
title ComfyUI Prompt Workbench
cd /d "%~dp0"

REM 优先用 ComfyUI 秋叶包自带的 Python（保证能跑，且不用另外装）
set "PYEXE=D:\AI\Qiuye\ComfyUI-aki-v3.2\python\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

echo 正在启动工作台（仅本机 127.0.0.1）...
"%PYEXE%" "%~dp0app\server.py" --open-browser
if errorlevel 1 pause
