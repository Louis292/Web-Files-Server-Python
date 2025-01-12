@echo off
REM Vérifie si pip est installé
python -m pip --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Pip n'est pas installé. Veuillez installer pip avant de continuer.
    exit /b 1
)

REM Vérifie si tous les packages dans requirements.txt sont installés
for /f "delims=" %%i in (requirements.txt) do (
    pip show %%i >nul 2>&1
    IF %ERRORLEVEL% NEQ 0 (
        echo Le package %%i n'est pas installé. Installation en cours...
        pip install %%i
    )
)

REM Exécute app.py
echo Tous les packages sont installés. Lancement de app.py...
python app.py
