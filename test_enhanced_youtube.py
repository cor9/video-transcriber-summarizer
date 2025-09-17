#!/usr/bin/env python3
"""
Test script for enhanced YouTube transcript functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.enhanced_youtube_transcript import get_enhanced_transcript, get_transcript_chunked, get_video_info

def test_enhanced_transcript():
    """Test the enhanced YouTube transcript functionality"""
    
    # Test video URL (the one mentioned in the original request)
    test_url = "https://www.youtube.com/watch?v=AJpK3YTTKZ4"
    
    print("🧪 Testing Enhanced YouTube Transcript Functionality")
    print("=" * 60)
    
    # Test 1: Get video info
    print("\n1. Testing video info...")
    info = get_video_info(test_url)
    print(f"Video Info: {info}")
    
    # Test 2: Get full transcript
    print("\n2. Testing full transcript...")
    result = get_enhanced_transcript(test_url)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        print(f"Metadata: {result.get('metadata', {})}")
    else:
        print(f"✅ Success!")
        print(f"Total characters: {result['total_chars']}")
        print(f"Chunks: {result['chunks']}")
        print(f"Metadata: {result['metadata']}")
        print(f"First 200 chars: {result['text'][:200]}...")
    
    # Test 3: Test chunked transcript (if we have a long transcript)
    print("\n3. Testing chunked transcript...")
    chunk_result = get_transcript_chunked(test_url, "en", None)
    
    if 'error' in chunk_result:
        print(f"❌ Error: {chunk_result['error']}")
    else:
        print(f"✅ Chunk Success!")
        print(f"Chunk size: {len(chunk_result['text'])}")
        print(f"Total chars: {chunk_result['total_chars']}")
        print(f"Has more: {chunk_result['next_cursor'] is not None}")
        print(f"First 200 chars: {chunk_result['text'][:200]}...")
        
        # If there's more content, test getting the next chunk
        if chunk_result['next_cursor']:
            print(f"\n4. Testing next chunk (cursor: {chunk_result['next_cursor']})...")
            next_chunk = get_transcript_chunked(test_url, "en", chunk_result['next_cursor'])
            if 'error' in next_chunk:
                print(f"❌ Next chunk error: {next_chunk['error']}")
            else:
                print(f"✅ Next chunk success!")
                print(f"Next chunk size: {len(next_chunk['text'])}")
                print(f"First 200 chars: {next_chunk['text'][:200]}...")

if __name__ == "__main__":
    test_enhanced_transcript()
