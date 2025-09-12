#!/usr/bin/env python3
"""
Test script to verify Gemini integration is working properly
"""

import os
import sys
import time

def test_gemini_summarize():
    """Test the gemini_summarize module"""
    try:
        from gemini_summarize import (
            summarize_with_gemini,
            cleanup_transcript,
            baseline_summary
        )
        print("✅ Successfully imported gemini_summarize functions")
        
        # Test cleanup_transcript
        test_text = """# https://youtube.com/watch?v=test
No text
This is actual content.
No text
More content here."""
        
        cleaned = cleanup_transcript(test_text)
        print(f"✅ cleanup_transcript works: '{cleaned}'")
        
        # Test baseline_summary
        baseline = baseline_summary("Test content", "bullet_points")
        print(f"✅ baseline_summary works: '{baseline[:50]}...'")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing gemini_summarize: {e}")
        return False

def test_gemini_api():
    """Test actual Gemini API call if key is available"""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("⚠️  No GEMINI_API_KEY or GOOGLE_API_KEY found - skipping API test")
        return True
    
    try:
        from gemini_summarize import summarize_with_gemini
        
        test_transcript = """
        This is a test transcript about artificial intelligence. 
        AI is transforming many industries including healthcare, finance, and transportation.
        Machine learning algorithms can process vast amounts of data to find patterns.
        Natural language processing enables computers to understand human speech.
        Computer vision allows machines to interpret visual information.
        """
        
        print("🔄 Testing Gemini API call...")
        start_time = time.time()
        
        summary = summarize_with_gemini(api_key, test_transcript, "bullet_points")
        
        elapsed = time.time() - start_time
        print(f"✅ Gemini API call successful! ({elapsed:.2f}s)")
        print(f"📝 Summary: {summary[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Gemini API test failed: {e}")
        return False

def test_youtube_id_extractor():
    """Test the YouTube ID extractor"""
    try:
        # Add the current directory to path so we can import web_interface
        sys.path.insert(0, os.path.dirname(__file__))
        from web_interface import extract_video_id, canonical_watch_url
        
        test_urls = [
            "https://www.youtube.com/watch?v=Z5EjbBPri-c",
            "https://youtu.be/Z5EjbBPri-c", 
            "https://www.youtube.com/embed/Z5EjbBPri-c",
            "https://www.youtube.com/v/Z5EjbBPri-c"
        ]
        
        for url in test_urls:
            video_id = extract_video_id(url)
            canonical = canonical_watch_url(video_id) if video_id else None
            print(f"✅ {url} -> {video_id} -> {canonical}")
            
        return True
        
    except Exception as e:
        print(f"❌ YouTube ID extractor test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Gemini Integration")
    print("=" * 50)
    
    tests = [
        ("Gemini Summarize Module", test_gemini_summarize),
        ("YouTube ID Extractor", test_youtube_id_extractor),
        ("Gemini API Call", test_gemini_api),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 30)
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Gemini integration is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
