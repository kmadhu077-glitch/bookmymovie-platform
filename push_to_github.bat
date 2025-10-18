@echo off
echo.
echo ================================
echo   PUSHING TO GITHUB REPOSITORY
echo ================================
echo.

REM Check if repository exists first
echo Checking GitHub repository...
git ls-remote origin > nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Repository found! Pushing files...
    git push -u origin main
    if %errorlevel% equ 0 (
        echo.
        echo ✓ SUCCESS! All 199 files pushed to GitHub
        echo ✓ Repository: https://github.com/kmadhu077/bookmymovie-platform
        echo.
        echo 🚀 Ready for Railway.app deployment!
        echo Opening Railway.app...
        start https://railway.app/new
    ) else (
        echo ❌ Push failed. Please check authentication.
        echo Try running: git push -u origin main
    )
) else (
    echo ❌ Repository not found at: https://github.com/kmadhu077/bookmymovie-platform
    echo Please create the repository on GitHub first.
    echo Opening GitHub...
    start https://github.com/kmadhu077
)

echo.
pause