# VidScribe2AI - Make-Based Workflow

A robust video transcription and summarization tool using a `make`-based workflow for better reliability and modularity.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Make
- Environment variables set:
  ```bash
  export ASSEMBLYAI_API_KEY="your_assemblyai_key"
  export ANTHROPIC_API_KEY="your_anthropic_key"
  ```

### Usage

#### Command Line (Make Workflow)
```bash
# Process a YouTube video
make YOUTUBE_URL="https://youtube.com/watch?v=VIDEO_ID"

# Process with specific summary type
make YOUTUBE_URL="https://youtube.com/watch?v=VIDEO_ID" SUMMARY_TYPE="key_insights"

# Clean up generated files
make clean

# Show help
make help
```

#### Web Interface
```bash
# Start the web interface
python web_interface.py

# Then visit http://localhost:5000
```

## 📁 Project Structure

```
video-transcriber/
├── Makefile                 # Main workflow definition
├── scripts/
│   ├── youtube_downloader.py    # Downloads audio from YouTube
│   ├── transcriber.py           # Transcribes audio using AssemblyAI
│   ├── summarizer.py            # Summarizes using Anthropic Claude
│   └── formatter.py             # Converts Markdown to HTML
├── web_interface.py         # Web interface that uses make
├── api/
│   └── index.py             # Original Flask app (legacy)
└── downloads/               # Generated audio files
    transcripts/             # Generated transcripts
    summaries/               # Generated summaries
```

## 🔧 How It Works

### 1. Download Audio (`youtube_downloader.py`)
- Extracts video ID from YouTube URL
- Uses multiple strategies to bypass bot detection
- Downloads best quality audio as MP4

### 2. Transcribe Audio (`transcriber.py`)
- Uploads audio file to AssemblyAI
- Waits for transcription to complete
- Saves transcript as text file

### 3. Summarize Transcript (`summarizer.py`)
- Sends transcript to Anthropic Claude
- Generates summary in specified format
- Saves summary as Markdown file

### 4. Format Output (`formatter.py`)
- Converts Markdown to styled HTML
- Adds professional styling and metadata
- Creates downloadable HTML file

## 🎯 Benefits of Make Workflow

### ✅ **Reliability**
- Each step is independent and can be retried
- File dependencies ensure proper order
- Easy to debug individual steps

### ✅ **Efficiency**
- Only processes changed files
- Parallel processing possible
- No unnecessary re-processing

### ✅ **Modularity**
- Each script has a single responsibility
- Easy to test individual components
- Reusable across different projects

### ✅ **Transparency**
- Clear workflow visible in Makefile
- Easy to understand and modify
- Version control friendly

## 🛠️ Advanced Usage

### Custom Summary Types
```bash
# Bullet points (default)
make YOUTUBE_URL="..." SUMMARY_TYPE="bullet_points"

# Key insights
make YOUTUBE_URL="..." SUMMARY_TYPE="key_insights"

# Detailed summary
make YOUTUBE_URL="..." SUMMARY_TYPE="detailed_summary"
```

### Batch Processing
```bash
# Process multiple videos
for url in "https://youtube.com/watch?v=VID1" "https://youtube.com/watch?v=VID2"; do
    make YOUTUBE_URL="$url"
done
```

### Custom Configuration
```bash
# Override default settings
make YOUTUBE_URL="..." AUDIO_FILE="custom_audio.mp4" TRANSCRIPT_FILE="custom.txt"
```

## 🔍 Troubleshooting

### YouTube Download Issues
```bash
# Check if video is accessible
make YOUTUBE_URL="..." validate-url

# Try different strategies
python scripts/youtube_downloader.py "URL" "output.mp4"
```

### API Key Issues
```bash
# Check environment variables
make check-env

# Test individual components
python scripts/transcriber.py "input.mp4" "output.txt"
python scripts/summarizer.py "input.txt" "output.md"
```

### File Not Found
```bash
# Check what files were generated
ls -la downloads/ transcripts/ summaries/

# Clean and retry
make clean
make YOUTUBE_URL="..."
```

## 📊 Output Files

### Generated Files
- `downloads/VIDEO_ID.mp4` - Downloaded audio
- `transcripts/VIDEO_ID.txt` - Raw transcript
- `summaries/VIDEO_ID.md` - Markdown summary
- `summaries/VIDEO_ID.html` - Styled HTML summary

### File Sizes
- Audio: 5-50MB (depending on video length)
- Transcript: 1-10KB (text only)
- Summary: 1-5KB (condensed content)
- HTML: 2-10KB (with styling)

## 🚀 Deployment

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ASSEMBLYAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."

# Run web interface
python web_interface.py
```

### Production (Vercel)
The web interface can be deployed to Vercel by updating the `vercel.json` to use `web_interface.py` instead of `api/index.py`.

## 🔄 Migration from Flask App

The original Flask app (`api/index.py`) is still available but the make-based workflow is recommended for:
- Better reliability
- Easier debugging
- More robust error handling
- Better scalability

To migrate:
1. Use the web interface (`web_interface.py`) instead of the Flask app
2. Or use the command-line make workflow directly
3. The original Flask app remains as a fallback option
