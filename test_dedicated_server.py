#!/usr/bin/env python3
"""
Test script for the dedicated MCP transcript server architecture
"""

import requests
import json
import time

def test_dedicated_server():
    """Test the dedicated MCP server locally"""
    print("🧪 Testing Dedicated MCP Server (Local)...")
    
    # Test video URL
    test_url = "https://www.youtube.com/watch?v=s9TzkYbliO8"
    
    print(f"📹 Test Video: {test_url}")
    print()
    
    # Test 1: Health check
    print("1️⃣ Testing Health Check...")
    try:
        response = requests.get("http://localhost:8080/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health Check: SUCCESS")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health Check: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Health Check: EXCEPTION - {e}")
    
    print()
    
    # Test 2: Transcript endpoint
    print("2️⃣ Testing Transcript Endpoint...")
    transcript_data = {
        "video_url": test_url,
        "language_codes": ["en"]
    }
    
    try:
        response = requests.post("http://localhost:8080/api/transcript", 
                               json=transcript_data, 
                               timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ Transcript Endpoint: SUCCESS")
                print(f"   Language: {result.get('language')}")
                print(f"   Text length: {len(result.get('text', ''))}")
                print(f"   Cached: {result.get('cached', False)}")
                print(f"   Preview: {result.get('text', '')[:100]}...")
            else:
                print("❌ Transcript Endpoint: FAILED")
                print(f"   Error: {result.get('error')}")
        else:
            print(f"❌ Transcript Endpoint: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Transcript Endpoint: EXCEPTION - {e}")
    
    print()
    
    # Test 3: Video info endpoint
    print("3️⃣ Testing Video Info Endpoint...")
    info_data = {
        "video_url": test_url
    }
    
    try:
        response = requests.post("http://localhost:8080/api/video-info", 
                               json=info_data, 
                               timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ Video Info Endpoint: SUCCESS")
                print(f"   Video ID: {result.get('video_id')}")
                print(f"   Has transcript: {result.get('has_transcript')}")
                print(f"   Duration: {result.get('duration')} seconds")
            else:
                print("❌ Video Info Endpoint: FAILED")
                print(f"   Error: {result.get('error')}")
        else:
            print(f"❌ Video Info Endpoint: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Video Info Endpoint: EXCEPTION - {e}")
    
    print()
    print("🎯 Dedicated Server Test Complete!")

def test_main_app_integration():
    """Test the main app integration with dedicated server"""
    print("🧪 Testing Main App Integration...")
    
    # Test video URL
    test_url = "https://www.youtube.com/watch?v=s9TzkYbliO8"
    
    print(f"📹 Test Video: {test_url}")
    print()
    
    # Test main form with dedicated server mode
    print("1️⃣ Testing Main Form with Dedicated Server Mode...")
    form_data = {
        "youtube_url": test_url,
        "use_dedicated_server": "on"
    }
    
    try:
        response = requests.post("http://localhost:5001/summarize", 
                               data=form_data, 
                               timeout=60)
        
        if response.status_code == 200:
            if "Dedicated Server Error" in response.text:
                print("❌ Main Form Dedicated Server Mode: FAILED")
                print("   Error detected in response")
            elif "summary" in response.text.lower():
                print("✅ Main Form Dedicated Server Mode: SUCCESS")
                print("   Summary generated successfully")
            else:
                print("⚠️ Main Form Dedicated Server Mode: UNCLEAR")
                print("   Response received but unclear if successful")
        else:
            print(f"❌ Main Form Dedicated Server Mode: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Main Form Dedicated Server Mode: EXCEPTION - {e}")
    
    print()
    print("🎯 Main App Integration Test Complete!")

def main():
    print("🚀 Dedicated MCP Server Architecture Test")
    print("=" * 50)
    print()
    
    print("📋 Instructions:")
    print("1. Start the dedicated server: cd mcp_server && python mcp_server.py")
    print("2. Start the main app: python web_interface.py")
    print("3. Run this test script")
    print()
    
    choice = input("Which test would you like to run? (1=Server, 2=Integration, 3=Both): ")
    
    if choice == "1":
        test_dedicated_server()
    elif choice == "2":
        test_main_app_integration()
    elif choice == "3":
        test_dedicated_server()
        print("\n" + "=" * 50 + "\n")
        test_main_app_integration()
    else:
        print("Invalid choice. Please run again and select 1, 2, or 3.")

if __name__ == "__main__":
    main()
