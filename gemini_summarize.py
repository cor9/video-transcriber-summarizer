# gemini_summarize.py
import os, time, re
import google.generativeai as genai

MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

def _retry(fn, tries=5, base=1.5):
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            if i == tries - 1:
                raise
            time.sleep(base ** i)
    raise last

def _chunks(txt, limit=14000):
    out, buf_len, buf = [], 0, []
    for line in txt.splitlines():
        L = len(line) + 1
        if buf_len + L > limit:
            out.append("\n".join(buf)); buf, buf_len = [], 0
        buf.append(line); buf_len += L
    if buf:
        out.append("\n".join(buf))
    return out

def cleanup_transcript(raw: str) -> str:
    if not raw:
        return ""
    # strip "No text" lines and URL headers we injected earlier
    cleaned = "\n".join(
        l for l in raw.splitlines()
        if l.strip() and l.strip().lower() != "no text" and not l.startswith("# http")
    )
    # collapse 3+ newlines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()

def baseline_summary(txt: str, mode: str) -> str:
    if not txt.strip():
        return "No transcript text found."
    suffix = "\n\n(Generated without Gemini — fallback path)"
    if mode == "key_insights":
        return "- Insight 1\n- Insight 2" + suffix
    if mode == "detailed_summary":
        return "Summary unavailable — model not called." + suffix
    return "- Bullet 1\n- Bullet 2" + suffix

def summarize_with_gemini(api_key: str, transcript: str, mode: str) -> str:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL)

    style = {
        "bullet_points": "Write tight bullet points. Include timestamps if explicitly present in the text.",
        "key_insights": "Extract 8–12 key insights. Each insight must be supported by a brief quote or paraphrase from the text.",
        "detailed_summary": "Write a structured, sectioned summary with subheads and short paragraphs."
    }.get(mode, "Write tight bullet points.")

    parts = _chunks(transcript)
    partials = []
    for i, part in enumerate(parts, 1):
        prompt = (
            f"You are summarizing chunk {i}/{len(parts)}.\n\n"
            f"Transcript chunk:\n'''\n{part}\n'''\n\n"
            f"Task: {style}\nOnly use facts present in the text."
        )
        resp = _retry(lambda: model.generate_content(prompt))
        partials.append(resp.text.strip())

    fuse = (
        "Merge, deduplicate, and tighten these partial summaries into one cohesive output:\n\n"
        + "\n\n---\n\n".join(partials)
        + "\n\nReturn only the final summary."
    )
    final = _retry(lambda: model.generate_content(fuse))
    return final.text.strip()
