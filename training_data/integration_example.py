#!/usr/bin/env python3
"""
Example integration of RAG chunks into VidScribe2AI
Shows how to use the training data for better summarization
"""

import json
import os
from pathlib import Path

def load_training_chunks():
    """Load all training chunks from the RAG chunks directory"""
    chunks_file = Path('training_data/rag_chunks/all_chunks.json')
    
    if not chunks_file.exists():
        print("❌ Training chunks not found. Run create_rag_chunks.py first.")
        return []
    
    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    print(f"📚 Loaded {len(chunks)} training chunks")
    return chunks

def find_relevant_chunks(query, chunks, top_k=3):
    """Find the most relevant chunks for a given query"""
    # Simple keyword matching (in production, use proper vector similarity)
    query_lower = query.lower()
    scored_chunks = []
    
    for chunk in chunks:
        score = 0
        content_lower = chunk['content'].lower()
        title_lower = chunk['title'].lower()
        
        # Score based on keyword matches
        for word in query_lower.split():
            if word in content_lower:
                score += content_lower.count(word)
            if word in title_lower:
                score += title_lower.count(word) * 2  # Title matches weighted higher
        
        if score > 0:
            scored_chunks.append((score, chunk))
    
    # Sort by score and return top_k
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [chunk for score, chunk in scored_chunks[:top_k]]

def create_context_prompt(query, relevant_chunks):
    """Create a context-rich prompt using relevant training chunks"""
    
    context_sections = []
    for chunk in relevant_chunks:
        context_sections.append(f"## {chunk['title']}\n{chunk['content']}")
    
    context = "\n\n".join(context_sections)
    
    prompt = f"""You are summarizing a video transcript. Use the following training examples as style guidance for your summary.

TRAINING EXAMPLES:
{context}

QUERY: {query}

INSTRUCTIONS:
1. Follow the structured format shown in the training examples
2. Use clear headings and bullet points
3. Include specific details and examples when relevant
4. Maintain the professional, informative tone
5. Provide actionable insights and key takeaways

Please summarize the transcript following this style guide."""

    return prompt

def enhanced_summarize_with_gemini(api_key, transcript, summary_format, query=""):
    """Enhanced summarization using training chunks for context"""
    
    # Load training chunks
    training_chunks = load_training_chunks()
    
    if not training_chunks:
        # Fallback to regular summarization
        from gemini_summarize import summarize_with_gemini
        return summarize_with_gemini(api_key, transcript, summary_format)
    
    # Find relevant chunks based on query or transcript content
    search_query = query or transcript[:200]  # Use query or first 200 chars of transcript
    relevant_chunks = find_relevant_chunks(search_query, training_chunks, top_k=3)
    
    if relevant_chunks:
        print(f"🎯 Found {len(relevant_chunks)} relevant training examples:")
        for chunk in relevant_chunks:
            print(f"   - {chunk['title']}")
        
        # Create enhanced prompt with context
        enhanced_prompt = create_context_prompt(search_query, relevant_chunks)
        
        # Use the enhanced prompt with Gemini
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Combine enhanced prompt with transcript
        full_prompt = f"{enhanced_prompt}\n\nTRANSCRIPT TO SUMMARIZE:\n{transcript}"
        
        response = model.generate_content(full_prompt)
        return response.text.strip()
    else:
        # No relevant chunks found, use regular summarization
        from gemini_summarize import summarize_with_gemini
        return summarize_with_gemini(api_key, transcript, summary_format)

def example_usage():
    """Example of how to use the enhanced summarization"""
    
    # Example transcript (shortened for demo)
    sample_transcript = """
    Today I want to talk about AI tools for productivity. There are many options available,
    but I want to focus on three main categories: research tools, writing assistants, and
    automation platforms. Each has its strengths and use cases.
    
    For research, tools like Perplexity AI are excellent because they provide source citations
    and can search the web in real-time. This is crucial for getting accurate, up-to-date
    information rather than relying on training data that might be outdated.
    
    Writing assistants like ChatGPT and Claude are great for content creation, but they
    work best when you provide clear context and specific instructions. The key is to
    be specific about what you want and provide examples when possible.
    
    Automation platforms like Zapier and Make.com can connect different tools and
    create workflows that save time on repetitive tasks. The learning curve can be
    steep, but the time savings are significant once you get the hang of it.
    """
    
    # Example query (what the user is looking for)
    query = "AI productivity tools research writing automation"
    
    print("🧪 Testing Enhanced Summarization with Training Data")
    print("=" * 60)
    
    # Load chunks to show what we have
    chunks = load_training_chunks()
    if chunks:
        print(f"📚 Available training chunks: {len(chunks)}")
        for i, chunk in enumerate(chunks[:3]):
            print(f"   {i+1}. {chunk['title']}")
        print("   ...")
    
    print(f"\n📝 Sample transcript: {len(sample_transcript.split())} words")
    print(f"🔍 Query: {query}")
    
    # Find relevant chunks
    relevant_chunks = find_relevant_chunks(query, chunks, top_k=3)
    print(f"\n🎯 Relevant chunks found: {len(relevant_chunks)}")
    for chunk in relevant_chunks:
        print(f"   - {chunk['title']} ({chunk['metadata']['word_count']} words)")
    
    # Show how the enhanced prompt would look
    if relevant_chunks:
        enhanced_prompt = create_context_prompt(query, relevant_chunks)
        print(f"\n📋 Enhanced prompt length: {len(enhanced_prompt)} characters")
        print("Preview:")
        print(enhanced_prompt[:300] + "...")

if __name__ == "__main__":
    example_usage()
