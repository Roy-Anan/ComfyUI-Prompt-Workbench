@echo off
chcp 936 >nul
setlocal
cd /d "%~dp0"
set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo [工作台] 未找到项目独立 Python 环境 .venv。
  pause
  exit /b 1
)
"%PYTHON%" scripts\workbench_stopper.py
pause
endlocal
