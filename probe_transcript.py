# probe_transcript.py
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    CouldNotRetrieveTranscript,
    VideoUnavailable,
    TooManyRequests
)

VIDEO_URL = "https://youtu.be/9eYKbppNbk8?si=vmfwT6GPyrOr78Gp"

import re
from urllib.parse import urlparse, parse_qs

def extract_video_id(url: str):
    u = urlparse(url)
    qs = parse_qs(u.query)
    if "v" in qs and qs["v"]:
        return qs["v"][0][:11]
    if "youtu.be" in (u.netloc or "").lower():
        seg = (u.path or "").strip("/").split("/")[0]
        return seg[:11] if seg else None
    m = re.search(r"/(?:embed|v|shorts)/([0-9A-Za-z_-]{11})", u.path or "")
    if m: return m.group(1)
    m = re.search(r"([0-9A-Za-z_-]{11})", u.path or "")
    return m.group(1) if m else None

def fetch_captions_smart(video_url, prefer_langs=("en","en-US","en-GB"), fallback_translate_to="en"):
    vid = extract_video_id(video_url)
    diag = {"video_id": vid, "step": None, "chosen": None, "langs_found": [], "generated": None, "translated": False}
    if not vid:
        return None, {**diag, "reason":"no_video_id"}

    # Step 1: direct preferred
    try:
        diag["step"] = "direct_preferred"
        entries = YouTubeTranscriptApi.get_transcript(vid, languages=list(prefer_langs))
        text = "\n".join(e.get("text","") for e in entries if e.get("text")).strip() or None
        if text:
            diag["chosen"] = "preferred_direct"
            return text, diag
    except (NoTranscriptFound, TranscriptsDisabled):
        pass
    except Exception as e:
        diag["direct_error"] = str(e)

    # Step 2: list & choose
    try:
        diag["step"] = "list_transcripts"
        tlist = YouTubeTranscriptApi.list_transcripts(vid)
        for t in tlist:
            diag["langs_found"].append({
                "language": t.language_code,
                "is_generated": t.is_generated,
                "is_translatable": t.is_translatable
            })

        def rank(t):
            try:
                pref_index = list(prefer_langs).index(t.language_code)
            except ValueError:
                pref_index = len(prefer_langs) + 1
            manual_bonus = 0 if not t.is_generated else 1
            return (pref_index, manual_bonus)

        cands = sorted(list(tlist), key=rank)

        # 2a) same-language
        for c in cands:
            if c.language_code in prefer_langs:
                txt = "\n".join(x.get("text","") for x in c.fetch() if x.get("text")).strip() or None
                if txt:
                    diag["chosen"] = {"language": c.language_code, "is_generated": c.is_generated}
                    diag["generated"] = c.is_generated
                    return txt, diag

        # 2b) translate if allowed
        if fallback_translate_to:
            for c in cands:
                if getattr(c, "is_translatable", False):
                    try:
                        t = c.translate(fallback_translate_to).fetch()
                        txt = "\n".join(x.get("text","") for x in t if x.get("text")).strip() or None
                        if txt:
                            diag["chosen"] = {"language": c.language_code, "is_generated": c.is_generated}
                            diag["generated"] = c.is_generated
                            diag["translated"] = True
                            return txt, diag
                    except Exception as te:
                        diag.setdefault("translate_errors", []).append(str(te))

        # 2c) any manual → any generated
        any_manual = [t for t in tlist if not t.is_generated]
        any_generated = [t for t in tlist if t.is_generated]
        for bucket in (any_manual, any_generated):
            for c in bucket:
                try:
                    txt = "\n".join(x.get("text","") for x in c.fetch() if x.get("text")).strip() or None
                    if txt:
                        diag["chosen"] = {"language": c.language_code, "is_generated": c.is_generated}
                        diag["generated"] = c.is_generated
                        return txt, diag
                except Exception as fe:
                    diag.setdefault("fetch_errors", []).append(str(fe))

        return None, {**diag, "reason":"no_working_track"}

    except TranscriptsDisabled:
        return None, {**diag, "reason":"captions_disabled"}
    except NoTranscriptFound:
        return None, {**diag, "reason":"no_transcripts"}
    except TooManyRequests:
        return None, {**diag, "reason":"rate_limited"}
    except VideoUnavailable:
        return None, {**diag, "reason":"video_unavailable"}
    except CouldNotRetrieveTranscript:
        return None, {**diag, "reason":"retrieve_failed"}
    except Exception as e:
        return None, {**diag, "reason":f"unexpected:{e}"}

if __name__ == "__main__":
    txt, di = fetch_captions_smart(VIDEO_URL)
    print("DIAG:", di)
    if txt:
        print("\nFIRST 600 CHARS:\n", txt[:600])
    else:
        print("\nNO TEXT. REASON:", di.get("reason"))
