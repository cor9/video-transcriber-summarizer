/**
 * Vercel API route for checking job status
 * Polls Firestore to get job status and download links
 */

import { Firestore } from '@google-cloud/firestore';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { job_id } = req.query;

    if (!job_id) {
      return res.status(400).json({ error: 'job_id is required' });
    }

    // Initialize Firestore client
    const firestore = new Firestore({
      projectId: process.env.GOOGLE_CLOUD_PROJECT,
      keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS
    });

    // Get job document
    const docRef = firestore.collection('jobs').doc(job_id);
    const doc = await docRef.get();

    if (!doc.exists) {
      return res.status(404).json({ error: 'Job not found' });
    }

    const jobData = doc.data();

    return res.status(200).json({
      success: true,
      ...jobData
    });

  } catch (error) {
    console.error('Error checking job status:', error);
    return res.status(500).json({
      error: 'Failed to check job status',
      details: error.message
    });
  }
}
