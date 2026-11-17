@echo off
title comfyui-prompt assistant
REM Launch local Ollama prompt assistant; entry comfyui-prompt:v1 from Modelfile.qwen3-comfyui.
REM Rules and model index are built in; paste current model profile then describe the image.
"C:\Users\<你的用户名>\AppData\Local\Programs\Ollama\ollama.exe" run comfyui-prompt:v1
echo.
echo [session ended] Press any key to close this window.
pause >nul
