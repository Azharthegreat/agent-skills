# Gotchas (every one of these cost real time; do not relearn them)

## Audio
- **Silent reused music.** A leftover `music.wav` was -69 dB (effectively silent); the user heard
  no music twice. Always `volumedetect` any music file before trusting it, and loudnorm synthesized
  beds to -16 LUFS.
- **Music masked by continuous VO.** The voice-over runs almost gap-to-gap, so music placed quietly
  "in the gaps" is never heard. The bed must be loud enough to sit UNDER the voice (music 0.85 on a
  -16 LUFS bed, voice 1.0). Overall mix mean should land about -15 dB.
- **Choppy/cutting music.** Per-chord fade-to-silence makes the bed stutter. Use acrossfade between
  chords for one continuous pad.

## Voice-over (edge-tts on Windows)
- **"aiodns needs a SelectorEventLoop".** Set `asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())`
  BEFORE importing edge_tts.
- **HTTP 403 WSServerHandshakeError.** Transient endpoint rejection; retry each line 3 to 4 times.
- **Wrong result captured silently.** A search that does not register leaves the previous result on
  screen, so you can capture the wrong person's card (happened with Ayesha -> Bilal). Verify every
  captured card by eye against the number you typed.

## Capture / adb
- **Git Bash mangles `/sdcard/`.** Prefix with `MSYS_NO_PATHCONV=1` or the command fails with
  "Must specify output file" / "failed to stat remote object".
- **emulator `screenrecord` is choppy** (~2-3 fps). Use stills + motion graphics instead.
- **Card framing drifts** with the recent-searches list length. Clear recent between captures; crop
  each card with its own verified coordinates. Never crop out a data field.

## Scenes
- **Show all data.** Each card scene must display every field; the user explicitly rejected cropping.
- **No em dashes** anywhere (chat, scenes, captions, descriptions, commit messages).

## Playwright / uploads
- **File upload allowed roots.** The Playwright MCP only accepts upload paths under its allowed
  roots (its outputs dir and the project dir). Copy the video/thumbnail there before `file_upload`.
- **Deep links bounce to Home** in Play Console / some SPA consoles on a cold navigation; navigate
  within the app via its own nav instead.
- **`browser_click` times out** on YouTube Studio and Instagram elements (never reports "stable").
  Use JS `.click()` via `browser_evaluate` for buttons, menu items, radios and Next/Save/Publish.
- **File chooser trigger:** JS-click the hidden `input[type=file]` (opens the OS chooser, which the
  MCP captures), then `browser_file_upload`. Do NOT also click a "Photo/video"/"Select files"
  button afterward - it opens a SECOND chooser; cancel a stray one with `browser_file_upload` +
  empty `paths`.
- **Lexical / DraftJS caption (Instagram, Facebook, TikTok).** `execCommand('insertText')` does NOT
  reliably insert into an empty Lexical box, and `execCommand('delete')`/range-delete leave it
  intact. What works: `el.focus()`, place a caret with `selectNodeContents(el)` + `range.collapse(false)`,
  then `el.dispatchEvent(new InputEvent('beforeinput',{bubbles:true,cancelable:true,inputType:'insertText',data:cap}))`.
  The FIRST `beforeinput` on a fresh box often no-ops, so fire it twice. To clear a garbled caption:
  JS `selectAll` then press a REAL Delete key (`browser_press_key Delete`), then re-insert once.
  Read `textContent` back after the insert to confirm it is a single clean copy (retries duplicate).
- **YouTube Studio `#textbox` (title / description).** For Urdu / non-ASCII text, or any
  replace-after-a-retry, `execCommand('selectAll')+insertText` failed (kept the old filename or
  appended). What works: `el.focus()` then Selection API `selectNodeContents(el)` then
  `execCommand('insertText', false, text)`.

## Batch cross-posting (Node connectOverCDP)
- **Check each platform's automation terms first, and post at human volume.** These notes are for
  cross-posting your own videos to your own accounts, a few at a time.
