@echo off
where ffmpeg >nul 2>nul || (echo Install FFmpeg and add it to PATH. & pause & exit /b 1)
if "%~1"=="" (echo Drag a WAV file onto this script. & pause & exit /b 1)
ffmpeg -n -i "%~1" -codec:a libmp3lame -b:a 192k "%~dpn1.mp3"
pause
