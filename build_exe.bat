@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Building onedir dist\Lumina\Lumina.exe ...
python -m PyInstaller --noconfirm --clean Lumina.spec
if errorlevel 1 (
  echo PyInstaller failed.
  exit /b 1
)
echo Packing portable zip and splitting into runableparts\ ...
python pack_app.py
echo.
echo Run: dist\Lumina\Lumina.exe
echo Split/merge: python chunker.py merge --parts runableparts
echo              python pack_app.py --unpack
