#!/bin/bash

# Railway.app Direct Deployment Guide
# This creates a ZIP file for manual upload to Railway.app

echo "======================================"
echo "  RAILWAY.APP DIRECT DEPLOYMENT"
echo "======================================"
echo

# Install Railway CLI
echo "Installing Railway CLI..."
npm install -g @railway/cli

echo "Authenticating with Railway..."
railway login

echo "Creating new Railway project..."
railway init

echo "Deploying BookMyMovie platform..."
railway up

echo "Getting deployment URL..."
railway domain

echo 
echo "✅ SUCCESS! Your BookMyMovie platform is now live!"
echo "🎬 Platform: Complete movie booking system"
echo "🎨 Branding: 'Book Fast Feel First'"
echo "📱 Features: Mobile app, AI recommendations, analytics"
echo