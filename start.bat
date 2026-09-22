@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
py -3.12 -m venv .venv
if not errorlevel 1 goto install
python -m venv .venv
if errorlevel 1 goto python_missing
:install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo GUI im Browser unter http://localhost:8081 oeffnen.
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto failed
exit /b 0
:python_missing
echo Bitte Python 3.12 installieren und dabei "Add python.exe to PATH" aktivieren.
:failed
echo Start fehlgeschlagen. Bitte die Fehlermeldung oben pruefen.
pause
exit /b 1
