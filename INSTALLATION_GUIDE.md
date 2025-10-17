🚀 BookMyMovie - Git & Heroku CLI Installation Guide
===================================================

📥 DOWNLOAD LINKS (Both should be opening automatically):
- Git for Windows: https://git-scm.com/download/windows
- Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli

🔧 INSTALLATION STEPS:

STEP 1: Install Git for Windows
===============================
1. Download should start automatically from the opened page
2. Look for "64-bit Git for Windows Setup" (or similar)
3. Run the downloaded .exe file
4. Installation Options (IMPORTANT - Use these settings):
   ✅ Use default installation directory
   ✅ Select components: Keep all default selections
   ✅ Start Menu folder: Default
   ✅ Default editor: Use default (usually Vim or Notepad++)
   ✅ Initial branch name: "main" (default)
   ✅ PATH environment: "Git from the command line and also from 3rd-party software" (RECOMMENDED)
   ✅ SSH executable: Use bundled OpenSSH
   ✅ HTTPS transport backend: Use the OpenSSL library
   ✅ Line ending conversions: Checkout Windows-style, commit Unix-style line endings
   ✅ Terminal emulator: Use MinTTY
   ✅ Default behavior of 'git pull': Default
   ✅ Credential helper: Git Credential Manager
   ✅ Extra options: Enable file system caching, Enable Git LFS support

STEP 2: Install Heroku CLI
==========================
1. On the Heroku page, scroll to find "Windows" section
2. Click "Download the Heroku CLI"
3. Run the downloaded installer
4. Installation Options:
   ✅ Use default installation directory
   ✅ Accept license agreement
   ✅ Complete installation (takes 2-3 minutes)

⚠️ IMPORTANT: After Both Installations
=====================================
1. Close ALL PowerShell windows
2. Open a NEW PowerShell window
3. Navigate back to your project: cd C:\Bookmymovie_Project
4. Test installations by running: git --version and heroku --version

✅ VERIFICATION COMMANDS:
=========================
After installation, run these to verify:

git --version
# Should show: git version 2.x.x.windows.x

heroku --version  
# Should show: heroku/8.x.x win32-x64 node-v18.x.x

🎯 NEXT STEP AFTER INSTALLATION:
================================
Once both are installed and verified:
1. Double-click "deploy_live.bat" in your project folder
OR
2. Run these commands in PowerShell:
   git init
   git add .
   git commit -m "BookMyMovie: Complete platform with 'Book Fast Feel First' branding"
   heroku login
   heroku create bookmymovie-demo
   git push heroku main

🎬 RESULT: Your "Book Fast Feel First" platform will be LIVE worldwide! 🌍

Estimated total time: 10-15 minutes for installation + 15-20 minutes for deployment = 30 minutes to go live!