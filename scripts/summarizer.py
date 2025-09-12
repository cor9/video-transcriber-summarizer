#!/usr/bin/env python3
"""
Transcript Summarizer
Summarizes transcripts using Anthropic Claude
"""

import sys
import os
import anthropic

def summarize_transcript(input_file, output_file, summary_type="bullet_points"):
    """Summarize transcript using Anthropic Claude"""
    
    # Check if API key is set
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is not set")
        sys.exit(1)
    
    # Initialize Anthropic client
    client = anthropic.Anthropic(api_key=api_key)
    
    # Create output directory
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Read transcript
    with open(input_file, 'r', encoding='utf-8') as f:
        transcript_text = f.read()
    
    print(f"Summarizing transcript: {input_file}")
    print(f"Transcript length: {len(transcript_text)} characters")
    
    # Define prompt templates
    prompt_templates = {
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
"""
    }
    
    try:
        # Get the appropriate prompt
        prompt_template = prompt_templates.get(summary_type, prompt_templates["bullet_points"])
        prompt = prompt_template.format(transcript=transcript_text)
        
        # Generate summary
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        summary = response.content[0].text
        
        # Save summary to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        print(f"Summary completed: {output_file}")
        print(f"Summary length: {len(summary)} characters")
        
    except Exception as e:
        print(f"Error summarizing transcript: {str(e)}")
        sys.exit(1)

def main():
    if len(sys.argv) < 3:
        print("Usage: python summarizer.py <input_file> <output_file> [summary_type]")
        print("Summary types: bullet_points, key_insights, detailed_summary")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    summary_type = sys.argv[3] if len(sys.argv) > 3 else "bullet_points"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file does not exist: {input_file}")
        sys.exit(1)
    
    # Validate summary type
    valid_types = ["bullet_points", "key_insights", "detailed_summary"]
    if summary_type not in valid_types:
        print(f"Error: Invalid summary type '{summary_type}'. Valid types: {', '.join(valid_types)}")
        sys.exit(1)
    
    summarize_transcript(input_file, output_file, summary_type)

if __name__ == "__main__":
    main()
