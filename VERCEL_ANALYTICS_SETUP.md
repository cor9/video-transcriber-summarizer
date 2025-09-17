# Vercel Analytics Integration

This document explains how Vercel Analytics has been integrated into your VidScribe2AI Flask application.

## What's Been Added

### 1. Analytics Script Integration
- Added Vercel Analytics script to the main HTML template
- Includes both the initialization script and the insights script
- Automatically tracks page views and user interactions

### 2. Custom Event Tracking
The following custom events are now tracked:

#### `transcription_started`
Triggered when a user starts a transcription process.
```javascript
{
  mode: 'youtube' | 'paste' | 'upload',
  summary_format: 'bullet_points' | 'key_insights' | 'detailed_summary',
  use_enhanced: boolean,
  has_url: boolean,
  has_transcript: boolean,
  has_file: boolean
}
```

#### `transcription_completed`
Triggered when a transcription is successfully completed.
```javascript
{
  mode: string,
  summary_format: string,
  use_enhanced: boolean,
  generation_ms: number,
  model: string
}
```

#### `transcription_error`
Triggered when a transcription fails.
```javascript
{
  mode: string,
  summary_format: string,
  use_enhanced: boolean,
  error_message: string (truncated to 100 chars)
}
```

#### `mode_changed`
Triggered when a user switches between input modes.
```javascript
{
  mode: 'youtube' | 'paste' | 'upload'
}
```

### 3. Configuration Updates
- Updated `vercel.json` to enable analytics
- Added analytics configuration to ensure proper tracking

## How It Works

### For Flask Applications on Vercel
Unlike Next.js applications that use `@vercel/analytics`, Flask applications on Vercel use the direct script integration:

```html
<script>
  window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
</script>
<script defer src="/_vercel/insights/script.js"></script>
```

### Event Tracking
Events are tracked using the `window.va()` function:
```javascript
window.va('track', 'event_name', { data: 'value' });
```

## Testing

### 1. Test Page
Visit `/analytics_test.html` on your deployed site to test analytics integration:
- Check if analytics is loaded
- Test custom event tracking
- Simulate user interactions

### 2. Manual Testing
1. Deploy your changes to Vercel
2. Visit your site and perform actions (transcribe videos, change modes, etc.)
3. Check your Vercel dashboard for analytics data
4. Data may take 30 seconds to appear

### 3. Browser Developer Tools
- Open browser dev tools
- Check Network tab for requests to `/_vercel/insights/`
- Verify `window.va` function is available in console

## Analytics Dashboard

Once deployed, you can view analytics in your Vercel dashboard:

1. Go to your project in Vercel dashboard
2. Click on "Analytics" tab
3. View page views, user interactions, and custom events
4. Filter by date range and specific events

## Privacy Considerations

- Error messages are truncated to 100 characters for privacy
- No personal data (like actual transcript content) is tracked
- Only metadata about usage patterns is collected
- Analytics respects user privacy settings and ad blockers

## Troubleshooting

### Analytics Not Loading
- Check if `/_vercel/insights/script.js` is accessible
- Verify `vercel.json` has analytics enabled
- Ensure you're on a Vercel deployment (not localhost)

### Events Not Appearing
- Wait 30 seconds for data to appear
- Check browser console for errors
- Verify `window.va` function is available
- Test with the analytics test page

### Content Blockers
- Some ad blockers may block analytics
- Test in incognito mode or with extensions disabled
- Analytics will still work for most users

## Benefits

With Vercel Analytics integrated, you can now track:

- **Usage Patterns**: Which features are most popular
- **Performance**: How long transcriptions take
- **Error Rates**: Which features have issues
- **User Behavior**: How users navigate your app
- **Feature Adoption**: Usage of enhanced mode vs regular mode

This data will help you:
- Optimize performance
- Fix common issues
- Understand user preferences
- Make data-driven decisions about features