- **Fastest reliable path is a Node `playwright-core` script over `chromium.connectOverCDP('http://127.0.0.1:9222')`**, one new tab per video, not the MCP one-by-one. Reuse `browser.contexts()[0]`; `browser.close()` only detaches (Brave keeps running). Log each result to a JSON file and skip ids already `posted` so a re-run resumes.
- **TikTok:** `tiktok.com/tiktokstudio/upload`, `setInputFiles` on `input[type=file]`, caption into `.public-DraftEditor-content` via click + Ctrl+A + Delete + `keyboard.insertText`, poll the Post button until enabled, click Post then "Post now", success = redirect to `/tiktokstudio/content`.
- **Instagram:** open the composer by JS-clicking the clickable ANCESTOR of `svg[aria-label="New post"]` (clicking the svg itself is flaky), then the "Post" menu item; the hidden `input[type=file]` (accept includes video/mp4) appears, `setInputFiles` it; set aspect Original; Next x2; caption into `div[contenteditable][aria-label*="aption"]` via `keyboard.insertText`; click Share.
- **The single most expensive IG trap: do NOT treat "caption box gone" as success.** The instant you click Share the caption box disappears and the dialog shows "Sharing" (a progress screen). Closing the tab there ABORTS the server upload and nothing posts (a whole 38-reel run phantom-"posted" this way). The upload takes ~40s; the dialog only then flips to **"Your reel has been shared."** (dialog also shows "Shared reel" / "Done", and `document.body.innerText` contains "Shared"). Poll `body.innerText` every 2s for `/your reel has been shared|has been shared/i` up to ~150s and close ONLY after it matches. `waitForFunction` on the same predicate proved unreliable in a loop; an explicit poll works.
- **Never wrap the batch in a shell `timeout`** that can kill node mid-share; run it backgrounded with no wrapper, or a kill lands between Share and confirmation and aborts that reel.
- **Verify against the profile, never the script's own status.** IG virtualizes the reels grid (~32 DOM nodes), so collect hrefs by accumulating into a Set DURING scroll, not once at the end. The cleanest single check is the total post count delta on `/<handle>/`.

## Thumbnail
- **A YouTube Short center-crops a 16:9 thumbnail to a narrow ~9:16 strip** in the feed, so a
  left/right layout loses its sides ("WHO'S CALLING?" shows as "'S CALL"). Keep all key content
  inside the central ~405px column of the 1280-wide image (or upload the true 9:16 thumb). Verify by
  cropping the 9:16 centre of the thumbnail and eyeballing it BEFORE upload.
- **Replacing a thumbnail** on an already-published video: open `studio.youtube.com/video/<id>/edit`,
  JS-click the `input[type=file][accept*=image]`, `browser_file_upload` the new one, then Save; the
  newest upload becomes the selected custom thumbnail.

## Data safety
- **Demo accounts only** in a public video. Never broadcast a real private number or the owner's own
  number. Fabricated demo records (random avatars, fake CNICs) are the safe choice.

## Publishing
- **Custom thumbnail always.** **AI disclosure per each platform's current rules** (the voice-over is synthetic).
- **Draft first, publish on explicit yes.** Tag Play builds and record post URLs + outcomes.
- **Urdu captions go in ROMAN URDU, not Urdu script.** The
  written caption/title/description for the Urdu cut uses Latin-script Roman Urdu ("Ye number kis ka
  hai? Foran janiye..."), not نستعلیق. The VO stays spoken Urdu. Posting pure Urdu script first got
  corrected.
- **Facebook page video via the web composer stalls.** facebook.com's Page composer turns a vertical
  video into a multi-step "Edit reel" flow (Add tags -> Trim -> captions -> Next -> Next...) that
  would not advance to Publish via automation. Use **Meta Business Suite** instead. Also: the "Share
  a thought" bubble on the Page is the Notes feature (not a post), and the notifications panel is a
  persistent hidden `div[role=dialog]` that `querySelector` grabs first - select the composer dialog
  by its text ("Create post" + a contenteditable), not the first dialog.
- **YouTube may auto-disable comments** on a freshly published Short. Leave the comment setting to
  the channel owner unless asked.
- **Practical YouTube channel targeting:** if a `studio.youtube.com/channel/<your-channel-id>` tab
  is already open on the attached browser, drive the upload from it (Create -> Upload videos) and
  confirm the left-rail channel name before publishing. That guarantees the right channel without
  a profile switch.
