#!/usr/bin/env python3
"""
Test script for three types of YouTube videos:
1. Manual Captions (easy) - Big channels, English, human captions
2. Auto-generated only (medium) - English auto-CC
3. Rate-limited / quirky (hard) - New or niche videos, shorts links
"""

import requests
import json
import time
import sys
from typing import Dict, List, Tuple

# Test video URLs for each category
TEST_VIDEOS = {
    "manual_captions": [
        "https://youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll - classic, manual captions
        "https://youtube.com/watch?v=9bZkp7q19f0",  # PSY - Gangnam Style - big channel
    ],
    "auto_generated": [
        "https://youtube.com/watch?v=YQHsXMglC9A",  # Adele - Hello - auto captions
        "https://youtube.com/watch?v=fJ9rUzIMcZQ",  # Queen - Bohemian Rhapsody - auto captions
    ],
    "rate_limited": [
        "https://youtube.com/watch?v=jNQXAC9IVRw",  # Me at the zoo - first YouTube video
        "https://youtube.com/shorts/dQw4w9WgXcQ",   # Shorts format
    ]
}

def test_worker_endpoint(worker_url: str, video_url: str, summary_format: str = "bullet_points") -> Tuple[bool, Dict]:
    """Test a single video against the worker endpoint"""
    try:
        response = requests.post(f"{worker_url}/summarize", 
            json={
                "url": video_url,
                "summary_format": summary_format,
                "context_hints": ["Test run"]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, {"error": f"HTTP {response.status_code}", "response": response.text}
            
    except Exception as e:
        return False, {"error": str(e)}

def run_test_suite(worker_url: str) -> Dict:
    """Run the complete test suite"""
    results = {
        "manual_captions": {"passed": 0, "total": 0, "details": []},
        "auto_generated": {"passed": 0, "total": 0, "details": []},
        "rate_limited": {"passed": 0, "total": 0, "details": []}
    }
    
    print("🧪 Testing VidScribe2AI Cloud Run Worker")
    print("=" * 60)
    
    for category, videos in TEST_VIDEOS.items():
        print(f"\n📹 Testing {category.replace('_', ' ').title()}")
        print("-" * 40)
        
        for video_url in videos:
            print(f"Testing: {video_url}")
            
            start_time = time.time()
            success, data = test_worker_endpoint(worker_url, video_url)
            elapsed = time.time() - start_time
            
            results[category]["total"] += 1
            
            if success:
                results[category]["passed"] += 1
                
                # Validate response structure
                transcript_len = len(data.get("transcript_text", ""))
                summary_len = len(data.get("summary_md", ""))
                source = data.get("meta", {}).get("captions_source", "unknown")
                
                print(f"  ✅ Success ({elapsed:.1f}s)")
                print(f"     Source: {source}")
                print(f"     Transcript: {transcript_len} chars")
                print(f"     Summary: {summary_len} chars")
                
                # Assertions
                assert transcript_len > 0, "Empty transcript"
                assert summary_len > 0, "Empty summary"
                assert source in ["youtube-transcript-api", "yt-dlp"], f"Unknown source: {source}"
                assert elapsed < 12, f"Too slow: {elapsed:.1f}s"
                
                results[category]["details"].append({
                    "url": video_url,
                    "success": True,
                    "elapsed": elapsed,
                    "source": source,
                    "transcript_len": transcript_len,
                    "summary_len": summary_len
                })
            else:
                print(f"  ❌ Failed ({elapsed:.1f}s)")
                print(f"     Error: {data.get('error', 'Unknown error')}")
                
                results[category]["details"].append({
                    "url": video_url,
                    "success": False,
                    "elapsed": elapsed,
                    "error": data.get("error", "Unknown error")
                })
    
    return results

def print_summary(results: Dict):
    """Print test summary"""
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    total_passed = 0
    total_tests = 0
    
    for category, data in results.items():
        passed = data["passed"]
        total = data["total"]
        rate = (passed / total * 100) if total > 0 else 0
        
        total_passed += passed
        total_tests += total
        
        status = "✅" if rate >= 95 else "⚠️" if rate >= 80 else "❌"
        print(f"{status} {category.replace('_', ' ').title():<20} {passed}/{total} ({rate:.1f}%)")
    
    overall_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    overall_status = "✅" if overall_rate >= 95 else "⚠️" if overall_rate >= 80 else "❌"
    
    print(f"\n{overall_status} Overall Success Rate: {total_passed}/{total_tests} ({overall_rate:.1f}%)")
    
    # Performance metrics
    all_elapsed = []
    sources = {"youtube-transcript-api": 0, "yt-dlp": 0}
    
    for category_data in results.values():
        for detail in category_data["details"]:
            if detail["success"]:
                all_elapsed.append(detail["elapsed"])
                if "source" in detail:
                    sources[detail["source"]] += 1
    
    if all_elapsed:
        avg_elapsed = sum(all_elapsed) / len(all_elapsed)
        max_elapsed = max(all_elapsed)
        print(f"⏱️  Average Latency: {avg_elapsed:.1f}s")
        print(f"⏱️  Max Latency: {max_elapsed:.1f}s")
        print(f"📊 Caption Sources: {sources}")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if overall_rate >= 95:
        print("   🎉 Excellent! System is production-ready.")
    elif overall_rate >= 80:
        print("   ⚠️  Good performance, but monitor rate-limited videos.")
    else:
        print("   ❌ Issues detected. Check worker logs and configuration.")
    
    if sources.get("yt-dlp", 0) > sources.get("youtube-transcript-api", 0):
        print("   📈 High yt-dlp usage indicates YouTube rate limiting.")
        print("   💡 Consider adding more conservative retry delays.")

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python test_video_types.py <WORKER_URL>")
        print("Example: python test_video_types.py https://vidscribe-worker-xxx.run.app")
        sys.exit(1)
    
    worker_url = sys.argv[1].rstrip('/')
    
    print(f"🎯 Testing worker: {worker_url}")
    
    # Test health endpoint first
    try:
        health_response = requests.get(f"{worker_url}/health", timeout=10)
        if health_response.status_code == 200:
            print("✅ Health check passed")
        else:
            print(f"❌ Health check failed: {health_response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Health check error: {e}")
        sys.exit(1)
    
    # Run test suite
    results = run_test_suite(worker_url)
    
    # Print summary
    print_summary(results)
    
    # Exit with appropriate code
    total_passed = sum(data["passed"] for data in results.values())
    total_tests = sum(data["total"] for data in results.values())
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    if success_rate >= 95:
        print("\n🎉 All tests passed! System is ready for production.")
        sys.exit(0)
    else:
        print(f"\n⚠️  Some tests failed. Success rate: {success_rate:.1f}%")
        sys.exit(1)

if __name__ == "__main__":
    main()
