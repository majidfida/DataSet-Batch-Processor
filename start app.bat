@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

:: Activate virtual environment
CALL venv\Scripts\activate

:: Start the Python application
echo Starting DataSet Batch Processor...
python start_app.py

:: Keep the window open
pause