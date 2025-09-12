#!/usr/bin/env python3
"""Debug the clean_paste function"""

import re

def clean_paste(text: str) -> str:
    """Clean pasted text by removing Tactiq metadata and timestamps"""
    
    TACTIQ_GARBAGE = re.compile(
        r"""^(?:\s*
            (?:tactiq\.io.*|no\stitle\sfound|https?://(?:www\.)?youtube\.com/.*|
             https?://youtu\.be/.*|No\s*text\s*$)
        )""",
        re.IGNORECASE | re.VERBOSE,
    )

    TIME_AT_START = re.compile(r"^\s*\d{2}:\d{2}:\d{2}(?:[.,]\d{1,3})?(?:\s*-\s*\d{2}:\d{2}:\d{2}(?:[.,]\d{1,3})?)?\s*")
    TIME_INLINE   = re.compile(r"\b\d{2}:\d{2}:\d{2}(?:[.,]\d{1,3})?\b")

    out = []
    for line in text.splitlines():
        print(f"Processing line: {repr(line)}")
        if TACTIQ_GARBAGE.match(line):
            print(f"  -> MATCHED TACTIQ_GARBAGE, skipping")
            continue
        # remove leading timestamps
        line = TIME_AT_START.sub("", line)
        print(f"  -> After TIME_AT_START: {repr(line)}")
        # kill orphan timing lines
        if not line.strip():
            print(f"  -> Empty after processing, skipping")
            continue
        # optional: strip inline timecodes like "at 00:03:21,"
        line = TIME_INLINE.sub("", line).strip()
        print(f"  -> After TIME_INLINE: {repr(line)}")
        if line:
            out.append(line)
            print(f"  -> Added to output")
        else:
            print(f"  -> Empty, not adding")
    # collapse repeated spaces created by removing times
    cleaned = re.sub(r"\s{2,}", " ", "\n".join(out)).strip()
    print(f"Final result: {repr(cleaned)}")
    return cleaned

# Test with the same text
test_text = """# tactiq.io free youtube transcript
# No title found
No text

00:00:00.000 --> 00:00:03.000
I learned how to use Perplexity for you. So, here's the Cliffnotes version to save you the hours and hours that I've spent digging into this tool, which I have realized has become one of my top three AI tools that I use literally multiple times a day.

00:00:03.000 --> 00:00:06.000
People usually like to describe Perplexity as like chatbt plus search, but it is actually so much more than that.

00:00:06.000 --> 00:00:09.000
So, in this video, I'm going to show you guys the core features of Perplexity, including its intelligent search capabilities.

https://youtube.com/watch?v=test123
"""

print("Testing clean_paste function:")
print("=" * 50)
result = clean_paste(test_text)
print("=" * 50)
print("Final cleaned result:")
print(result)
