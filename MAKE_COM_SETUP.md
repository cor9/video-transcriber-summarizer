# Make.com Blueprint Setup Guide

## 🚀 Quick Start

### 1. **Import the Blueprint**
1. Log in to [make.com](https://make.com)
2. Go to "Scenarios" page
3. Click "Create a new scenario"
4. Click the "More" menu (⋯) in the bottom toolbar
5. Select "Import Blueprint"
6. Upload the `make_com_blueprint.json` file

### 2. **Connect Your Accounts**
You'll need to connect these services:

#### **AssemblyAI**
- Go to [assemblyai.com](https://assemblyai.com)
- Sign up and get your API key
- In Make.com, click on the AssemblyAI module
- Click "Add" next to the connection
- Enter your API key

#### **Anthropic Claude**
- Go to [anthropic.com](https://anthropic.com)
- Sign up and get your API key
- In Make.com, click on the Anthropic module
- Click "Add" next to the connection
- Enter your API key

#### **Google Drive**
- In Make.com, click on the Google Drive module
- Click "Add" next to the connection
- Sign in with your Google account
- Grant permissions

#### **4K Video Downloader API**
- Go to [4kdownloader.com](https://4kdownloader.com)
- Sign up for API access
- Get your API key
- In Make.com, click on the HTTP module (YouTube Downloader)
- Update the Authorization header with your API key

### 3. **Configure the Webhook**
1. Click on the "Webhook Trigger" module
2. Copy the webhook URL
3. Save this URL - you'll use it to trigger the scenario

### 4. **Set Up Google Drive Folder**
1. Create a folder in Google Drive called "VidScribe2AI"
2. Get the folder ID from the URL
3. Update the Google Drive module with the folder ID

### 5. **Test the Scenario**
1. Click "Run once" to test
2. Or send a POST request to your webhook URL:

```bash
curl -X POST "YOUR_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "summary_type": "bullet_points"
  }'
```

## 🔧 Configuration Details

### **Webhook Payload Format**
```json
{
  "youtube_url": "https://youtube.com/watch?v=VIDEO_ID",
  "summary_type": "bullet_points" // or "key_insights" or "detailed_summary"
}
```

### **Response Format**
```json
{
  "success": true,
  "video_url": "https://youtube.com/watch?v=VIDEO_ID",
  "video_title": "Video Title",
  "transcript": "Full transcript text...",
  "summary": "AI-generated summary...",
  "html_content": "<html>Styled HTML...</html>",
  "markdown_content": "# Markdown content...",
  "download_links": {
    "html": "https://drive.google.com/file/...",
    "markdown": "Markdown content as string"
  },
  "metadata": {
    "duration": 180,
    "confidence": 0.95,
    "tokens_used": 1500
  }
}
```

## 🎯 Usage Examples

### **Web Form Integration**
```html
<!DOCTYPE html>
<html>
<head>
    <title>VidScribe2AI</title>
</head>
<body>
    <form id="videoForm">
        <input type="url" id="youtubeUrl" placeholder="YouTube URL" required>
        <select id="summaryType">
            <option value="bullet_points">Bullet Points</option>
            <option value="key_insights">Key Insights</option>
            <option value="detailed_summary">Detailed Summary</option>
        </select>
        <button type="submit">Process Video</button>
    </form>

    <div id="results" style="display:none;">
        <h3>Results:</h3>
        <div id="summary"></div>
        <div id="downloadLinks"></div>
    </div>

    <script>
        document.getElementById('videoForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const response = await fetch('YOUR_WEBHOOK_URL', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    youtube_url: document.getElementById('youtubeUrl').value,
                    summary_type: document.getElementById('summaryType').value
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('summary').innerHTML = data.summary;
                document.getElementById('downloadLinks').innerHTML = 
                    `<a href="${data.download_links.html}" target="_blank">Download HTML</a>`;
                document.getElementById('results').style.display = 'block';
            }
        });
    </script>
</body>
</html>
```

### **API Integration**
```python
import requests
import json

def process_video(youtube_url, summary_type="bullet_points"):
    webhook_url = "YOUR_WEBHOOK_URL"
    
    payload = {
        "youtube_url": youtube_url,
        "summary_type": summary_type
    }
    
    response = requests.post(webhook_url, json=payload)
    return response.json()

# Usage
result = process_video("https://youtube.com/watch?v=dQw4w9WgXcQ")
print(result['summary'])
```

## 🛠️ Customization Options

### **Modify Summary Prompts**
1. Click on the "Anthropic Claude Summarizer" module
2. Edit the prompt field
3. Add custom instructions for different summary types

### **Change HTML Styling**
1. Click on the "HTML Styler" module
2. Edit the CSS in the template
3. Customize colors, fonts, layout, etc.

### **Add More Output Destinations**
1. Add a new module after "HTML Styler"
2. Choose from Dropbox, Email, Slack, etc.
3. Connect the modules with arrows

### **Modify Error Handling**
1. Click on the scenario settings
2. Adjust retry attempts and delays
3. Set up error notifications

## 📊 Monitoring & Analytics

### **View Scenario Runs**
1. Go to "Scenarios" page
2. Click on your scenario
3. View "Runs" tab to see execution history

### **Monitor Performance**
- Check execution times
- Monitor error rates
- Track API usage costs

### **Set Up Notifications**
1. Go to "Settings" > "Notifications"
2. Set up email alerts for errors
3. Configure success notifications

## 🔒 Security Best Practices

### **API Key Management**
- Use environment variables for API keys
- Rotate keys regularly
- Monitor API usage

### **Webhook Security**
- Use HTTPS webhooks only
- Implement authentication if needed
- Validate input data

### **Data Privacy**
- Review data retention policies
- Ensure GDPR compliance
- Use secure storage options

## 💰 Cost Estimation

### **Make.com Operations**
- **Free Plan:** 1,000 operations/month
- **Core Plan:** 10,000 operations/month ($9/month)
- **Pro Plan:** 40,000 operations/month ($29/month)

### **API Costs**
- **AssemblyAI:** ~$0.0001 per second of audio
- **Anthropic Claude:** ~$0.003 per 1K tokens
- **4K Video Downloader:** Varies by plan

### **Example Cost (10 videos/month)**
- Make.com: Free (under 1,000 operations)
- AssemblyAI: ~$0.50 (5 hours of audio)
- Anthropic: ~$1.50 (50K tokens)
- **Total: ~$2.00/month**

## 🚨 Troubleshooting

### **Common Issues**

#### **YouTube Download Fails**
- Check 4K Video Downloader API key
- Verify YouTube URL format
- Try different video (some may be restricted)

#### **Transcription Fails**
- Check AssemblyAI API key
- Verify audio file URL is accessible
- Check audio file format

#### **Summarization Fails**
- Check Anthropic API key
- Verify transcript text is not empty
- Check token limits

#### **Google Drive Upload Fails**
- Check Google Drive connection
- Verify folder permissions
- Check file size limits

### **Debug Steps**
1. Check scenario execution logs
2. Verify all connections are active
3. Test each module individually
4. Check API quotas and limits

## 📈 Scaling Tips

### **High Volume Processing**
- Upgrade to higher Make.com plan
- Use batch processing
- Implement queue management

### **Performance Optimization**
- Use parallel processing where possible
- Optimize API calls
- Cache frequently used data

### **Error Recovery**
- Set up automatic retries
- Implement fallback strategies
- Monitor and alert on failures

This blueprint gives you a complete, production-ready YouTube summarization system that's much more reliable than the Python approach!
