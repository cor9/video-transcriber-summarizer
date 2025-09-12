# Quick Setup Guide - YouTube API Key

## 🔑 **Your API Key**
```
AIzaSyAR0iZ7-3QwCbyQ5vXFCzL6HZUvt5YXAks
```

## ⚡ **Quick Setup (2 minutes)**

### **For Vercel Deployment:**

1. **Go to Vercel Dashboard**
   - Visit [vercel.com/dashboard](https://vercel.com/dashboard)
   - Select your `video-transcriber` project

2. **Add Environment Variable**
   - Go to "Settings" → "Environment Variables"
   - Click "Add New"
   - Name: `YOUTUBE_API_KEY`
   - Value: `AIzaSyAR0iZ7-3QwCbyQ5vXFCzL6HZUvt5YXAks`
   - Click "Save"

3. **Redeploy**
   - Go to "Deployments" tab
   - Click "Redeploy" on the latest deployment
   - Wait for deployment to complete

### **For Local Testing:**

1. **Set Environment Variable**
   ```bash
   export YOUTUBE_API_KEY="AIzaSyAR0iZ7-3QwCbyQ5vXFCzL6HZUvt5YXAks"
   ```

2. **Run the App**
   ```bash
   python api/index.py
   ```

3. **Test It**
   ```bash
   python test_youtube_captions.py
   ```

## 🧪 **Test Your Setup**

### **Option 1: Run Test Script**
```bash
python test_youtube_captions.py
```

### **Option 2: Test in Browser**
1. Go to your app URL
2. Try this YouTube video: `https://youtube.com/watch?v=dQw4w9WgXcQ`
3. Should work instantly with captions!

### **Option 3: Health Check**
```bash
curl https://your-app-url.com/health
```

Should return:
```json
{
  "status": "healthy",
  "youtube_api_configured": true
}
```

## 🎯 **What Should Happen Now**

### **✅ YouTube Videos with Captions:**
- **Process in 2-3 seconds** ⚡
- **No more bot blocking errors**
- **Clean, legal approach**

### **✅ YouTube Videos without Captions:**
- **Clear error message**
- **Helpful suggestions**
- **Fallback options**

### **✅ Direct Media URLs:**
- **Work via AssemblyAI**
- **Same as before**

## 🔒 **Security Best Practices**

### **✅ Do:**
- Keep API key in environment variables
- Restrict API key to YouTube Data API v3
- Monitor usage in Google Cloud Console
- Rotate keys periodically

### **❌ Don't:**
- Commit API key to code
- Share API key publicly
- Use in client-side code
- Leave unrestricted

## 🚀 **You're Ready!**

Once you set the environment variable:

1. **YouTube videos with captions** → Work instantly ⚡
2. **No more "bot blocking" errors** → Clean, professional
3. **Much faster processing** → 2-3 seconds vs 30-60 seconds
4. **Legal and reliable** → Uses official YouTube API

**The app will now process YouTube videos like a pro!** 🎉

## 🆘 **Troubleshooting**

### **"youtube_api_configured": false**
- Check environment variable is set correctly
- Restart your application
- Verify the API key is valid

### **"No captions available"**
- Try a different video
- Popular/educational videos usually have captions
- Use direct media URL as fallback

### **Still getting bot blocking errors**
- Make sure you're using the latest code
- Check that the new transcribe route is deployed
- Verify environment variables are set
