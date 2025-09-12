/**
 * Vercel API route for collecting user feedback
 * Stores feedback in a simple JSON file or could integrate with Firestore
 */

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { 
      video_url, 
      summary_format, 
      helpful, 
      notes, 
      meta = {} 
    } = req.body;

    if (typeof helpful !== 'boolean') {
      return res.status(400).json({ error: 'helpful field is required and must be boolean' });
    }

    // Create feedback record
    const feedback = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      video_url: video_url || null,
      summary_format: summary_format || null,
      helpful: helpful,
      notes: notes || '',
      meta: {
        ...meta,
        user_agent: req.headers['user-agent'] || '',
        ip: req.headers['x-forwarded-for'] || req.connection.remoteAddress || '',
      }
    };

    // For now, just log the feedback
    // In production, you'd store this in Firestore, Supabase, or a database
    console.log('User feedback received:', JSON.stringify(feedback, null, 2));

    // You could also send to an external service
    // await sendToAnalytics(feedback);

    return res.status(200).json({
      success: true,
      message: 'Feedback recorded successfully',
      feedback_id: feedback.id
    });

  } catch (error) {
    console.error('Error recording feedback:', error);
    return res.status(500).json({
      error: 'Failed to record feedback',
      details: error.message
    });
  }
}
