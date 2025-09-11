# 🎥 Video Transcriber & Summarizer

A powerful web application that transcribes videos using AssemblyAI and generates AI-powered summaries using Anthropic's Claude. Perfect for converting long videos into digestible, structured content.

## ✨ Features

- **Video Transcription**: Convert any publicly accessible video URL into text using AssemblyAI
- **AI-Powered Summarization**: Generate summaries using Anthropic's Claude with multiple style options:
  - 📝 Bullet Points
  - 💡 Key Insights  
  - 📋 Detailed Summary
  - 📋 Actionable Guide
- **Multiple Output Formats**: Download summaries as HTML or Markdown files
- **Modern Web Interface**: Clean, responsive design with real-time progress tracking
- **Temporary File Management**: Secure handling of temporary files with automatic cleanup

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd /Users/coreyralston/video-transcriber
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   export ASSEMBLYAI_API_KEY="your_assemblyai_api_key_here"
   export ANTHROPIC_API_KEY="your_anthropic_api_key_here"
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Open your browser and visit:**
   ```
   http://localhost:8080
   ```

## 📋 Usage

1. **Enter Video URL**: Paste any publicly accessible video URL (YouTube, Vimeo, direct video files, etc.)

2. **Choose Summary Style**: Select from four different summarization approaches:
   - **Bullet Points**: Clean, concise bullet-point format
   - **Key Insights**: Structured analysis with headings
   - **Detailed Summary**: Comprehensive overview with sections
   - **Actionable Guide**: Step-by-step instructions and practical advice

3. **Select Output Format**: Choose between HTML or Markdown for your download

4. **Process**: Click "Transcribe & Summarize" and watch the progress steps

5. **Download**: Once complete, download your formatted summary file

## 🏗️ Architecture

### Backend (`app.py`)
- **Flask Web Framework**: Handles HTTP requests and responses
- **AssemblyAI Integration**: Transcribes video URLs to text
- **Anthropic Claude Integration**: Generates AI-powered summaries
- **Temporary File Management**: Secure handling of intermediate files

### Frontend (`templates/index.html`)
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Progress**: Visual feedback during processing
- **Modern UI**: Clean, professional interface with smooth animations

### Data Flow
```
Video URL → AssemblyAI → Transcript → Claude AI → Summary → Formatted Output
```

## 🔧 Configuration

The application uses environment variables for API keys. You can set them in two ways:

### Option 1: Environment Variables (Recommended)
```bash
export ASSEMBLYAI_API_KEY="your_assemblyai_api_key_here"
export ANTHROPIC_API_KEY="your_anthropic_api_key_here"
```

### Option 2: Create a .env file
Create a `.env` file in the project root:
```
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**Note**: You must provide your own API keys to use this application. The application will not start without them.

## 📁 Project Structure

```
video-transcriber/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .env.example          # Environment variables template
└── templates/
    └── index.html         # Web interface template
```

## 🛠️ API Endpoints

- `GET /` - Main application interface
- `POST /transcribe` - Process video transcription and summarization
- `GET /download/<filename>` - Download generated summary files
- `GET /health` - Health check endpoint

## 🔒 Security Features

- **Temporary File Cleanup**: All intermediate files are automatically deleted
- **Input Validation**: URL validation and error handling
- **Secure File Handling**: Proper file permissions and cleanup
- **Environment Variables**: API keys stored securely outside of code

## 🎯 Supported Video Sources

- YouTube videos (public URLs)
- Vimeo videos
- Direct video file URLs (.mp4, .avi, .mov, etc.)
- Any publicly accessible video URL supported by AssemblyAI

## 🚨 Error Handling

The application includes comprehensive error handling for:
- Invalid video URLs
- Network connectivity issues
- API rate limits
- Transcription failures
- Summarization errors

## 📊 Performance Notes

- **Transcription Time**: Depends on video length (typically 1-2 minutes per minute of video)
- **Summarization Time**: Usually 10-30 seconds depending on transcript length
- **File Cleanup**: Automatic cleanup of temporary files after processing

## 🔄 Development

To modify or extend the application:

1. **Add New Summary Styles**: Edit the `PROMPT_TEMPLATES` dictionary in `app.py`
2. **Modify UI**: Update `templates/index.html` for frontend changes
3. **Add Features**: Extend the Flask routes in `app.py`

## 📝 License

This project is for educational and personal use. Please ensure you have proper API access and usage rights for AssemblyAI and Anthropic services.

## 🤝 Support

For issues or questions:
1. Check the error messages in the web interface
2. Verify your video URL is publicly accessible
3. Ensure stable internet connection for API calls
4. Check that API keys are valid and have sufficient credits

---

**Happy Transcribing! 🎬✨**