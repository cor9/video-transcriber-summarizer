# Project Context

Project: VidScribe2AI - AI Video Transcription & Summarization Platform
Goal: Transform any video/audio into structured summaries with AI-powered transcription using AssemblyAI and Anthropic Claude

## Pipelines
- User uploads video/audio URL → AssemblyAI transcription → Anthropic Claude summarization → Formatted HTML output
- Direct media file URLs (MP4, MP3, WAV, etc.) supported
- YouTube URLs require pre-processing (download audio first)

## Constraints
- Vercel serverless environment (no persistent storage)
- AssemblyAI doesn't support YouTube URLs directly
- Must use compatible Python packages for serverless deployment
- HTML-only output with inline CSS styling

## Open Issues (update daily)
- [x] Vercel deployment crashes (FIXED - removed conflicting app.py)
- [x] YouTube URL support (FIXED - clear error messaging with alternatives)
- [x] Static asset loading (FIXED - proper vercel.json routing)
- [x] API key configuration (FIXED - environment variables working)
- [x] Template rendering issues (FIXED - embedded HTML directly)
- [x] Enhanced YouTube transcript functionality (FIXED - added pagination and better error handling)
- [x] Vercel Analytics integration (FIXED - added comprehensive user tracking)
- [x] Build compatibility issues (FIXED - resolved dependency conflicts)

---

# Current Implementation Context (2025-01-12)

## What's Actually Built
- Flask application deployed on Vercel as serverless function
- Direct HTML embedding (no template files) to avoid path issues
- AssemblyAI integration for video/audio transcription
- Anthropic Claude integration for AI summarization
- Beautiful dark gradient UI with sitelogo.svg branding
- Comprehensive error handling and user guidance
- Enhanced YouTube transcript functionality with pagination support
- Vercel Analytics integration for user behavior tracking
- Multiple input modes: YouTube URL, Paste Transcript, Upload SRT/VTT
- Advanced error handling with helpful suggestions and fallback options

## Key Components Working
- Main page loads successfully (200 OK)
- Health endpoint reports API key status
- Transcribe endpoint processes direct media URLs
- Static assets (favicon.ico, sitelogo.svg) load properly
- YouTube URL detection with helpful error messages
- Multiple summary formats (bullet points, key insights, detailed)
- Auto-deployment from GitHub commits
- Enhanced YouTube transcript API with pagination (/api/youtube/transcript)
- Video information endpoint (/api/youtube/info)
- Vercel Analytics tracking user interactions and errors
- Comprehensive error handling with actionable suggestions

## Recent Fixes Applied
- Removed conflicting app.py file that was causing Vercel crashes
- Added missing request import to Flask app
- Implemented proper YouTube URL detection and user guidance
- Updated UI messaging to be accurate about supported formats
- Enhanced error handling with structured responses and suggestions
- Fixed static asset serving through vercel.json routing
- Added enhanced YouTube transcript functionality with pagination
- Integrated Vercel Analytics for comprehensive user tracking
- Resolved Vercel build issues with dependency compatibility
- Improved error messages with helpful suggestions and fallback options

## Architecture Decision Needed
- Consider adding YouTube audio extraction service for better UX
- Evaluate adding user authentication for saved transcripts
- Consider adding batch processing capabilities
