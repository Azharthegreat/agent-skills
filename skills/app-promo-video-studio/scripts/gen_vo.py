# -*- coding: utf-8 -*-
"""
gen_vo.py - generate per-line voice-over mp3s with edge-tts (free Microsoft neural TTS).

Usage:
    python gen_vo.py <vo_spec.json> <out_dir>

vo_spec.json:
    { "voice": "en-US-AvaNeural", "rate": "+8%", "lines": ["line 1", "line 2", ...] }

Outputs l1.mp3 .. lN.mp3 in <out_dir>.

Known good voices:
    English : en-US-AvaNeural  (warm female). Alt: en-US-AriaNeural, en-US-GuyNeural (male).
    Urdu    : ur-PK-UzmaNeural (female). Alt: ur-PK-AsadNeural (male).

GOTCHAS (both are load-bearing on Windows):
1. edge-tts on Windows throws "aiodns needs a SelectorEventLoop". Fix: set
   WindowsSelectorEventLoopPolicy BEFORE importing edge_tts (done below).
2. The TTS endpoint intermittently returns HTTP 403 (WSServerHandshakeError). Retry each line
   a few times with a short sleep; it almost always succeeds within 2-4 tries.
3. edge-tts needs network. If offline/blocked, this is the ONLY blocked component - still produce
   scenes, music and the silent cut, and report the missing VO rather than faking it.
"""
import sys, os, json, asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import edge_tts

spec = json.load(open(sys.argv[1], encoding="utf-8"))
OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
VOICE = spec.get("voice", "en-US-AvaNeural"); RATE = spec.get("rate", "+6%")

async def main():
    for i, text in enumerate(spec["lines"], 1):
        for attempt in range(5):
            try:
                await edge_tts.Communicate(text, VOICE, rate=RATE).save(os.path.join(OUT, f"l{i}.mp3"))
                print("ok", i); break
            except Exception as e:
                print("retry", i, attempt, str(e)[:50]); await asyncio.sleep(2)
        else:
            print("FAILED line", i, "- report missing VO, do not fake it")

asyncio.run(main())
