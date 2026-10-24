@echo off
echo Starting Layout-Preserving OCR Project...
echo [1/2] Starting Django Backend on http://127.0.0.1:8000...
start "OCR Backend (Django)" cmd /k "cd /d %~dp0 && env\Scripts\python.exe backend\manage.py runserver"

echo [2/2] Starting Vite Frontend on http://localhost:5173...
start "OCR Frontend (Vite)" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo Done! Backend and Frontend servers are running.
pause
