@echo off
cd /d "%~dp0"
python -m pip install pyinstaller pystray pillow keyboard wordfreq
python -m PyInstaller --noconsole --onefile --clean --name LayoutSwitcher --collect-data wordfreq --collect-data langcodes switcher.py
echo.
echo Done: dist\LayoutSwitcher.exe
pause
