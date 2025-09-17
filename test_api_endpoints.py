#!/usr/bin/env python3
"""
Test script for the new API endpoints
"""
import requests
import json

def test_api_endpoints():
    """Test the new YouTube API endpoints"""
    
    base_url = "http://localhost:5000"  # Adjust if your app runs on different port
    test_url = "https://www.youtube.com/watch?v=AJpK3YTTKZ4"
    
    print("🧪 Testing New API Endpoints")
    print("=" * 50)
    
    # Test 1: YouTube transcript endpoint
    print("\n1. Testing /api/youtube/transcript...")
    try:
        response = requests.post(f"{base_url}/api/youtube/transcript", 
                               json={"url": test_url, "language": "en"})
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                result = data['data']
                print(f"✅ Success!")
                print(f"Total chars: {result['total_chars']}")
                print(f"Chunks: {result['chunks']}")
                print(f"First 200 chars: {result['text'][:200]}...")
            else:
                print(f"❌ API Error: {data['error']}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the web app is running!")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: YouTube info endpoint
    print("\n2. Testing /api/youtube/info...")
    try:
        response = requests.post(f"{base_url}/api/youtube/info", 
                               json={"url": test_url})
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                info = data['data']
                print(f"✅ Success!")
                print(f"Video Info: {info}")
            else:
                print(f"❌ API Error: {data['error']}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the web app is running!")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Enhanced mode in main process endpoint
    print("\n3. Testing enhanced mode in /process...")
    try:
        response = requests.post(f"{base_url}/process", 
                               json={
                                   "mode": "youtube",
                                   "video_url": test_url,
                                   "summary_format": "bullet_points",
                                   "use_enhanced": True
                               })
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"✅ Enhanced mode success!")
                print(f"Message: {data['message']}")
                print(f"Metrics: {data.get('metrics', {})}")
            else:
                print(f"❌ API Error: {data['error']}")
                if 'suggestions' in data:
                    print(f"Suggestions: {data['suggestions']}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the web app is running!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_api_endpoints()
