@echo off
chcp 936 >nul
setlocal
cd /d "%~dp0"
set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo [工作台] 未找到项目独立 Python 环境 .venv，无法启动。
  pause
  exit /b 1
)
"%PYTHON%" scripts\workbench_launcher.py
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo [工作台] 启动未成功，错误代码 %EXITCODE%。
  pause
)
endlocal
exit /b %EXITCODE%
