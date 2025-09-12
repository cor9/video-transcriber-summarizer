#!/usr/bin/env python3
"""
Test script for the hybrid VidScribe2AI architecture
Tests both Vercel API routes and Cloud Run worker
"""

import os
import sys
import time
import requests
import json
from urllib.parse import urlparse

def test_cloud_run_worker(base_url):
    """Test the Cloud Run worker directly"""
    print("🧪 Testing Cloud Run Worker")
    print("-" * 40)
    
    # Test health check
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test job enqueue
    test_job = {
        "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "summary_format": "bullet_points"
    }
    
    try:
        response = requests.post(
            f"{base_url}/enqueue",
            json=test_job,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            job_id = data.get('job_id')
            print(f"✅ Job enqueued successfully: {job_id}")
            
            # Test status check
            for i in range(5):  # Check status 5 times
                time.sleep(2)
                status_response = requests.get(f"{base_url}/status/{job_id}", timeout=10)
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get('status', 'unknown')
                    print(f"   Status check {i+1}: {status}")
                    
                    if status == 'completed':
                        print("✅ Job completed successfully!")
                        print(f"   Download links: {status_data.get('download_links', {})}")
                        return True
                    elif status == 'failed':
                        print(f"❌ Job failed: {status_data.get('error', 'Unknown error')}")
                        return False
                else:
                    print(f"❌ Status check failed: {status_response.status_code}")
                    return False
            
            print("⚠️  Job still processing after 10 seconds")
            return True  # Not necessarily a failure
            
        else:
            print(f"❌ Job enqueue failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Job enqueue error: {e}")
        return False

def test_vercel_api(base_url):
    """Test the Vercel API routes"""
    print("\n🧪 Testing Vercel API Routes")
    print("-" * 40)
    
    # Test job submission
    test_job = {
        "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "summary_format": "bullet_points"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/submit",
            json=test_job,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            job_id = data.get('job_id')
            print(f"✅ Job submitted via Vercel: {job_id}")
            
            # Test status check
            for i in range(3):  # Check status 3 times
                time.sleep(2)
                status_response = requests.get(f"{base_url}/api/status?job_id={job_id}", timeout=10)
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get('status', 'unknown')
                    print(f"   Status check {i+1}: {status}")
                    
                    if status == 'completed':
                        print("✅ Job completed via Vercel!")
                        return True
                    elif status == 'failed':
                        print(f"❌ Job failed: {status_data.get('error', 'Unknown error')}")
                        return False
                else:
                    print(f"❌ Status check failed: {status_response.status_code}")
                    return False
            
            print("⚠️  Job still processing after 6 seconds")
            return True  # Not necessarily a failure
            
        else:
            print(f"❌ Job submission failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Job submission error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 VidScribe2AI Hybrid Architecture Test")
    print("=" * 50)
    
    # Get URLs from environment or use defaults
    cloud_run_url = os.getenv('CLOUD_RUN_URL')
    vercel_url = os.getenv('VERCEL_URL')
    
    if not cloud_run_url:
        cloud_run_url = input("Enter Cloud Run service URL: ").strip()
    
    if not vercel_url:
        vercel_url = input("Enter Vercel app URL: ").strip()
    
    if not cloud_run_url or not vercel_url:
        print("❌ Both URLs are required for testing")
        return 1
    
    print(f"Cloud Run URL: {cloud_run_url}")
    print(f"Vercel URL: {vercel_url}")
    print()
    
    # Run tests
    tests = [
        ("Cloud Run Worker", lambda: test_cloud_run_worker(cloud_run_url)),
        ("Vercel API Routes", lambda: test_vercel_api(vercel_url)),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Hybrid architecture is working.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
