@echo off
echo ===================================================
echo   INSTALLING PYTORCH WITH CUDA 12.1 (NVIDIA GPU)
echo ===================================================
echo.
echo 1. Uninstalling existing torch versions...
python -m pip uninstall -y torch torchvision torchaudio
echo.
echo 2. Downloading & Installing PyTorch CUDA 12.1...
echo    (Ini mungkin memakan waktu karena file ~2.5 GB)
echo.
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
echo.
echo 3. Verifying installation...
python -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('GPU Name:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
echo.
echo ===================================================
echo   SELESAI! Silakan restart aplikasi.
echo ===================================================
pause
