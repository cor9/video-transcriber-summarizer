#!/usr/bin/env python3
"""
Test YouTube captions functionality with the new API key
"""

import os
import requests
import json

# Test configuration
YOUTUBE_API_KEY = "AIzaSyAR0iZ7-3QwCbyQ5vXFCzL6HZUvt5YXAks"
BASE_URL = "https://vidscribe2ai.site"  # Change to localhost if testing locally

def test_youtube_captions():
    """Test YouTube captions functionality"""
    
    print("🧪 Testing YouTube Captions API")
    print("=" * 50)
    
    # Test URLs with known captions
    test_videos = [
        {
            "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "name": "Rick Roll (popular, likely has captions)",
            "expected": "success"
        },
        {
            "url": "https://youtu.be/dQw4w9WgXcQ", 
            "name": "Rick Roll (short format)",
            "expected": "success"
        },
        {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "name": "Rick Roll (full format)",
            "expected": "success"
        }
    ]
    
    for i, test in enumerate(test_videos, 1):
        print(f"\n{i}. Testing: {test['name']}")
        print(f"   URL: {test['url']}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/transcribe",
                json={
                    "video_url": test['url'],
                    "prompt_choice": "bullet_points",
                    "output_format": "html"
                },
                timeout=30
            )
            
            data = response.json()
            
            if data.get('success'):
                print("   ✅ SUCCESS!")
                print(f"   📝 Transcript length: {len(data.get('raw_transcript', ''))}")
                print(f"   🎯 Summary length: {len(data.get('summary', ''))}")
                print(f"   💬 Message: {data.get('message', '')}")
                
                # Show preview of transcript
                transcript = data.get('raw_transcript', '')
                if transcript:
                    preview = transcript[:200] + "..." if len(transcript) > 200 else transcript
                    print(f"   📖 Transcript preview: {preview}")
                    
            else:
                print("   ❌ FAILED")
                print(f"   🚨 Error: {data.get('error', 'Unknown error')}")
                
                # Show suggestions if available
                suggestions = data.get('suggestions', [])
                if suggestions:
                    print("   💡 Suggestions:")
                    for suggestion in suggestions:
                        print(f"      • {suggestion}")
                        
        except requests.exceptions.Timeout:
            print("   ⏱️ TIMEOUT - Request took too long")
        except Exception as e:
            print(f"   💥 EXCEPTION: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    print("✅ If you see SUCCESS messages, the YouTube captions API is working!")
    print("❌ If you see FAILED messages, check your API key configuration")
    print("💡 The app now uses official YouTube captions instead of downloading videos")

def test_health_endpoint():
    """Test the health endpoint to verify API key configuration"""
    
    print("\n🏥 Testing Health Endpoint")
    print("=" * 30)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        data = response.json()
        
        print(f"Status: {data.get('status', 'unknown')}")
        print(f"AssemblyAI configured: {data.get('assemblyai_configured', False)}")
        print(f"Anthropic configured: {data.get('anthropic_configured', False)}")
        print(f"YouTube API configured: {data.get('youtube_api_configured', False)}")
        
        if data.get('youtube_api_configured'):
            print("✅ YouTube API key is properly configured!")
        else:
            print("❌ YouTube API key is NOT configured - check your environment variables")
            
    except Exception as e:
        print(f"💥 Health check failed: {str(e)}")

def test_direct_api():
    """Test YouTube API directly"""
    
    print("\n🔍 Testing YouTube API Directly")
    print("=" * 35)
    
    try:
        # Test the YouTube Data API directly
        video_id = "dQw4w9WgXcQ"
        url = f"https://www.googleapis.com/youtube/v3/captions?part=id,snippet&videoId={video_id}&key={YOUTUBE_API_KEY}"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            
            if items:
                print(f"✅ Found {len(items)} caption track(s) for video {video_id}")
                for item in items:
                    lang = item['snippet'].get('language', 'unknown')
                    name = item['snippet'].get('name', 'unknown')
                    print(f"   📝 Language: {lang}, Name: {name}")
            else:
                print(f"❌ No captions found for video {video_id}")
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"💥 Direct API test failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 VidScribe2AI YouTube Captions Test Suite")
    print("=" * 50)
    
    # Test health endpoint first
    test_health_endpoint()
    
    # Test YouTube API directly
    test_direct_api()
    
    # Test the full captions functionality
    test_youtube_captions()
    
    print("\n💡 Next Steps:")
    print("1. If tests pass, your YouTube captions are working!")
    print("2. If tests fail, check your environment variables")
    print("3. Make sure YOUTUBE_API_KEY is set in your deployment")
    print("4. Try different YouTube videos if some don't have captions")
