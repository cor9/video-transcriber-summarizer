#!/usr/bin/env python3
"""
Test script for enhanced error handling
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.enhanced_youtube_transcript import get_enhanced_transcript

def test_error_scenarios():
    """Test various error scenarios"""
    
    print("🧪 Testing Enhanced Error Handling")
    print("=" * 50)
    
    # Test cases for different error scenarios
    test_cases = [
        {
            "name": "Video without captions",
            "url": "https://www.youtube.com/watch?v=GuTcle5edjk",
            "description": "This video has captions disabled"
        },
        {
            "name": "Invalid URL",
            "url": "https://www.youtube.com/watch?v=invalid123",
            "description": "This should trigger video unavailable error"
        },
        {
            "name": "Non-YouTube URL",
            "url": "https://example.com/video",
            "description": "This should trigger invalid URL error"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📋 Testing: {test_case['name']}")
        print(f"Description: {test_case['description']}")
        print(f"URL: {test_case['url']}")
        print("-" * 40)
        
        result = get_enhanced_transcript(test_case['url'])
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            print(f"Error Type: {result.get('metadata', {}).get('error_type', 'unknown')}")
            
            if 'suggestions' in result:
                print("💡 Suggestions:")
                for suggestion in result['suggestions']:
                    print(f"  • {suggestion}")
            
            if 'common_causes' in result:
                print("🔍 Common Causes:")
                for cause in result['common_causes']:
                    print(f"  • {cause}")
        else:
            print(f"✅ Success! Got transcript with {result['total_chars']} characters")
        
        print()

if __name__ == "__main__":
    test_error_scenarios()
