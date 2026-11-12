# Publishing to the four channels

Target channels: **YouTube**, **Facebook (your Page)**, **Instagram**, **TikTok**.
The 1080x1920 master uploads natively to all four (Shorts / Reels / TikTok / FB Reels).

## Non-negotiable rules

1. **Always upload a CUSTOM thumbnail.** Never let the platform auto-pick a frame. Generate both
   with `scripts/make_thumbnail.py` (`thumb_9x16.png` and `thumb_16x9.png`). Match the thumbnail
   orientation to the upload: a **vertical Reel / Short uses the 9:16 `thumb_9x16.png`**; only a
   regular landscape YouTube video uses `thumb_16x9.png`. Since our master is 9:16 and every target
   is a Reel/Short/TikTok, the default thumbnail is `thumb_9x16.png` on all four channels.
2. **Answer the AI / altered-content question truthfully.** These promos are built from real app
   captures and real UI with a synthetic (neural) voice-over. Check each platform's current
   definition: if it covers synthetic voice, disclose it. If you add AI-generated footage or
   people, always disclose.
3. **Draft first, publish only on an explicit yes.** Publishing is outward-facing and irreversible.
   Prepare everything (upload as private/draft, fill metadata, set thumbnail) and get the owner's "go"
   for each platform before making it public. Never auto-publish.
4. **Honest copy.** No invented numbers, claims or reviews. Keep the third-party-directory and
   number-removal disclosure where the caption allows. No em dashes.
5. **One video, adapt per platform.** Tailor caption, hashtags and title to each channel; do not
   paste identical copy to all four.
6. **Urdu captions in ROMAN URDU (Latin script), not Urdu/Nastaliq script.** The Urdu cut's written
   caption, title and description use Roman Urdu ("Ye number kis ka hai? Foran janiye..."); the
   spoken VO stays Urdu.

## Accounts and browser

- Drive the uploads over CDP on the browser that is already signed in (attach to its debugging
  port, do not launch a second instance).
- **If the YouTube channel lives in a different browser profile from your other accounts**, identify
  the right context by a `studio.youtube.com` tab, never a plain `youtube.com` tab: a profile can
  keep a channel tab open for a channel it does not own.
- Facebook Page, Instagram and TikTok: the project's brand accounts. Confirm the logged-in handle
  before posting.
- The CDP upload mechanics (file-input vs file-chooser interception, Lexical/DraftJS caption entry
  via click + Ctrl+A + insertText, and per-platform publish quirks) are the same ones proven for
  this account. If a dedicated upload skill exists (e.g. `youtube-video-seo-publisher`), prefer it
  for YouTube; it preserves the login and avoids native file pickers.
- **Driving it with the Playwright MCP instead of raw CDP** (10 Oct 2026, proven on YT + TikTok +
  IG): `browser_click` times out on YouTube/IG, so use JS `.click()` for buttons; trigger file
  choosers by JS-clicking the hidden `input[type=file]` then `browser_file_upload`; enter Lexical
  captions (IG/FB/TikTok) by dispatching a `beforeinput` InputEvent (fire twice), and YouTube
  title/description by Selection-API `selectNodeContents` + `execCommand insertText`. Full detail
  and clearing a garbled caption: [gotchas.md](gotchas.md) -> Playwright / uploads.

## Per-platform checklist

### YouTube (Short / Reel)
- Upload the 9:16 master. Title with the hook + app name. Description: one-line pitch, feature
  bullets, the Play Store link **with a referrer/UTM tag**, and the disclosure line.
- **Set the custom thumbnail - use the vertical `thumb_9x16.png`** (a Short/Reel is vertical, so
  its thumbnail is 9:16, NOT 16:9). `thumb_16x9.png` is only for a regular landscape upload.
- **Audience / Made for kids: select "No, it's not made for kids".** These promos are for adults;
  always choose No here (it blocks comments and personalization if set to Yes).
- **"Altered or synthetic content":** answer by YouTube's current definition (see rule 2).
- Add relevant tags/hashtags (#CallerID #PhoneDirectory #CallerIDApp etc.) and SEO keywords in the
  description. Leave as Private/Unlisted draft until approved, then Publish.
- After publishing, add the video to the app's playlist (channel keeps one playlist per app).

### Facebook Page - Reel
- Post as a Reel from the Page. Caption with hook + link + 3 to 5 hashtags. Cover = `thumb_9x16.png`.
- Apply Meta's AI label if its current rules cover the synthetic voice-over (see rule 2).
- **Use Meta Business Suite, not the facebook.com Page composer.** The web Page composer turns a
  vertical video into a multi-step "Edit reel" flow that stalls on Next via automation (10 Oct 2026
  run: YouTube/TikTok/Instagram all went through, Facebook had to be skipped). Business Suite ->
  Create Reel posts to the Page reliably.

### Instagram - Reel
- Reel upload, 9:16. Caption + hashtags (IG rewards 3 to 8 tight hashtags). Cover frame =
  `thumb_9x16.png`. AI label per Meta's current rules (see rule 2).

### TikTok
- Upload 9:16. Caption short + hashtags. Cover = `thumb_9x16.png`. Disclose "promotional content"
  only if TikTok requires a commercial-content toggle for ads. Set the AI-generated-content toggle
  per TikTok's current rules for synthetic voice (see rule 2).

## Specs (verify against the live platform; these change)

- Shared base: 9:16, 1080x1920, MP4, H.264/AAC.
- YouTube Shorts <= 3 min; TikTok <= 10 min (verified accounts) / 3 min otherwise; IG Reels 3 to
  90 s on the Reels shelf; FB Reels similar. Our promo is ~30 s, safely within all.

## After posting

- Record each post's URL and the outcome (not just "posted") in the campaign ledger, so the next
  review can compare period to period.
