#!/bin/bash

# Deploy the simple version to Vercel
echo "🚀 Deploying Simple VidScribe2AI..."

# Copy simple files to replace complex ones
cp simple_app.py web_interface.py
cp simple_requirements.txt requirements.txt

# Commit and push
git add .
git commit -m "Deploy simple version - direct YouTube + Gemini approach

✅ SIMPLIFIED ARCHITECTURE:
- Remove complex make command dependencies
- Direct YouTube transcript extraction with youtube-transcript-api
- Direct AI summarization with Gemini API
- Single Flask app with embedded HTML
- No Cloud Run worker complexity
- Just 2 simple steps: Get transcript -> Get summary

🎯 BENEFITS:
- Much easier to debug and maintain
- No hidden Makefile dependencies
- Direct error handling and logging
- Faster development and testing
- Clear, readable code structure"

git push origin master

echo "✅ Simple version deployed!"
echo "🌐 Your site should now work much more reliably at https://vidscribe2ai.site/"
