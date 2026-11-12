---
name: app-promo-video-studio
description: Produce and publish a polished vertical app promo video from Android emulator captures, end to end and reproducibly, for any app (app-agnostic, spec-driven). Captures clean UI stills, composes 1080x1920 motion-graphic scenes, generates English and Urdu neural voice-over, synthesizes a continuous music bed, auto-times and assembles the cut with FFmpeg, builds a custom 9:16 and 16:9 thumbnail, then prepares uploads to YouTube, your Facebook Page, Instagram and TikTok. Use when the user wants an app promo video, marketing video, app ad, app trailer, Play Store or Google Play promo video, app demo, feature launch video, or a vertical social clip, in English or Urdu, shipped to the channels. Keywords and triggers - app promo video, app marketing video, promo reel, YouTube Short, YouTube reel, TikTok video, Instagram Reel, Facebook Reel, app ad, app trailer, app demo video, feature launch, bilingual Urdu and English voiceover, emulator screen-capture video, vertical 9x16 video, custom thumbnail, publish to YouTube Facebook Instagram TikTok, make video for my app, create a reel. Build locally with Python PIL plus edge-tts plus FFmpeg; the only ever-blocked piece is synthesized voice if the network is down.
---

# App Promo Video Studio

Make a finished, honest app promo video from emulator captures, then publish it to YouTube,
your Facebook Page, Instagram and TikTok. Preserve the real app UI; never invent
features, numbers or claims.

**This skill is app-agnostic.** It works for any app. Everything is
spec-driven: a new app is a new JSON spec plus its own screenshots, demo records, CTA, disclosure
lines and voice-over lines - no code changes. The Astra Phone Directory promo (10 Oct 2026) is the
worked reference in `examples/`; copy it and swap the app's content. For each new app, confirm the
one marketing promise, the real feature set, the safe demo data, the Play Store link, and the
honest disclosure lines before producing. Publish to the brand's own YouTube channel, Facebook
Page, Instagram and TikTok; only the per-app YouTube playlist differs between apps.

Reuse the loaded skill within a session. Discover tool paths at runtime (`which ffmpeg`,
`emulator -list-avds`); do not hardcode machine paths, and keep in-repo paths relative.

## Hard rules (do not violate)

- **Only safe demo data in a public video.** Fabricated demo records (random names/avatars, fake
  CNICs) are fine; NEVER a real private person's number or the owner's own. Confirm the demo set
  with the user if the app returns live third-party data.
- **Show every data field.** Each card scene displays the whole card; do not crop out a field.
- **Honest copy.** No invented features, numbers, awards or reviews. Keep the third-party-directory
  and number-removal disclosure in the CTA and captions.
- **No em dashes** anywhere (scenes, captions, titles, descriptions, commit messages). Use "-" or
  split the sentence.
- **Custom thumbnail, always.** Never let a platform auto-pick a frame. For a Reel / Short / TikTok
  (vertical) use the **9:16 `thumb_9x16.png`**; only a landscape YouTube upload uses `thumb_16x9.png`.
  A YouTube Short center-crops a 16:9 thumbnail to a narrow ~9:16 strip, so keep the key content in
  the central ~405px column and verify by cropping the 9:16 centre before upload.
- **Urdu captions/titles in ROMAN URDU (Latin), not Urdu script.** The spoken VO stays Urdu; the
  written caption/title/description for the Urdu cut is Roman Urdu.
- **AI disclosure: be accurate, never automatic.** Read each platform's current definition of
  AI-generated, altered or synthetic content and answer it truthfully. The voice-over is a neural
  (synthetic) voice, so disclose it wherever the platform's rules cover synthetic audio.
- **YouTube "Made for kids": always No.** These promos are for adults.
- **Draft first, publish only on an explicit per-platform yes.** Publishing is outward-facing and
  irreversible; prepare everything private, then wait for the go. Tag the Play build and record
  each post URL + outcome afterward.

## Workflow (six stages)

Full detail in [references/pipeline.md](references/pipeline.md). Scripts live in `scripts/`,
an example spec in `examples/` (add your own screenshots first).

