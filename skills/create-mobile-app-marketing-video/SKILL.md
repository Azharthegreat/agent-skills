---
name: create-mobile-app-marketing-video
description: Turn mobile-app screenshots, screen recordings, logos, feature notes, and store links into polished marketing videos with storyboards, phone mockups, motion graphics, Urdu and English voice-over, subtitles, music, sound design, platform-specific exports, and quality assurance. Use when Codex must create or plan an app promo, Play Store video, Facebook or Instagram ad, Reel, TikTok, YouTube demo, feature launch, or bilingual product video from raw mobile captures. Prefer a connected professional video-rendering or voice provider when available; otherwise build a reproducible local Remotion or FFmpeg workflow and clearly identify any missing voice-generation dependency.
---

# Mobile App Marketing Video

Produce a finished video package, not only a script. Preserve the real app UI and represent features truthfully.

## Intake

Collect or infer the following without blocking on optional choices:

- app name, logo, store URL, target audience, campaign goal, required CTA
- screenshots and screen recordings, with each file's intended feature if known
- output platforms, duration, language versions, brand colors, music preference
- Urdu and English voice gender, energy, accent, and pronunciation notes

If voice preferences are missing, create voice-ready scripts and choose a neutral, warm commercial direction. Keep the voice choice configurable until synthesis.

## Production workflow

1. Inventory every input. Inspect dimensions, orientation, duration, frame rate, audio, dead time, status-bar content, accidental notifications, personal data, and visual defects.
2. Define one marketing promise and three to five supporting features. Do not invent capabilities, security claims, awards, statistics, testimonials, pricing, or availability.
3. Build a timecoded storyboard before editing. Use a hook, problem, product reveal, feature proof, benefit, trust point, and CTA. Read [references/story-and-timing.md](references/story-and-timing.md).
4. Choose the strongest capture for each spoken claim. Prefer visible proof over decorative stock footage.
5. Clean screen recordings non-destructively: trim idle sections, crop irrelevant borders, hide personal data, normalize orientation, and retain readable UI timing.
6. Present mobile captures inside tasteful device frames when useful. Use direct full-screen capture when readability matters more than mockup styling.
7. Add purposeful motion only: smooth crop movement, restrained zoom, callout tracking, clean transitions, and text timed to the demonstrated feature. Avoid template-like visual noise.
8. Write separate Urdu and English voice-over scripts from the same verified message architecture. Do not mechanically translate. Read [references/bilingual-voice.md](references/bilingual-voice.md).
9. Generate one language per master version unless the user explicitly wants mixed bilingual narration. Pronounce brand and technical terms consistently.
10. Add burned-in captions and subtitle files. Match caption language to narration; use readable line lengths and safe margins.
11. Select licensed or user-supplied music. Keep speech intelligible, duck music beneath narration, use short sound effects sparingly, and avoid copyrighted commercial tracks without authorization.
12. Render a review master, inspect it fully, fix defects, then export requested platform variants. Read [references/render-and-qa.md](references/render-and-qa.md).

## Tool routing

- Prefer a connected Remotion workflow for reproducible layouts, timelines, device frames, captions, and multi-format renders.
- Prefer a connected professional voice provider such as HeyGen when the user wants generated Urdu and English voice-over and the provider supports the selected voice.
- Use image generation only for supporting backgrounds, abstract visual assets, or device-scene mockups. Never replace genuine app screens with invented UI.
- Use local FFmpeg and the available runtime for media inspection, trimming, scaling, audio mixing, captions, and encoding when external video tools are unavailable.
- If no speech-synthesis capability is available, still produce the finished edit project, exact timecoded scripts, pronunciation guide, and voice placeholders; state that synthesized voice audio remains the only blocked component.

## Required deliverables

Create as applicable:

- final MP4 for each requested language and aspect ratio
- clean master without burned-in captions when useful
- SRT or VTT captions
- Urdu and English scripts with timings and pronunciation notes
- storyboard or shot list
- editable Remotion/project source or reproducible render manifest
- media inventory and licenses/attribution note
- thumbnail or cover frame when requested

Use clear filenames such as `app-campaign-urdu-9x16.mp4` and `app-campaign-english-16x9.mp4`.

## Quality bar

- Make the first two seconds immediately understandable without audio.
- Keep UI text readable on a phone screen at normal playback size.
- Cut on meaning, not merely on a fixed beat grid.
- Avoid long logo intros, fake reviews, excessive glow, random transitions, tiny captions, and generic AI imagery.
- Remove or mask phone numbers, emails, notifications, account names, photos, and other unintended personal data.
- Never distort the app screen to fit a device frame.
- Preview the complete video with sound and render at least representative frames from the opening, middle, CTA, and every aspect-ratio variant.

## Default platform set

When the user asks for a general marketing package without platform details, prepare:

- 9:16 vertical, 1080x1920, 20 to 30 seconds
- 1:1 square, 1080x1080, 20 to 30 seconds
- 16:9 landscape, 1920x1080, 30 to 45 seconds

Treat these as editable defaults, not rigid requirements.
