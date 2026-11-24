@echo off
cd /d "%~dp0\.."
py -3.10 -m venv .venv || goto fail
.venv\Scripts\python -m pip install --upgrade pip || goto fail
.venv\Scripts\python -m pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121 || goto fail
.venv\Scripts\python -m pip install -r local\requirements.txt || goto fail
call npm install || goto fail
echo Setup complete. Run local\start.bat.
pause
exit /b 0
:fail
echo Setup failed. Check the error above.
pause
exit /b 1
