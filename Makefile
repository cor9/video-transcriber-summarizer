# VidScribe2AI - Video Transcription & Summarization Workflow
# Usage: make YOUTUBE_URL="https://youtube.com/watch?v=VIDEO_ID"

# Configuration
YOUTUBE_URL ?= 
VIDEO_ID = $(shell echo $(YOUTUBE_URL) | sed 's/.*[?&]v=\([^&]*\).*/\1/')
AUDIO_FILE = downloads/$(VIDEO_ID).mp4
TRANSCRIPT_FILE = transcripts/$(VIDEO_ID).txt
SUMMARY_MD_FILE = summaries/$(VIDEO_ID).md
SUMMARY_HTML_FILE = summaries/$(VIDEO_ID).html

# API Keys (set via environment variables)
ASSEMBLYAI_API_KEY ?= $(shell echo $$ASSEMBLYAI_API_KEY)
ANTHROPIC_API_KEY ?= $(shell echo $$ANTHROPIC_API_KEY)

# Default target
all: $(SUMMARY_HTML_FILE)

# Create necessary directories
directories:
	@mkdir -p downloads transcripts summaries

# Download audio from YouTube
$(AUDIO_FILE): directories
	@echo "Downloading audio from YouTube: $(YOUTUBE_URL)"
	@python scripts/youtube_downloader.py "$(YOUTUBE_URL)" "$@"

# Transcribe audio using AssemblyAI
$(TRANSCRIPT_FILE): $(AUDIO_FILE)
	@echo "Transcribing audio: $<"
	@python scripts/transcriber.py "$<" "$@"

# Summarize transcript using Anthropic
$(SUMMARY_MD_FILE): $(TRANSCRIPT_FILE)
	@echo "Summarizing transcript: $<"
	@python scripts/summarizer.py "$<" "$@"

# Convert Markdown to HTML
$(SUMMARY_HTML_FILE): $(SUMMARY_MD_FILE)
	@echo "Converting to HTML: $<"
	@python scripts/formatter.py "$<" "$@"

# Clean up all generated files
clean:
	@echo "Cleaning up generated files..."
	@rm -rf downloads transcripts summaries

# Clean up only audio files (keep transcripts and summaries)
clean-audio:
	@echo "Cleaning up audio files..."
	@rm -rf downloads

# Show help
help:
	@echo "VidScribe2AI - Video Transcription & Summarization Workflow"
	@echo ""
	@echo "Usage:"
	@echo "  make YOUTUBE_URL=\"https://youtube.com/watch?v=VIDEO_ID\""
	@echo "  make clean                    # Remove all generated files"
	@echo "  make clean-audio             # Remove only audio files"
	@echo "  make help                    # Show this help"
	@echo ""
	@echo "Environment Variables:"
	@echo "  ASSEMBLYAI_API_KEY          # Required for transcription"
	@echo "  ANTHROPIC_API_KEY           # Required for summarization"
	@echo ""
	@echo "Example:"
	@echo "  make YOUTUBE_URL=\"https://youtube.com/watch?v=dQw4w9WgXcQ\""

# Check if required environment variables are set
check-env:
	@if [ -z "$(ASSEMBLYAI_API_KEY)" ]; then \
		echo "Error: ASSEMBLYAI_API_KEY environment variable is not set"; \
		exit 1; \
	fi
	@if [ -z "$(ANTHROPIC_API_KEY)" ]; then \
		echo "Error: ANTHROPIC_API_KEY environment variable is not set"; \
		exit 1; \
	fi
	@echo "Environment variables check passed"

# Validate YouTube URL
validate-url:
	@if [ -z "$(YOUTUBE_URL)" ]; then \
		echo "Error: YOUTUBE_URL is required"; \
		echo "Usage: make YOUTUBE_URL=\"https://youtube.com/watch?v=VIDEO_ID\""; \
		exit 1; \
	fi
	@echo "YouTube URL validated: $(YOUTUBE_URL)"

# Full workflow with validation
process: check-env validate-url all

.PHONY: all clean clean-audio help check-env validate-url process directories
