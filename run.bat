@echo off
title NewsAgent — AI Tweet Generator
echo.
echo  ============================================
echo   NewsAgent - AI News Tweet Content Generator
echo  ============================================
echo.

if not exist ".env" (
    echo  [!] .env file not found!
    echo      Copy .env.example to .env and add your ANTHROPIC_API_KEY.
    echo.
    pause
    exit /b 1
)

if not exist "venv\Scripts\activate.bat" (
    echo  [*] First run — setting up virtual environment...
    python -m venv venv
    echo  [*] Installing dependencies...
    venv\Scripts\pip install -r requirements.txt --quiet
    echo  [*] Setup complete!
    echo.
)

call venv\Scripts\activate.bat
echo  [*] Running NewsAgent...
echo  [*] Scraping news + generating all tweet formats...
echo  [*] (This takes 3-8 minutes depending on number of sources)
echo.
python run.py %*

echo.
pause
