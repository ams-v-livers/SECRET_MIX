@echo off
cd /d "%~dp0\.."
echo Open http://127.0.0.1:8765 after entering your PIN.
.venv\Scripts\python local\server.py
pause
