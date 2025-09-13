/**
 * Vercel API route for video summarization
 * Handles URL, file upload, and pasted text
 */

import formidable from 'formidable';
import fs from 'fs';

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const workerUrl = process.env.WORKER_URL;
    if (!workerUrl) {
      return res.status(500).json({ error: 'WORKER_URL not configured' });
    }

    // Check if it's a file upload (multipart/form-data)
    const contentType = req.headers['content-type'] || '';
    
    if (contentType.includes('multipart/form-data')) {
      // Handle file upload
      const form = formidable({
        maxFileSize: 50 * 1024 * 1024, // 50MB limit
      });

      const [fields, files] = await form.parse(req);
      
      const file = files.file?.[0];
      const summary_format = fields.summary_format?.[0] || 'bullet_points';
      const context_hints = fields.context_hints?.[0] ? JSON.parse(fields.context_hints[0]) : [];

      if (!file) {
        return res.status(400).json({ error: 'No file uploaded' });
      }

      // Read file content
      const fileContent = fs.readFileSync(file.filepath, 'utf8');
      
      // Determine file type and extract text
      let transcriptText = '';
      const filename = file.originalFilename || '';
      
      if (filename.toLowerCase().endsWith('.txt')) {
        transcriptText = fileContent;
      } else if (filename.toLowerCase().endsWith('.srt')) {
        transcriptText = srtToText(fileContent);
      } else if (filename.toLowerCase().endsWith('.vtt')) {
        transcriptText = vttToText(fileContent);
      } else {
        // For media files, we'd need to send to Cloud Run worker for transcription
        // For now, return error for unsupported media files
        return res.status(400).json({ 
          error: 'Media file transcription not yet implemented. Please upload SRT, VTT, or TXT files.' 
        });
      }

      // Clean up uploaded file
      fs.unlinkSync(file.filepath);

      // Send to Cloud Run worker for summarization
      const response = await fetch(`${workerUrl}/summarize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          transcript_text: transcriptText,
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
        transcript: transcriptText,
        summary_md: data.summary_md,
        summary_html: data.summary_html,
        meta: { ...data.meta, source: 'file_upload', filename },
        message: `File ${filename} processed successfully`
      });

    } else {
      // Handle JSON requests (URL or pasted text)
      const { video_url, pasted_text, summary_format = 'bullet_points', context_hints = [] } = req.body;

      if (pasted_text) {
        // Handle pasted text
        const response = await fetch(`${workerUrl}/summarize`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            transcript_text: pasted_text,
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
          transcript: pasted_text,
          summary_md: data.summary_md,
          summary_html: data.summary_html,
          meta: { ...data.meta, source: 'pasted_text' },
          message: 'Pasted text processed successfully'
        });

      } else if (video_url) {
        // Handle video URL
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

      } else {
        return res.status(400).json({ error: 'video_url, pasted_text, or file upload required' });
      }
    }

  } catch (error) {
    console.error('Error processing request:', error);
    return res.status(500).json({
      error: 'Failed to process request',
      details: error.message
    });
  }
}

// Helper functions for subtitle parsing
function srtToText(srt) {
  return srt
    .split('\n')
    .filter(line => {
      const trimmed = line.trim();
      return trimmed && 
             !trimmed.match(/^\d+$/) && // not just a number
             !trimmed.includes('-->'); // not a timestamp
    })
    .join('\n');
}

function vttToText(vtt) {
  let headerSkipped = false;
  return vtt
    .split('\n')
    .filter(line => {
      const trimmed = line.trim();
      if (!headerSkipped && trimmed.toLowerCase().startsWith('webvtt')) {
        headerSkipped = true;
        return false;
      }
      return trimmed && 
             !trimmed.includes('-->') && // not a timestamp
             !trimmed.match(/^\d+$/); // not just a number
    })
    .join('\n');
}