1. **Capture (emulator).** Clean status bar with `scripts/set_demo_statusbar.sh`; screenshot with
   `adb exec-out screencap -p` (prefix `/sdcard/` commands with `MSYS_NO_PATHCONV=1`). Prefer
   stills over `screenrecord` (it is choppy). Clear recent-searches so framing is consistent; crop
   each result card to the whole white card.
2. **Compose scenes.** `python scripts/make_scenes.py <spec.json> <assets_dir> <out_dir>` ->
   `s1.png..sN.png`. Grammar: hook -> home screenshot -> one card per demo record -> capability
   statement -> CTA. See [references/pipeline.md](references/pipeline.md) for the design rules.
3. **Voice-over (EN + UR).** `python scripts/gen_vo.py <vo_spec.json> <out_dir>`. English
   `en-US-AvaNeural`, Urdu `ur-PK-UzmaNeural`. The script carries the Windows SelectorEventLoop fix
   and 403 retry. Write natural Urdu, not a literal translation.
4. **Music.** `FFMPEG=<ffmpeg> scripts/build_music.sh <out.wav> <seconds>` - continuous chord pad,
   loudnormed to -16 LUFS so it is audible under the voice. Pass a few seconds more than the scene
   total. Verify with `volumedetect`.
5. **Assemble.** `python scripts/build_video.py --scenes <dir> --vo <dir> --music <wav>
   --out <mp4> --ffmpeg <ffmpeg>`. Auto-times each scene to its VO line (so EN and UR both fit),
   crossfades scenes, mixes music under the voice. Verify duration, levels and frames.
6. **Thumbnail + publish.** `python scripts/make_thumbnail.py <spec.json> <assets_dir> <out_dir>`
   then follow [references/publishing.md](references/publishing.md) for the four channels (custom
   thumbnail, honest AI disclosure, draft-first, confirm the target channel before upload).

## Quick start (from the example)

```bash
SK=<skills-dir>/app-promo-video-studio   # wherever the skill is installed
FF=$(which ffmpeg); W=<scratch_dir>
python "$SK/scripts/make_scenes.py"   "$SK/examples/video_spec.example.json" "$SK/examples/assets" "$W/scenes"
python "$SK/scripts/gen_vo.py"        "$SK/examples/vo_en.json" "$W/vo_en"
FFMPEG="$FF" bash "$SK/scripts/build_music.sh" "$W/music_en.wav" 33
python "$SK/scripts/build_video.py" --scenes "$W/scenes" --vo "$W/vo_en" --music "$W/music_en.wav" --out "$W/promo_en.mp4" --ffmpeg "$FF"
python "$SK/scripts/make_thumbnail.py" "$SK/examples/video_spec.example.json" "$SK/examples/assets" "$W/thumb"
```

Swap in Urdu by running `gen_vo.py` with `examples/vo_ur.json` into `vo_ur`, rebuilding music a few
seconds longer (Urdu lines run longer), and assembling against `vo_ur`.

## Make it robust and intelligent

- **Auto-timing** (`build_video.py`) sizes each scene to its voice line, so the same scenes render
  clean EN and UR cuts without hand-tuning offsets.
- **Spec-driven** (`make_scenes.py`, `make_thumbnail.py` read one JSON), so a new app is a new spec
  plus fresh screenshots, not new code.
- **Verify every stage**: capture by eye (right record, all fields), music `volumedetect` (~-15 dB
  mean = really in the mix), final render (duration + levels + frames from hook/card/statement/CTA).
- **Fail honestly**: if edge-tts is network-blocked, ship scenes + music + timecoded scripts and
  name the voice as the only blocked part. Never fake voice, data, or claims.

## References

- [references/pipeline.md](references/pipeline.md) - capture, scenes, VO, music, assembly in detail.
- [references/publishing.md](references/publishing.md) - the four channels, custom thumbnail, no-AI
  rule, accounts/profiles, per-platform checklist, draft-first gate.
- [references/gotchas.md](references/gotchas.md) - every trap that cost time (silent music, masked
  music, edge-tts Windows fix, `/sdcard` path mangling, card framing drift, upload roots).
- [examples/](examples/) - the reference spec and EN/UR voice-over lines; screenshots are not shipped.
