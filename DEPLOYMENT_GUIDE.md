# 🚀 Simple Deployment Guide

## Overview
Your app now uses a **dedicated transcript server** by default. No options, no confusion - it just works.

## 📋 Deployment Steps

### 1. Deploy the Dedicated Server
```bash
cd mcp_server
vercel --prod
```
**Server URL**: `https://mcp-youtube-transcript-server.vercel.app`

### 2. Deploy the Main App
```bash
# Set the server URL
export MCP_SERVER_URL="https://mcp-youtube-transcript-server.vercel.app"

# Deploy
vercel --prod
```

## ✅ That's It!

Your app now:
- ✅ Uses the dedicated server automatically
- ✅ Has better error handling
- ✅ Includes caching for performance
- ✅ No user options to confuse them
- ✅ Just works

## 🧪 Test It
Visit your site and paste any YouTube URL - it will use the dedicated server automatically.
