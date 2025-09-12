# CONTROL.md

Cursor, you must obey this file at all times.

You are required to:
1. **Read CONTROL.md, context.md, and DECISIONS.md at the start of every session.**
2. **Summarize the last 3–5 entries from DECISIONS.md** aloud before proposing anything new.
3. **Check context.md** before guessing project details.
4. **Append to DECISIONS.md** every time an issue is resolved or a choice is made.
5. **Use the correct date.** Always print today’s date in `YYYY-MM-DD` format and wait for my confirmation before logging.
6. **Follow all Commandments (below).**

---

## SECTION 1: COMMANDMENTS (rules.md)

1. **Read the docs.** Quote relevant sections before suggesting commands.
2. **Do not spin in circles.** If an attempt fails, explain *why* and wait.
3. **Output commands cleanly.** Show terminal commands only, in code blocks.
4. **Verify before improvising.** Summarize the plan in one sentence, wait for approval.
5. **Apologize only once.** Then move forward.
6. **Assume minimal context.** Restate what you know before guessing.
7. **Keep logs short.** Show only relevant output unless asked otherwise.
8. **Stop at errors.** Don’t blindly rerun variants.
9. **Confirm success criteria.** Define “what success looks like” before running.
10. **Follow my lead.** Drop ideas I reject; don’t sneak them back later.
11. **Do not delegate what you can do faster.** Run/fetch trivial tasks yourself.

---

## SECTION 2: LOGGING RULES (DECISIONS.md)

- **Autologging required:** After each resolved issue or decision, propose a new entry for DECISIONS.md and wait for approval. Then append.
- **Date rule:** Always print today’s date (YYYY-MM-DD) and wait for my confirmation before logging.
- **Never overwrite.** Only append new entries. Preserve history.

### Entry Template
```markdown
## YYYY-MM-DD
**Issue:** [short description]
**Decision:** [what was done/decided]
**Status:** [Success / Pending / Blocked]
```

---

## SECTION 3: CONTEXT (context.md)

Cursor must consult `context.md` before making assumptions. Keep it current.

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

---

# Current Implementation Context (2025-01-12)

## What's Actually Built
- Flask application deployed on Vercel as serverless function
- Direct HTML embedding (no template files) to avoid path issues
- AssemblyAI integration for video/audio transcription
- Anthropic Claude integration for AI summarization
- Beautiful dark gradient UI with sitelogo.svg branding
- Comprehensive error handling and user guidance

## Key Components Working
- Main page loads successfully (200 OK)
- Health endpoint reports API key status
- Transcribe endpoint processes direct media URLs
- Static assets (favicon.ico, sitelogo.svg) load properly
- YouTube URL detection with helpful error messages
- Multiple summary formats (bullet points, key insights, detailed)
- Auto-deployment from GitHub commits

## Recent Fixes Applied
- Removed conflicting app.py file that was causing Vercel crashes
- Added missing request import to Flask app
- Implemented proper YouTube URL detection and user guidance
- Updated UI messaging to be accurate about supported formats
- Enhanced error handling with structured responses and suggestions
- Fixed static asset serving through vercel.json routing

## Architecture Decision Needed
- Consider adding YouTube audio extraction service for better UX
- Evaluate adding user authentication for saved transcripts
- Consider adding batch processing capabilities

### Environment notes
- Python: 3.9 (Vercel default)
- Flask: 2.3.3
- AssemblyAI: 0.21.0
- Anthropic: 0.3.11 (pinned for compatibility)
- httpx: 0.24.1 (pinned for compatibility)
- Hosting: Vercel serverless functions
- Domain: vidscribe2ai.site

### Known resolutions to reference
- Vercel 500 errors → solved by removing conflicting app.py and using api/index.py structure
- Anthropic compatibility → solved by pinning anthropic==0.3.11 and httpx==0.24.1
- Template rendering → solved by embedding HTML directly in Flask route
- Static assets 404 → solved by proper vercel.json routing configuration

---

## SECTION 4: EMERGENCY BRAKES

- **Spiral reset:** `STOP. Summarize plan in one sentence. Wait for my approval.`
- **Doc reminder:** `Check CONTROL.md, DECISIONS.md, and context.md. Don’t repeat solved issues.`
- **Lazy delegation check:** `Run it yourself. Do not hand back trivial steps.`
