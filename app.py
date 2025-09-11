import os
import tempfile
import time
from flask import Flask, render_template, request, jsonify, send_file
import assemblyai as aai
import anthropic
from datetime import datetime

app = Flask(__name__)

# API Configuration
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Check if API keys are provided
if not ASSEMBLYAI_API_KEY:
    raise ValueError("ASSEMBLYAI_API_KEY environment variable is required")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable is required")

# Initialize API clients
aai.settings.api_key = ASSEMBLYAI_API_KEY
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Prompt templates for different summarization styles
PROMPT_TEMPLATES = {
    "bullet_points": """
Please summarize the following video transcript in clear, concise bullet points. Focus on the main topics, key insights, and important takeaways. Use bullet points for easy reading.

Transcript:
{transcript}
""",
    
    "key_insights": """
Analyze the following video transcript and extract the most important insights, lessons, and actionable information. Present your findings in a structured format with clear headings.

Transcript:
{transcript}
""",
    
    "detailed_summary": """
Provide a comprehensive summary of the following video transcript. Include:
1. Main topic and purpose
2. Key points discussed
3. Important details and examples
4. Conclusions or takeaways

Transcript:
{transcript}
""",
    
    "actionable_guide": """
Transform the following video transcript into a practical, actionable guide. Focus on:
1. Step-by-step instructions
2. Specific actions the viewer can take
3. Tools, resources, or methods mentioned
4. Key takeaways that can be implemented immediately
5. Clear, actionable advice

Format as a practical guide with numbered steps and actionable items.

Transcript:
{transcript}
"""
}

def handle_transcribe_request(video_url):
    """
    Transcribe video using AssemblyAI API
    """
    try:
        # Create a transcriber
        transcriber = aai.Transcriber()
        
        # Start transcription
        transcript = transcriber.transcribe(video_url)
        
        # Wait for transcription to complete
        while transcript.status != aai.TranscriptStatus.completed:
            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(f"Transcription failed: {transcript.error}")
            time.sleep(1)
            transcript = transcriber.get_transcript(transcript.id)
        
        # Save transcript to temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        temp_file.write(transcript.text)
        temp_file.close()
        
        return temp_file.name, transcript.text
        
    except Exception as e:
        raise Exception(f"Transcription error: {str(e)}")

def handle_summarize_request(text_file_path, prompt_choice):
    """
    Summarize transcript using Anthropic Claude
    """
    try:
        # Read transcript from file
        with open(text_file_path, 'r', encoding='utf-8') as file:
            transcript_text = file.read()
        
        # Get the appropriate prompt template
        prompt_template = PROMPT_TEMPLATES.get(prompt_choice, PROMPT_TEMPLATES["bullet_points"])
        prompt = prompt_template.format(transcript=transcript_text)
        
        # Call Anthropic Claude API
        response = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4000,
            temperature=0.7,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        summary_text = response.content[0].text
        return summary_text
        
    except Exception as e:
        raise Exception(f"Summarization error: {str(e)}")

def format_output(summary_text, format_type="html"):
    """
    Format the summary text into HTML or Markdown
    """
    try:
        if format_type == "html":
            # Convert to HTML with proper formatting
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Summary</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        ul, ol {{
            margin: 15px 0;
        }}
        li {{
            margin: 8px 0;
        }}
        .timestamp {{
            font-size: 0.9em;
            color: #7f8c8d;
            font-style: italic;
        }}
        .summary-meta {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #3498db;
        }}
    </style>
</head>
<body>
    <h1>Video Summary</h1>
    <div class="summary-meta">
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Format:</strong> HTML Summary</p>
    </div>
    <div class="content">
        {summary_text.replace(chr(10), '<br>').replace('•', '&bull;')}
    </div>
</body>
</html>
"""
            # Save to temporary HTML file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            
        else:  # Markdown format
            markdown_content = f"""# Video Summary

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Format:** Markdown Summary

---

{summary_text}
"""
            # Save to temporary Markdown file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8')
            temp_file.write(markdown_content)
            temp_file.close()
        
        return temp_file.name
        
    except Exception as e:
        raise Exception(f"Formatting error: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        prompt_choice = data.get('prompt_choice', 'bullet_points')
        output_format = data.get('output_format', 'html')
        
        if not video_url:
            return jsonify({'error': 'Video URL is required'}), 400
        
        # Step 1: Transcribe video
        transcript_file, transcript_text = handle_transcribe_request(video_url)
        
        # Step 2: Summarize transcript
        summary_text = handle_summarize_request(transcript_file, prompt_choice)
        
        # Step 3: Format output
        formatted_file = format_output(summary_text, output_format)
        
        # Clean up transcript file
        os.unlink(transcript_file)
        
        return jsonify({
            'success': True,
            'transcript': transcript_text,
            'summary': summary_text,
            'download_file': formatted_file,
            'file_extension': '.html' if output_format == 'html' else '.md'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)