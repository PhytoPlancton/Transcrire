@echo off
rem Double-clic pour lancer Transcrire sur Windows.
rem Premier lancement : installe Whisper dans .venv et telecharge le modele (1,6 Go).
cd /d "%~dp0"

set "PY=python"
where py >nul 2>nul && set "PY=py -3"

if not exist ".venv\Scripts\python.exe" (
  echo Premier lancement : installation de Whisper, une a deux minutes...
  %PY% -m venv .venv || goto :err
  ".venv\Scripts\python.exe" -m pip install --upgrade pip -q
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :err
)

set "MODEL_DIR=%USERPROFILE%\whisper-turbo"
set "HF=https://huggingface.co/mobiuslabsgmbh/faster-whisper-large-v3-turbo/resolve/main"
if defined WHISPER_MODEL goto :run
if exist "%MODEL_DIR%\ok.txt" goto :model_ok
echo Telechargement du modele Whisper, 1,6 Go, une seule fois...
if not exist "%MODEL_DIR%" mkdir "%MODEL_DIR%"
for %%f in (config.json preprocessor_config.json tokenizer.json vocabulary.json model.bin) do (
  curl.exe -L -# -C - -o "%MODEL_DIR%\%%f" "%HF%/%%f" || goto :err
)
echo ok> "%MODEL_DIR%\ok.txt"
:model_ok
set "WHISPER_MODEL=%MODEL_DIR%"

:run
".venv\Scripts\python.exe" transcrire.py
goto :eof

:err
echo.
echo Une erreur est survenue. Fais une capture de cette fenetre.
pause
