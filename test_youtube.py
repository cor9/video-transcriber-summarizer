#!/usr/bin/env python3
"""
Test script to verify YouTube processing works
"""

import requests
import json
import os

def test_youtube_processing():
    """Test YouTube URL processing"""
    
    # Test URLs
    test_urls = [
        "https://youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll (short, popular)
        "https://youtu.be/dQw4w9WgXcQ",  # Short format
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Full format
    ]
    
    # Check if running locally or on Vercel
    base_url = "http://localhost:5000" if os.getenv("LOCAL_TEST") else "https://vidscribe2ai.site"
    
    print(f"Testing against: {base_url}")
    print("=" * 50)
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}. Testing URL: {url}")
        
        try:
            response = requests.post(
                f"{base_url}/transcribe",
                json={
                    "video_url": url,
                    "prompt_choice": "bullet_points",
                    "output_format": "html"
                },
                timeout=30
            )
            
            data = response.json()
            
            if data.get('success'):
                print("✅ SUCCESS!")
                print(f"   Transcript length: {len(data.get('raw_transcript', ''))}")
                print(f"   Summary length: {len(data.get('summary', ''))}")
            else:
                print("❌ FAILED")
                print(f"   Error: {data.get('error', 'Unknown error')}")
                
        except requests.exceptions.Timeout:
            print("⏱️ TIMEOUT - Vercel 10-second limit hit")
        except Exception as e:
            print(f"💥 EXCEPTION: {str(e)}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

def test_direct_url():
    """Test direct media URL processing"""
    
    # Example direct URL (you'd need a real one)
    test_url = "https://example.com/sample.mp4"
    
    base_url = "http://localhost:5000" if os.getenv("LOCAL_TEST") else "https://vidscribe2ai.site"
    
    print(f"\nTesting direct URL: {test_url}")
    print("=" * 50)
    
    try:
        response = requests.post(
            f"{base_url}/transcribe",
            json={
                "video_url": test_url,
                "prompt_choice": "bullet_points",
                "output_format": "html"
            },
            timeout=30
        )
        
        data = response.json()
        
        if data.get('success'):
            print("✅ SUCCESS!")
            print(f"   Transcript length: {len(data.get('raw_transcript', ''))}")
            print(f"   Summary length: {len(data.get('summary', ''))}")
        else:
            print("❌ FAILED")
            print(f"   Error: {data.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"💥 EXCEPTION: {str(e)}")

if __name__ == "__main__":
    print("🧪 VidScribe2AI Test Suite")
    print("=" * 50)
    
    # Test YouTube URLs
    test_youtube_processing()
    
    # Test direct URL (commented out since we don't have a real test file)
    # test_direct_url()
    
    print("\n💡 Tips:")
    print("- YouTube blocking is normal - try different videos")
    print("- Shorter videos (< 5 min) work better")
    print("- Direct media URLs work reliably")
    print("- Vercel free tier has 10-second timeout limits")
