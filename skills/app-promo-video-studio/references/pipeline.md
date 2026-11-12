# Production pipeline

Proven end to end on the Astra Phone Directory promo (10 Oct 2026). Follow the stages in order.
Discover tool paths at runtime; do not hardcode them in repo files (the repo lives at a different
drive on each machine). Verify with `which ffmpeg` / `emulator -list-avds` first.

## 0. Decide the angle and gather real data

- One marketing promise, 3 to 5 proofs. Never invent features, numbers, awards or claims.
- Prefer stills + motion graphics over raw emulator `screenrecord`: emulator screen recording is
  choppy (~2-3 fps) and looks stuttery. Capture crisp PNG stills and animate them in post.
- Use ONLY safe demo data in a public video. Fabricated demo accounts (random names/avatars, fake
  CNICs) are fine. NEVER show a real private person's number or the owner's own number. If the
  app returns live third-party data, pick records that are clearly demo/seed, or get the exact
  demo account set from the user.

## 1. Capture (Android emulator)

1. Set a clean status bar: `scripts/set_demo_statusbar.sh` (fixed 12:00, full battery/signal,
   no notifications).
2. Disable ads for a clean feature demo where possible (a debug build without the test-ads flag,
   or a tier that does not show ads). An ad in the middle of a result card ruins the frame.
3. Screenshot with `adb -s <serial> exec-out screencap -p > shot.png`.
4. MANDATORY: prefix any command touching `/sdcard/` with `MSYS_NO_PATHCONV=1`. Git Bash rewrites
   `/sdcard/clip.mp4` into `C:/Program Files/Git/sdcard/...` and the command fails silently
   ("Must specify output file", "failed to stat remote object").
5. Show the WHOLE data card in each shot. The user's rule: do not cut any field. Scroll so the
   full card (name, operator, line type, city, address, masked id, etc.) is visible, then crop
   to just the white card for the scene.
6. Capture gotcha: the result card's scroll position shifts with the length of any "recent
   searches" list below it. Clear recent searches between captures (or tune the swipe per card)
   so framing is consistent. Crop each card with its own coordinates and verify each by eye.
7. Account/data tier: an app can show different data to different account tiers. Capture with a
   demo account that shows only fictional records, and verify which account is active by a test
   lookup before assuming.

## 2. Compose scenes (PIL, 1080x1920)

- `scripts/make_scenes.py <spec.json> <assets_dir> <out_dir>` renders `s1.png..sN.png`.
- Scene grammar that worked: hook (incoming-call mock, "Who's calling?") -> screenshot (home,
  "One number. Full identity.") -> one `card` scene per demo record (caption = "PROFESSION - CITY",
  full card, brand strip) -> statement (capability list) -> cta (icon, "Free on Google Play",
  honest disclosure lines).
- Brand blue gradient for hook/statement/cta; light gradient for card/screenshot. Soft drop
  shadow under each card. Fonts: Arial Black for headlines, Arial Bold/Regular for body.
- No em dashes anywhere. Keep the card fully visible. Captions short.
- The CTA MUST carry the honest lines (e.g., "Listings come from a third-party directory. Your
  number can be removed on request.").

## 3. Voice-over (edge-tts, English AND Urdu)

- `scripts/gen_vo.py <vo_spec.json> <out_dir>` -> `l1.mp3..lN.mp3`, one line per scene.
- English voice `en-US-AvaNeural` (rate +8%), Urdu `ur-PK-UzmaNeural` (rate +6%). Male alts:
  `en-US-GuyNeural`, `ur-PK-AsadNeural`.
- Write Urdu as natural Urdu, not a word-for-word translation. Same message, both languages.
- Two Windows gotchas are handled in the script and must stay: the SelectorEventLoop fix (edge-tts
  dies otherwise with "aiodns needs a SelectorEventLoop"), and retry on intermittent HTTP 403.
- edge-tts needs network. If it is blocked, ship scenes + music + the timecoded scripts and say
  the synthesized voice is the only blocked part. Never fake it.

## 4. Music bed (synthesized, continuous, loud enough)

- `FFMPEG=<ffmpeg> scripts/build_music.sh <out.wav> <seconds>`. Pass a few seconds MORE than the
  sum of scene durations.
- Two hard-won rules baked into the script:
  - CONTINUOUS: chords are acrossfaded, never faded to silence between them. Per-chord fade-outs
    create dips that sound like the track keeps cutting.
  - LOUDNORM to -16 LUFS: a raw sine pad sits near -25 dB and is completely masked by a continuous
    voice-over. The old reused `music.wav` was effectively silent (-69 dB) and the user heard no
    music at all. Always loudnorm, then verify with `ffmpeg -i bed.wav -af volumedetect -f null -`
    (mean should be about -15 dB).

## 5. Assemble (auto-timed)

- `python scripts/build_video.py --scenes <dir> --vo <dir> --music <wav> --out <mp4>
  --ffmpeg <ffmpeg>`.
- It sets each scene duration to `max(min, vo_line_duration + pad)` so EN and UR both fit without
  manual retiming, computes xfade offsets, places each VO line at its scene start, and mixes music
  (volume 0.85 after loudnorm) under the voice with `amix normalize=0` + `alimiter`.
- Because the voice is near-continuous, the music must be audible UNDER it, not just in gaps. The
  0.85 volume on a -16 LUFS bed gives roughly a 10 dB voice-over-music separation: present but not
  competing.
- Verify every render: duration, `volumedetect` (overall mean about -15 dB means music is really
  in the mix), and eyeball frames from the hook, a card, the statement and the CTA.

## 6. Exports

- Master is 1080x1920 (9:16). That one file serves YouTube Shorts, TikTok, Instagram Reels and
  Facebook Reels directly.
- If a 16:9 or 1:1 cut is requested, re-run the assembler against scene frames rendered at that
  size (or pad/letterbox), do not stretch.
- Always also produce a custom thumbnail: `scripts/make_thumbnail.py` (see publishing.md).

## Reusing the Astra example

`examples/` carries the exact spec, scene list and VO lines from the shipped Astra video. Copy it,
swap the app name, screenshots, demo records, CTA and disclosure lines, and re-run the four scripts.
