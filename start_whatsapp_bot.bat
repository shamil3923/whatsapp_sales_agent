@echo off
echo 🤖 Starting WhatsApp Sales Agent with ngrok
echo ==========================================

echo.
echo Step 1: Starting WhatsApp Bot...
echo ✅ Bot will run on http://localhost:5000
echo ✅ Keep this window open!
echo.
echo After the bot starts:
echo 1. Open a NEW terminal
echo 2. Navigate to your ngrok folder
echo 3. Run: ngrok http 5000
echo 4. Copy the HTTPS URL
echo 5. Configure webhook in Meta Console
echo.
echo Starting bot in 3 seconds...
timeout /t 3 /nobreak >nul

echo.
echo 🚀 WhatsApp Sales Agent Starting...
echo ==========================================
python whatsapp_integration.py

pause
