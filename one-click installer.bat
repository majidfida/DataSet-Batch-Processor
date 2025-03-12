@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

:: Define the virtual environment folder
SET VENV_DIR=venv
SET PYTHON=python

:: Check if Python is installed
where %PYTHON% >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed. Please install Python and try again.
    pause
    exit /b
)

:: Create virtual environment if it doesn't exist
IF NOT EXIST %VENV_DIR% (
    echo Creating virtual environment...
    %PYTHON% -m venv %VENV_DIR%
)

:: Activate virtual environment
CALL %VENV_DIR%\Scripts\activate

:: Upgrade pip and install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

:: Create necessary folders
mkdir input_images 2>nul
mkdir output_folder 2>nul

:: Run the application
echo Starting the application...
python start_app.py

:: Keep the window open
pause
