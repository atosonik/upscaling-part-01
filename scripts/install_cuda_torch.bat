@echo off
cd /d "%~dp0\.."
echo Downloading CUDA PyTorch wheel with resume...
if not exist .cache mkdir .cache
curl.exe -L --fail --retry 30 --retry-all-errors --retry-delay 2 -C - -o .cache\torch-2.6.0+cu124-cp312-cp312-win_amd64.whl "https://download.pytorch.org/whl/cu124/torch-2.6.0%%2Bcu124-cp312-cp312-win_amd64.whl"
if errorlevel 1 (
  echo Wheel download failed. You can run this script again to resume.
  exit /b 1
)
call venv\Scripts\python.exe -m pip install --force-reinstall .cache\torch-2.6.0+cu124-cp312-cp312-win_amd64.whl
call venv\Scripts\python.exe -m pip install torchvision --index-url https://download.pytorch.org/whl/cu124
echo CUDA PyTorch install finished.
venv\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu')"
