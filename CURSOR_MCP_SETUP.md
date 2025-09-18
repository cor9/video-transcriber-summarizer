# Cursor MCP Setup Guide

## Overview
This project includes MCP (Model Context Protocol) configuration for Cursor development, allowing direct YouTube transcript fetching while coding.

## Prerequisites
- Python ≥3.9
- `uv` package manager (installed via `pipx`)
- Network access for GitHub package downloads

## Installation Steps

### 1. Install uv (if not already installed)
```bash
pipx install uv
pipx ensurepath
```

### 2. Verify Installation
```bash
which uv
# Should show: /Users/coreyralston/.local/bin/uv
```

### 3. Test MCP Server
```bash
uvx --from git+https://github.com/jkawamoto/mcp-youtube-transcript mcp-youtube-transcript --help
```

## Configuration
The MCP configuration is in `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "youtube-transcript": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/jkawamoto/mcp-youtube-transcript",
        "mcp-youtube-transcript",
        "--response-limit",
        "15000"
      ]
    }
  }
}
```

## Usage in Cursor

### Basic Transcript Fetching
In a new Cursor chat, use:
```
Use tool youtube-transcript.get_transcript with:
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "lang": "en"
}
```

### Paginated Results
For long videos, you'll get a `next_cursor`. Continue fetching:
```
Use tool youtube-transcript.get_transcript with:
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "lang": "en",
  "next_cursor": "<token_from_previous_response>"
}
```

## Configuration Options

### Response Limit
- **Current**: `15000` characters per response
- **Adjust**: Lower to `5000` for smaller responses
- **Disable**: Set to `-1` for no pagination

### Language Options
- `"en"` - English
- `"auto"` - Auto-generated captions
- `"en-US"` - US English
- `"en-GB"` - British English

## Troubleshooting

### Common Issues
1. **`uvx: command not found`**
   - Solution: Install uv globally (`pipx install uv`)

2. **SSL/GitHub rate limit errors**
   - Solution: Try again or fork the repo and pin to a release tag

3. **Timeouts**
   - Solution: Increase `--response-limit` or manually chunk transcripts

### Verification Commands
```bash
# Check uv installation
which uv

# Test MCP server
uvx --from git+https://github.com/jkawamoto/mcp-youtube-transcript mcp-youtube-transcript --version

# Check Python version
python --version
```

## Important Notes

- **Development Only**: MCP configuration is for Cursor development only
- **Vercel Deployment**: Uses Flask `/summarize` endpoint, not MCP
- **Separate Concerns**: MCP for dev-time transcript fetching, Flask for production web app
- **Path Updates**: May need to restart terminal or source shell config after `pipx ensurepath`

## Benefits

- **Direct Access**: Fetch transcripts while coding without external API calls
- **Pagination**: Handle long videos with automatic chunking
- **Language Support**: Multiple language variants and auto-generated captions
- **Development Speed**: No need to deploy/test for transcript functionality
