@echo off
echo.
echo ==========================================
echo   BOOKMYMOVIE LIVE DEPLOYMENT SCRIPT
echo ==========================================
echo.
echo 🎬 "Book Fast Feel First" - Going Live!
echo.

REM Check if Git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Git not found! Please install Git first:
    echo 📥 https://git-scm.com/download/windows
    echo.
    pause
    exit /b 1
)

REM Check if Heroku CLI is installed
heroku --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Heroku CLI not found! Please install Heroku CLI first:
    echo 📥 https://devcenter.heroku.com/articles/heroku-cli
    echo.
    pause
    exit /b 1
)

echo ✅ Git and Heroku CLI are installed!
echo.

echo 🚀 Starting deployment process...
echo.

REM Initialize Git repository if not already done
if not exist ".git" (
    echo 📁 Initializing Git repository...
    git init
    if errorlevel 1 (
        echo ❌ Failed to initialize Git repository
        pause
        exit /b 1
    )
)

REM Add all files to Git
echo 📋 Adding all files to Git...
git add .
if errorlevel 1 (
    echo ❌ Failed to add files to Git
    pause
    exit /b 1
)

REM Commit changes
echo 💾 Committing changes...
git commit -m "BookMyMovie: Complete platform with 'Book Fast Feel First' branding - Ready for deployment"
if errorlevel 1 (
    echo ⚠️ No changes to commit or commit failed
)

REM Login to Heroku
echo 🔐 Logging into Heroku...
echo (This will open your browser for authentication)
heroku login
if errorlevel 1 (
    echo ❌ Heroku login failed
    pause
    exit /b 1
)

REM Create Heroku app
echo 🌐 Creating Heroku app...
set /p appname="Enter app name (or press Enter for 'bookmymovie-demo'): "
if "%appname%"=="" set appname=bookmymovie-demo

heroku create %appname%
if errorlevel 1 (
    echo ⚠️ App creation failed - app name might be taken
    echo Trying with random suffix...
    heroku create %appname%-%RANDOM%
    if errorlevel 1 (
        echo ❌ Failed to create Heroku app
        pause
        exit /b 1
    )
)

REM Deploy to Heroku
echo 🚀 Deploying to Heroku...
git push heroku main
if errorlevel 1 (
    echo ❌ Deployment failed
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   🎉 DEPLOYMENT COMPLETE! 🎉
echo ==========================================
echo.
echo ✅ Your BookMyMovie platform is now LIVE!
echo 🌐 View your app: heroku open
echo 📊 Check logs: heroku logs --tail
echo 📱 Share your live URL with the world!
echo.
echo 🎬 "Book Fast Feel First" - Now serving users globally! ✨
echo.

REM Open the deployed app
set /p open="Open your live app now? (y/n): "
if /i "%open%"=="y" (
    heroku open
)

pause