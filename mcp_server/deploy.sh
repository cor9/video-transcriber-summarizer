#!/bin/bash

# Deploy MCP YouTube Transcript Server to Vercel
# This script sets up the dedicated transcript server

echo "🚀 Deploying MCP YouTube Transcript Server..."

# Create vercel.json for the MCP server
cat > vercel.json << EOF
{
  "version": 2,
  "name": "mcp-youtube-transcript-server",
  "builds": [
    {
      "src": "mcp_server.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "mcp_server.py"
    }
  ],
  "env": {
    "PYTHON_VERSION": "3.9"
  }
}
EOF

echo "✅ Created vercel.json for MCP server"
echo "📁 Server files ready for deployment"
echo ""
echo "🔧 To deploy:"
echo "1. cd mcp_server"
echo "2. vercel --prod"
echo ""
echo "🌐 Your MCP server will be available at:"
echo "   https://mcp-youtube-transcript-server.vercel.app"
echo ""
echo "📡 API endpoint:"
echo "   https://mcp-youtube-transcript-server.vercel.app/api/transcript"
