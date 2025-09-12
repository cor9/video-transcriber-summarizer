import google.generativeai as genai
import os

MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro-latest")

def init_gemini():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing")
    genai.configure(api_key=key)
    return genai.GenerativeModel(MODEL)

_PROMPTS = {
    "bullet_points": "Summarize the transcript as sharp bullet points with timestamps when obvious. Keep to 10 bullets.",
    "key_insights": "Extract 5-7 key insights, each with a short supporting quote from the transcript.",
    "detailed_summary": "Write a detailed, sectioned summary with headings and 2-3 sentence paragraphs."
}

def summarize(transcript_text: str, summary_format: str, context_hints: list[str] | None = None) -> str:
    model = init_gemini()
    style = _PROMPTS.get(summary_format, _PROMPTS["bullet_points"])
    context = "\n".join([f"- {c}" for c in (context_hints or [])])
    sys = f"""You are a senior content editor.
Quality bar: clear, factual, concise. No fluff. Preserve the creator's claims carefully.
Context hints (may inform emphasis):
{context if context else '- None'}
Output must be Markdown."""
    prompt = f"{style}\n\nTranscript:\n{transcript_text[:120000]}"  # stay under limit
    resp = model.generate_content([{"role":"user","parts":[sys]}, {"role":"user","parts":[prompt]}])
    return resp.text or ""
