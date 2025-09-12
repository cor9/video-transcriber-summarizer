# Make.com Scenario: YouTube to HTML/MD Summarizer

## 🎯 Overview
This Make.com scenario will automatically process YouTube videos into formatted summaries using a visual workflow with no coding required.

## 🔗 Scenario Flow

### 1. **Trigger: Webhook**
- **Module:** Webhooks
- **Purpose:** Receive YouTube URL from web form or API call
- **Configuration:**
  - Create a custom webhook URL
  - Accept JSON payload: `{"youtube_url": "https://youtube.com/watch?v=VIDEO_ID", "summary_type": "bullet_points"}`
  - Set up authentication if needed

### 2. **YouTube Audio Download**
- **Module:** HTTP
- **Purpose:** Download audio from YouTube using third-party service
- **Configuration:**
  - **Method:** POST
  - **URL:** `https://api.4kdownloader.com/api/convert` (or similar service)
  - **Headers:**
    ```json
    {
      "Content-Type": "application/json",
      "Authorization": "Bearer YOUR_API_KEY"
    }
  - **Body:**
    ```json
    {
      "url": "{{youtube_url}}",
      "format": "mp3",
      "quality": "best"
    }
    ```
  - **Output:** Audio file URL

### 3. **Transcribe Audio**
- **Module:** AssemblyAI > Transcribe a File
- **Purpose:** Convert audio to text
- **Configuration:**
  - **File URL:** `{{audio_file_url}}` (from previous step)
  - **Language:** Auto-detect
  - **Speaker Labels:** Enable if needed
  - **Output:** Full transcript text

### 4. **Summarize Text**
- **Module:** Anthropic > Create a Message
- **Purpose:** Generate AI summary
- **Configuration:**
  - **Model:** claude-3-sonnet-20240229
  - **Input Text:** `{{transcript_text}}`
  - **Prompt:** 
    ```
    Please summarize the following video transcript in {{summary_type}} format. 
    Focus on the main topics, key insights, and important takeaways.
    
    Transcript:
    {{transcript_text}}
    ```
  - **Output:** Summary text

### 5. **Format to Markdown**
- **Module:** Tools > Text Parser
- **Purpose:** Create Markdown file
- **Configuration:**
  - **Text:** `{{summary_text}}`
  - **Template:** 
    ```markdown
    # Video Summary
    
    **Video URL:** {{youtube_url}}
    **Generated:** {{now}}
    
    ## Summary
    {{summary_text}}
    
    ## Full Transcript
    {{transcript_text}}
    ```

### 6. **Convert to HTML**
- **Module:** HTTP
- **Purpose:** Convert Markdown to HTML
- **Configuration:**
  - **Method:** POST
  - **URL:** `https://api.github.com/markdown`
  - **Headers:**
    ```json
    {
      "Content-Type": "application/json",
      "Accept": "application/vnd.github.v3+json"
    }
  - **Body:**
    ```json
    {
      "text": "{{markdown_content}}",
      "mode": "markdown"
    }
    ```
  - **Output:** HTML content

### 7. **Create Styled HTML**
- **Module:** Tools > Text Parser
- **Purpose:** Add CSS styling to HTML
- **Configuration:**
  - **Text:** `{{html_content}}`
  - **Template:**
    ```html
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Video Summary</title>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 1000px; margin: 0 auto; padding: 20px; }
            .container { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            h1, h2, h3 { color: #2c3e50; }
            .meta { color: #6c757d; font-size: 0.9em; margin-bottom: 20px; }
            ul, ol { margin: 15px 0; padding-left: 30px; }
            blockquote { border-left: 4px solid #3498db; margin: 20px 0; padding: 10px 20px; background: #f8f9fa; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎥 Video Summary</h1>
            <div class="meta">
                <strong>Video URL:</strong> {{youtube_url}}<br>
                <strong>Generated:</strong> {{now}}
            </div>
            {{html_content}}
        </div>
    </body>
    </html>
    ```

### 8. **Output/Delivery Options**

#### Option A: Google Drive
- **Module:** Google Drive > Upload a File
- **Configuration:**
  - **File Name:** `video_summary_{{video_id}}.html`
  - **File Content:** `{{styled_html}}`
  - **Folder:** `/VidScribe2AI/Summaries/`

#### Option B: Dropbox
- **Module:** Dropbox > Upload a File
- **Configuration:**
  - **File Name:** `video_summary_{{video_id}}.html`
  - **File Content:** `{{styled_html}}`
  - **Folder:** `/VidScribe2AI/Summaries/`

#### Option C: Webhook Response
- **Module:** Webhooks > Return a Response
- **Configuration:**
  - **Status:** 200
  - **Content Type:** application/json
  - **Body:**
    ```json
    {
      "success": true,
      "video_url": "{{youtube_url}}",
      "transcript": "{{transcript_text}}",
      "summary": "{{summary_text}}",
      "html_content": "{{styled_html}}",
      "markdown_content": "{{markdown_content}}",
      "download_links": {
        "html": "{{google_drive_link}}",
        "markdown": "{{markdown_drive_link}}"
      }
    }
    ```

## 🔧 Setup Instructions

### 1. **Create Make.com Account**
- Go to [make.com](https://make.com)
- Sign up for a free account
- Upgrade to paid plan for more operations

### 2. **Set Up API Keys**
- **AssemblyAI:** Get API key from [assemblyai.com](https://assemblyai.com)
- **Anthropic:** Get API key from [anthropic.com](https://anthropic.com)
- **YouTube Downloader:** Sign up for service like 4K Video Downloader API

### 3. **Create Scenario**
- Click "Create a new scenario"
- Add modules in order
- Configure each module with the settings above
- Test with a sample YouTube URL

### 4. **Deploy Webhook**
- Copy the webhook URL from the first module
- Use it in your web form or API calls

## 🎯 Benefits of Make.com Approach

### ✅ **No Coding Required**
- Visual workflow builder
- Drag-and-drop modules
- Built-in error handling

### ✅ **Reliable & Scalable**
- Automatic retries
- Rate limiting handled
- Cloud-based execution

### ✅ **Easy Integration**
- Webhook triggers
- Multiple output options
- Real-time monitoring

### ✅ **Cost Effective**
- Pay per operation
- No server maintenance
- Automatic scaling

## 🚀 Usage Examples

### Web Form Integration
```html
<form action="YOUR_WEBHOOK_URL" method="POST">
    <input type="url" name="youtube_url" placeholder="YouTube URL" required>
    <select name="summary_type">
        <option value="bullet_points">Bullet Points</option>
        <option value="key_insights">Key Insights</option>
        <option value="detailed_summary">Detailed Summary</option>
    </select>
    <button type="submit">Process Video</button>
</form>
```

### API Integration
```javascript
fetch('YOUR_WEBHOOK_URL', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        youtube_url: 'https://youtube.com/watch?v=VIDEO_ID',
        summary_type: 'bullet_points'
    })
})
.then(response => response.json())
.then(data => console.log(data));
```

## 📊 Expected Output

The scenario will produce:
- **HTML File:** Styled summary with full transcript
- **Markdown File:** Raw markdown format
- **JSON Response:** All content for API integration
- **Download Links:** Direct access to generated files

This Make.com approach completely eliminates the need for Python scripts, server management, and deployment complexity!
