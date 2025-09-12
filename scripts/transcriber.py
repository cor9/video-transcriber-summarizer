#!/usr/bin/env python3
"""
Audio Transcriber
Transcribes audio files using AssemblyAI
"""

import sys
import os
import assemblyai as aai

def transcribe_audio(input_file, output_file):
    """Transcribe audio file using AssemblyAI"""
    
    # Check if API key is set
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        print("Error: ASSEMBLYAI_API_KEY environment variable is not set")
        sys.exit(1)
    
    # Configure AssemblyAI
    aai.settings.api_key = api_key
    
    # Create output directory
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    print(f"Transcribing audio file: {input_file}")
    
    try:
        # Upload and transcribe file
        with open(input_file, 'rb') as f:
            transcript = aai.Transcriber().transcribe(f)
        
        # Wait for transcription to complete
        while transcript.status not in [aai.TranscriptStatus.completed, aai.TranscriptStatus.error]:
            transcript = aai.Transcriber().get_transcript(transcript.id)
        
        if transcript.status == aai.TranscriptStatus.error:
            print(f"Transcription failed: {transcript.error}")
            sys.exit(1)
        
        # Save transcript to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(transcript.text)
        
        print(f"Transcription completed: {output_file}")
        print(f"Transcript length: {len(transcript.text)} characters")
        
    except Exception as e:
        print(f"Error transcribing audio: {str(e)}")
        sys.exit(1)

def main():
    if len(sys.argv) != 3:
        print("Usage: python transcriber.py <input_file> <output_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file does not exist: {input_file}")
        sys.exit(1)
    
    transcribe_audio(input_file, output_file)

if __name__ == "__main__":
    main()
