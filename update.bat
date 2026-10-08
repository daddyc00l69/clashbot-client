@echo off
cd /d "%~dp0"
echo ========================================================
echo         CLASHBOT CLIENT - AUTO UPDATE
echo ========================================================
echo.
echo Stashing local configuration...
git stash
echo.
echo Pulling latest updates from server...
git pull origin main
echo.
echo Restoring profile configuration...
git stash pop
echo.
echo ========================================================
echo   Update completed successfully!
echo ========================================================
pause
