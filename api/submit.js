/**
 * Vercel API route for video summarization
 * Calls Cloud Run worker directly instead of using job queue
 */

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { video_url, summary_format = 'bullet_points', context_hints = [] } = req.body;

    if (!video_url) {
      return res.status(400).json({ error: 'video_url is required' });
    }

    // Call Cloud Run worker directly
    const workerUrl = process.env.WORKER_URL;
    if (!workerUrl) {
      return res.status(500).json({ error: 'WORKER_URL not configured' });
    }

    const response = await fetch(`${workerUrl}/summarize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url: video_url,
        summary_format,
        context_hints: context_hints || [
          "Audience: general; tone: informative and concise",
          "Prefer actionable insights and key takeaways"
        ]
      })
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      return res.status(502).json({ 
        error: data.error || 'Worker failed',
        details: data
      });
    }

    return res.status(200).json({
      success: true,
      transcript: data.transcript_text,
      summary_md: data.summary_md,
      summary_html: data.summary_html,
      meta: data.meta,
      message: 'Video processed successfully'
    });

  } catch (error) {
    console.error('Error processing video:', error);
    return res.status(500).json({
      error: 'Failed to process video',
      details: error.message
    });
  }
}
