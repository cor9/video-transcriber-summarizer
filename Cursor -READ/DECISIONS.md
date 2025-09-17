# Project Decisions Log

## 2025-01-12
**Issue:** Vercel deployment crashes with 500 Internal Server Error
**Decision:** Removed conflicting app.py file and test files, ensuring Vercel uses api/index.py structure
**Status:** Success

## 2025-01-12
**Issue:** Missing request import causing "name 'request' is not defined" error
**Decision:** Added request import to Flask imports: `from flask import Flask, jsonify, request`
**Status:** Success

## 2025-01-12
**Issue:** YouTube URLs not supported by AssemblyAI, causing confusing errors
**Decision:** Implemented YouTube URL detection with helpful error messages and user guidance
**Status:** Success

## 2025-01-12
**Issue:** Template rendering issues in Vercel serverless environment
**Decision:** Embedded entire HTML content directly into Flask route as multi-line string
**Status:** Success

## 2025-01-12
**Issue:** Static assets (favicon, sitelogo.svg) returning 404 errors
**Decision:** Configured vercel.json with proper routing for static files and added Flask routes
**Status:** Success

## 2025-01-12
**Issue:** Anthropic library compatibility issues with httpx
**Decision:** Downgraded anthropic to 0.3.11 and pinned httpx to 0.24.1 in requirements.txt
**Status:** Success

## 2025-01-12
**Issue:** User requested design updates to match provided logo assets
**Decision:** Updated UI to use sitelogo.svg with larger size (500x300px) and dark background styling
**Status:** Success

## 2025-01-12
**Issue:** Need to restore full transcription functionality after simplifying for debugging
**Decision:** Re-implemented complete AssemblyAI and Anthropic integration with proper error handling
**Status:** Success

## 2025-01-12
**Issue:** User requested implementation of YouTube support following the provided schema
**Decision:** Enhanced existing Flask app with pytube library, added YouTube download workflow, implemented schema functions (download_audio_from_youtube, transcribe_audio_with_assemblyai, summarize_with_anthropic, generate_output_files), updated UI to support YouTube URLs and summary format selection, maintained Vercel serverless compatibility with proper temp file cleanup
**Status:** Success

## 2025-01-12
**Issue:** User requested file download functionality for HTML and MD files
**Decision:** Added file download endpoints (/download/<filename>), enhanced generate_output_files to create downloadable files with unique IDs, updated UI to show download links, implemented proper file storage in /tmp/vidscribe_outputs directory, added comprehensive HTML styling for downloaded files
**Status:** Success

## 2025-01-12
**Issue:** Vercel deployment failing with 500 errors due to pytube compatibility and Anthropic client initialization issues
**Decision:** Replaced pytube with yt-dlp for better serverless compatibility, implemented lazy initialization for Anthropic client to avoid import errors, updated YouTube download function to use yt-dlp with proper error handling
**Status:** Success

## 2025-01-12
**Issue:** YouTube blocking downloads with "Sign in to confirm you're not a bot" error
**Decision:** Added proper HTTP headers and user agents to bypass bot detection, implemented retry logic and timeout settings, added helpful error messages and suggestions when YouTube blocks downloads, updated UI to warn users about potential restrictions
**Status:** Success

## 2025-01-12
**Issue:** User suggested fallback to get transcripts from YouTube captions or Tactiq
**Decision:** Implemented YouTube captions fallback using youtube-transcript-api, created smart fallback system that tries captions first then audio download, added video ID extraction from various URL formats, enhanced error handling with multiple fallback options, updated UI to show transcript source information
**Status:** Success

## 2025-01-12
**Issue:** YouTube videos being blocked with bot detection affecting both captions and audio download
**Decision:** Implemented comprehensive video accessibility checking before processing, added specific error handling for different failure types (private videos, no captions, bot blocking), enhanced user guidance with targeted suggestions, created video accessibility validation function, improved error messages and fallback strategies
**Status:** Success

## 2025-01-12
**Issue:** User requested integration of jkawamoto/mcp-youtube-transcript MCP server functionality into web app
**Decision:** Created enhanced_youtube_transcript.py module with pagination support, added new API endpoints (/api/youtube/transcript, /api/youtube/info), integrated enhanced mode checkbox in web interface, added yt-dlp dependency for better fallback support, maintained backward compatibility with existing transcript system
**Status:** Success

## 2025-01-12
**Issue:** User requested Vercel Analytics integration for tracking user interactions
**Decision:** Added Vercel Analytics script to HTML template, implemented custom event tracking (transcription_started, transcription_completed, transcription_error, mode_changed), updated vercel.json configuration, created analytics test page and comprehensive documentation, maintained privacy by truncating error messages
**Status:** Success

## 2025-01-12
**Issue:** Vercel build failures due to invalid schema and incompatible dependencies
**Decision:** Removed invalid 'analytics' property from vercel.json, updated yt-dlp from 2024.1.7 to 2022.10.4 for Vercel compatibility, resolved schema validation errors while maintaining all functionality
**Status:** Success

## 2025-01-12
**Issue:** Poor error handling for videos without transcripts causing user confusion
**Decision:** Enhanced error handling with detailed user-friendly messages, added specific suggestions for different error types (subtitles_disabled, rate_limited, video_unavailable), implemented structured error responses with actionable guidance, improved frontend error display with emojis and better formatting
**Status:** Success

---
# Imported Decisions & Learnings (from user)

## Decisions
