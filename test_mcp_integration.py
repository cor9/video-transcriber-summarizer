#!/usr/bin/env python3
"""
Test script to verify MCP server functionality is working in the web app
"""

import requests
import json

def test_mcp_endpoints():
    """Test the MCP-style endpoints"""
    base_url = "https://vidscribe2ai.site"  # Update with your actual URL
    
    # Test video URL
    test_url = "https://www.youtube.com/watch?v=s9TzkYbliO8"
    
    print("🧪 Testing MCP Server Integration...")
    print(f"📹 Test Video: {test_url}")
    print()
    
    # Test 1: Get transcript via MCP endpoint
    print("1️⃣ Testing MCP Transcript Endpoint...")
    transcript_data = {
        "video_url": test_url,
        "language_codes": ["en"]
    }
    
    try:
        response = requests.post(f"{base_url}/api/mcp/youtube/transcript", 
                               json=transcript_data, 
                               timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ MCP Transcript Endpoint: SUCCESS")
                print(f"   Language: {result.get('language')}")
                print(f"   Text length: {len(result.get('text', ''))}")
                print(f"   Preview: {result.get('text', '')[:100]}...")
            else:
                print("❌ MCP Transcript Endpoint: FAILED")
                print(f"   Error: {result.get('error')}")
        else:
            print(f"❌ MCP Transcript Endpoint: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ MCP Transcript Endpoint: EXCEPTION - {e}")
    
    print()
    
    # Test 2: Get video info via MCP endpoint
    print("2️⃣ Testing MCP Video Info Endpoint...")
    info_data = {
        "video_url": test_url
    }
    
    try:
        response = requests.post(f"{base_url}/api/mcp/youtube/info", 
                               json=info_data, 
                               timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ MCP Video Info Endpoint: SUCCESS")
                print(f"   Video ID: {result.get('video_id')}")
                print(f"   Has transcript: {result.get('has_transcript')}")
                print(f"   Duration: {result.get('duration')} seconds")
            else:
                print("❌ MCP Video Info Endpoint: FAILED")
                print(f"   Error: {result.get('error')}")
        else:
            print(f"❌ MCP Video Info Endpoint: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ MCP Video Info Endpoint: EXCEPTION - {e}")
    
    print()
    
    # Test 3: Test main form with MCP mode
    print("3️⃣ Testing Main Form with MCP Mode...")
    form_data = {
        "youtube_url": test_url,
        "use_mcp_mode": "on"
    }
    
    try:
        response = requests.post(f"{base_url}/summarize", 
                               data=form_data, 
                               timeout=60)
        
        if response.status_code == 200:
            if "MCP Error" in response.text:
                print("❌ Main Form MCP Mode: FAILED")
                print("   Error detected in response")
            elif "summary" in response.text.lower():
                print("✅ Main Form MCP Mode: SUCCESS")
                print("   Summary generated successfully")
            else:
                print("⚠️ Main Form MCP Mode: UNCLEAR")
                print("   Response received but unclear if successful")
        else:
            print(f"❌ Main Form MCP Mode: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Main Form MCP Mode: EXCEPTION - {e}")
    
    print()
    print("🎯 MCP Integration Test Complete!")

if __name__ == "__main__":
    test_mcp_endpoints()
