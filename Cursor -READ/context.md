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
- [x] Deprecated Gemini SDK (FIXED - upgraded to google-genai with chunked summarization)
- [x] Token budget issues with long videos (FIXED - implemented map-reduce chunking)
- [x] MCP server deployment issues (FIXED - local-first approach with fallback)
- [x] Flask-CORS dependency missing (FIXED - added Flask-Cors==4.0.1)
- [x] Vercel configuration conflicts (FIXED - proper functions format with bot protection)

---

# Current Implementation Context (2025-01-17)

## What's Actually Built
- Flask application deployed on Vercel as serverless function (api/index.py)
- New Google Gen AI SDK (google-genai) with gemini-2.5-flash model
- Chunked map-reduce summarization for long videos (160k char limit, 12k chunks)
- Local-first YouTube transcript fetching with MCP server fallback
- Direct HTML embedding (no template files) to avoid path issues
- Beautiful dark gradient UI with sitelogo.svg branding
- Comprehensive error handling with specific failure type messages
- CORS-enabled Flask app with bot protection routes
- Multiple language probing for transcripts (auto, en, en-US, en-GB)
- Configurable environment variables for model, limits, and server URLs
- Cursor MCP integration for development workflow

## Key Components Working
- Main page loads successfully (200 OK) with Gemini model info display
- YouTube transcript fetching with local-first approach and MCP fallback
- Chunked summarization handles long videos without token budget issues
- Static assets (favicon.ico, sitelogo.svg) load properly with bot protection
- YouTube URL detection with specific error messages for different failure types
- Map-reduce summarization for videos longer than 12k characters
- Auto-deployment from GitHub commits with proper Vercel functions format
- CORS-enabled endpoints for cross-origin requests
- Environment variable configuration for model selection and limits
- Cursor MCP integration for development transcript fetching
- Comprehensive error handling with actionable suggestions

## Recent Fixes Applied
- Upgraded from deprecated google.generativeai to new google-genai SDK
- Implemented chunked map-reduce summarization for long videos (160k char limit)
- Switched to gemini-2.5-flash model with configurable environment variables
- Added local-first transcript fetching with MCP server fallback
- Enhanced error handling with specific messages for different failure types
- Fixed Flask-CORS dependency missing (added Flask-Cors==4.0.1)
- Resolved Vercel configuration conflicts with proper functions format
- Added bot protection routes (204 status for favicon/robots.txt/sitemap.xml)
- Implemented CORS with permissive origins for cross-origin requests
- Added Cursor MCP integration for development workflow
- Created comprehensive setup guide with usage examples and troubleshooting

## Architecture Decisions Made
- ✅ **Local-First Transcript Fetching**: Prioritize youtube-transcript-api over external MCP servers for reliability
- ✅ **Chunked Summarization**: Implement map-reduce approach to handle long videos without token budget issues
- ✅ **Modern SDK**: Use google-genai instead of deprecated google.generativeai
- ✅ **Bot Protection**: Add 204 routes for common bot requests to prevent unnecessary cold starts
- ✅ **CORS Integration**: Enable cross-origin requests with permissive origins
- ✅ **Development Workflow**: Integrate Cursor MCP for direct transcript fetching during development

## Future Considerations
- Consider adding YouTube audio extraction service for better UX
- Evaluate adding user authentication for saved transcripts
- Consider adding batch processing capabilities
- Monitor token usage and adjust chunk sizes based on actual usage patterns

### Environment notes
- Python: 3.11 (Vercel functions runtime)
- Flask: 3.0.3
- Flask-Cors: 4.0.1
- google-genai: 0.5.0 (new SDK)
- youtube-transcript-api: 0.6.2
- requests: 2.32.3
- Hosting: Vercel serverless functions (api/index.py)
- Domain: vidscribe2ai.site
- Model: gemini-2.5-flash (configurable via GEMINI_MODEL env var)

### Known resolutions to reference
- Vercel 500 errors → solved by proper functions format and Flask-CORS dependency
- Token budget issues → solved by chunked map-reduce summarization
- MCP server failures → solved by local-first transcript fetching approach
- Deprecated SDK → solved by upgrading to google-genai
- Bot requests causing cold starts → solved by 204 status routes
