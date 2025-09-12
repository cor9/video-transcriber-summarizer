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

---
# Imported Decisions & Learnings (from user)

## Decisions
