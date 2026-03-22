@echo off
title 💙 Manubeta Trading Assistant
color 0B
echo.
echo  💙 Manubeta Starting...
echo  Look for the icon in your system tray (bottom-right corner)
echo.
pip install mss pillow requests pystray -q 2>nul
python manubeta_app.py
pause
