/**
 * Vercel API route for submitting video processing jobs
 * This replaces the heavy /process route with a lightweight job enqueuer
 */

import { GoogleAuth } from 'google-auth-library';
import { PubSub } from '@google-cloud/pubsub';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { video_url, summary_format = 'bullet_points' } = req.body;

    if (!video_url) {
      return res.status(400).json({ error: 'video_url is required' });
    }

    // Initialize Pub/Sub client
    const pubsub = new PubSub({
      projectId: process.env.GOOGLE_CLOUD_PROJECT,
      keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS
    });

    // Generate job ID
    const job_id = crypto.randomUUID();

    // Create job data
    const jobData = {
      job_id,
      video_url,
      summary_format,
      status: 'queued',
      created_at: new Date().toISOString()
    };

    // Publish to Pub/Sub topic
    const topic = pubsub.topic(process.env.PUBSUB_TOPIC || 'transcribe-jobs');
    const messageId = await topic.publishMessage({
      data: Buffer.from(JSON.stringify(jobData)),
      attributes: {
        job_id,
        video_url,
        summary_format
      }
    });

    console.log(`Enqueued job ${job_id} with message ID ${messageId}`);

    return res.status(200).json({
      success: true,
      job_id,
      status: 'queued',
      message: 'Job enqueued successfully'
    });

  } catch (error) {
    console.error('Error submitting job:', error);
    return res.status(500).json({
      error: 'Failed to submit job',
      details: error.message
    });
  }
}
