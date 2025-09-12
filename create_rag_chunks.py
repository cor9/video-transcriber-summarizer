#!/usr/bin/env python3
"""
Convert the Perplexity AI summary into RAG-ready chunks
with proper IDs, metadata, and vector store format
"""

import os
import json
import re
from pathlib import Path

def extract_metadata_from_header(content):
    """Extract metadata from the header comments"""
    metadata = {}
    lines = content.split('\n')
    
    for line in lines[:10]:  # Check first 10 lines
        if line.startswith('# '):
            if ':' in line:
                key, value = line[2:].split(':', 1)
                metadata[key.strip()] = value.strip()
    
    return metadata

def split_into_chunks(content):
    """Split content into logical chunks based on headings"""
    chunks = []
    
    # Split by main headings (## 1., ## 2., etc.)
    sections = re.split(r'^## \d+\.', content, flags=re.MULTILINE)
    
    for i, section in enumerate(sections):
        if not section.strip():
            continue
            
        # Clean up the section
        section = section.strip()
        
        # Skip the header metadata
        if section.startswith('# CONTEXT-TYPE:'):
            continue
            
        # Extract title from first line
        lines = section.split('\n')
        title = lines[0].strip() if lines else f"Section {i}"
        
        # Remove title from content
        content_lines = lines[1:] if len(lines) > 1 else lines
        chunk_content = '\n'.join(content_lines).strip()
        
        if chunk_content:
            chunks.append({
                'title': title,
                'content': chunk_content,
                'section_number': i
            })
    
    return chunks

def create_chunk_metadata(chunk, base_metadata, chunk_id):
    """Create metadata for a chunk"""
    return {
        'id': chunk_id,
        'title': chunk['title'],
        'section_number': chunk['section_number'],
        'content_type': base_metadata.get('CONTEXT-TYPE', 'Meeting Summary'),
        'source': base_metadata.get('SOURCE', 'Tactiq Transcript'),
        'style': base_metadata.get('STYLE', 'Structured with bullets + conclusion'),
        'domain': base_metadata.get('DOMAIN', 'AI Tools / Productivity'),
        'word_count': len(chunk['content'].split()),
        'char_count': len(chunk['content']),
        'chunk_type': 'training_example'
    }

def main():
    """Main function to process the training data"""
    
    # Read the source file
    source_file = Path('training_data/perplexity_ai_summary_example.md')
    
    if not source_file.exists():
        print(f"❌ Source file not found: {source_file}")
        return 1
    
    with open(source_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract metadata
    metadata = extract_metadata_from_header(content)
    print(f"📋 Extracted metadata: {metadata}")
    
    # Split into chunks
    chunks = split_into_chunks(content)
    print(f"📦 Created {len(chunks)} chunks")
    
    # Create output directory
    output_dir = Path('training_data/rag_chunks')
    output_dir.mkdir(exist_ok=True)
    
    # Process each chunk
    all_chunks = []
    
    for i, chunk in enumerate(chunks):
        chunk_id = f"perplexity_summary_{i+1:02d}"
        
        # Create chunk metadata
        chunk_metadata = create_chunk_metadata(chunk, metadata, chunk_id)
        
        # Create chunk document
        chunk_doc = {
            'id': chunk_id,
            'metadata': chunk_metadata,
            'content': chunk['content'],
            'title': chunk['title']
        }
        
        all_chunks.append(chunk_doc)
        
        # Save individual chunk file
        chunk_file = output_dir / f"{chunk_id}.json"
        with open(chunk_file, 'w', encoding='utf-8') as f:
            json.dump(chunk_doc, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Created chunk {chunk_id}: {chunk['title'][:50]}...")
    
    # Save combined chunks file
    combined_file = output_dir / 'all_chunks.json'
    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    
    # Create vector store format (for Pinecone, Weaviate, etc.)
    vector_store_file = output_dir / 'vector_store_format.json'
    vector_docs = []
    
    for chunk in all_chunks:
        vector_doc = {
            'id': chunk['id'],
            'text': chunk['content'],
            'metadata': chunk['metadata']
        }
        vector_docs.append(vector_doc)
    
    with open(vector_store_file, 'w', encoding='utf-8') as f:
        json.dump(vector_docs, f, indent=2, ensure_ascii=False)
    
    # Create summary report
    report_file = output_dir / 'chunking_report.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"""# RAG Chunking Report - Perplexity AI Summary

## Overview
- **Source**: {metadata.get('SOURCE', 'Tactiq Transcript')}
- **Content Type**: {metadata.get('CONTEXT-TYPE', 'Meeting Summary')}
- **Total Chunks**: {len(chunks)}
- **Domain**: {metadata.get('DOMAIN', 'AI Tools / Productivity')}

## Chunk Summary

""")
        
        for i, chunk in enumerate(chunks):
            f.write(f"### {i+1}. {chunk['title']}\n")
            f.write(f"- **ID**: perplexity_summary_{i+1:02d}\n")
            f.write(f"- **Words**: {len(chunk['content'].split())}\n")
            f.write(f"- **Characters**: {len(chunk['content'])}\n")
            f.write(f"- **Preview**: {chunk['content'][:100]}...\n\n")
    
    print(f"\n🎉 RAG chunking complete!")
    print(f"📁 Output directory: {output_dir}")
    print(f"📄 Individual chunks: {len(chunks)} files")
    print(f"📋 Combined file: {combined_file}")
    print(f"🔍 Vector store format: {vector_store_file}")
    print(f"📊 Report: {report_file}")
    
    # Print chunk summary
    print(f"\n📋 Chunk Summary:")
    for i, chunk in enumerate(chunks):
        print(f"  {i+1:2d}. {chunk['title'][:50]:<50} ({len(chunk['content'].split())} words)")
    
    return 0

if __name__ == "__main__":
    exit(main())
