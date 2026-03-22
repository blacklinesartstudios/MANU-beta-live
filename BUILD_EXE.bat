@echo off
title 💙 Manubeta — Building .exe
color 0B
echo.
echo  ╔══════════════════════════════════════╗
echo  ║   💙 Manubeta — Building .exe        ║
echo  ║   This takes 3-4 minutes             ║
echo  ╚══════════════════════════════════════╝
echo.
echo  Step 1: Installing packages...
pip install pyinstaller mss pillow requests pystray -q
echo  ✅ Packages ready
echo.
echo  Step 2: Building Manubeta.exe...
echo  (Do NOT close this window)
echo.
pyinstaller --onefile --windowed --noconsole ^
  --name "Manubeta" ^
  --icon NONE ^
  manubeta_app.py
echo.
echo  ✅ DONE! Your Manubeta.exe is in the 'dist' folder!
echo.
echo  ══════════════════════════════════════
echo  HOW TO USE:
echo  1. Open 'dist' folder
echo  2. Double-click Manubeta.exe
echo  3. Look for 💙 in your system tray (bottom-right)
echo  4. Right-click the icon to open/close/analyze
echo  ══════════════════════════════════════
echo.
pause
