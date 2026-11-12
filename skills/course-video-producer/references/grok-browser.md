# Grok Imagine browser runbook

## Evidence and freshness

UI labels in this runbook were last verified in September 2026. The Grok interface changes often, so re-inspect the live page on every run before relying on any label or position.

Official [reference-to-video documentation](https://docs.x.ai/developers/model-capabilities/video/reference-to-video), checked 9 September 2026, distinguishes identity/object references from an image that fixes the opening frame. Its API describes preset voices and limits that do not establish what a particular web subscription exposes. Do not substitute API syntax such as `<IMAGE_0>` for browser @reference chips. Browser subscription and paid API are separate workflows.

## 1. Prepare assets and establish the session

- Read the current script and verified demos before opening the generator. Create one explicit scene ID per unique teaching fragment.
- Inspect the actual portrait, logo and studio image. Confirm rights to the likeness and supplied media. Do not infer a voice identity from a photograph.
- Keep a reference registry with local relative path, SHA256, intended role, actual saved browser name and thumbnail evidence. A useful project set is `Azhar` (Character), `CourseStudio` (Location), `Logo` (Prop or image reference).
- Open the user's already authorized browser using its available browser skill/tool. List tabs first, then open `https://grok.com/imagine`. Confirm account access without exporting credentials. If signed out, request manual sign-in; continue independent local preparation, not generation.
- Take a screenshot and a fresh accessibility/DOM snapshot. Use visible labels and fresh references for clicks. Do not automate hidden provider APIs or reproduce session cookies.

## 2. Register a reusable reference

The observed path was the **plus / Upload** button beside the composer, then **References**, then **+ New** or **Upload media**. Exact labels can differ.

1. Open the plus picker and choose References, not Generations or an unrelated prior upload.
2. Inspect existing cards first. Match thumbnail AND name to the local registry. Reuse a correct saved reference, avoiding duplicate names that select the wrong person.
3. If missing, choose New/Upload media and use the native file chooser to select the approved local image. Wait for its thumbnail to finish loading.
4. If a name field appears, assign a short distinct name such as `Azhar`, `CourseStudio`, `Logo`. The UI may display these as `@Azhar` etc. Use the resulting name, not an assumed alias.
5. If a role selector appears, use Character for the person; Location/Background for the set if offered; Prop/Object for a logo/object if offered. If no role UI is present, do not invent one: specify the role explicitly in the prompt and record that it is prompt-directed.
6. Save using the actual displayed control. Verify the reference is now visible in the library with the intended thumbnail/name. Cancel if another person's card is selected. Never rename/delete unrelated existing references.

Character is **who**. Location is **where**. Prop is **what object**. A starting image is **the opening composition**. These are not interchangeable. Uploading a portrait as the starting frame can preserve its cafe/room even when the prose requests a new studio.

## 3. Attach references to THIS generation

1. Start a clean Imagine composer for a new shot. Do not paste a new scene into a previous result's edit/extend box unless continuation is intentional.
2. Select the saved references through the picker. If the editor offers @autocomplete, choose the matching existing card from that list rather than leaving a plain `@name` string.
3. Check the actual attached chips/thumbnails in the composer. A reference name mentioned only in prose is not attachment evidence.
4. Clear stale prompt text using focus, select-all and delete where necessary. Reinspect the editor after every reference insertion: previous runs retained old words alongside newly filled text. If clearing removed chips, reattach them and verify again.
5. Explicitly map the selected references at the start of the prompt. With a portrait and a separate set, say: use the portrait for identity/clothing only; discard its location; the studio reference determines the background from frame zero. Ignore any generated branding inside the studio picture and use the original logo instead.

## 4. Set native generation controls

| Control | Select and verify | Do not assume |
|---|---|---|
| Mode | Video, not Image or Agent, for this short-shot workflow | A prompt saying video selects Video mode |
| Aspect ratio | The requested ratio, normally 16:9 for a course | Uploading a portrait implies landscape |
| Duration | A duration the current UI offers; observed course setting was 15s | Every account allows 15s or 25s |
| Resolution | The actual native option selected; observed reference shots were 720p | Typing 1080p upgrades a 720p result |
| Audio | Enabled for spoken presenter scenes; verify the audio/voice control | A speaker icon always means generation audio rather than playback mute |
| Voice | Reuse an explicitly approved saved voice if actually available | An image, preset name or repeated prose locks a speaker |
| References | Exact chips for this shot | Last post's references carry over |
| Quota | Read the current visible usage and reset message | Ten simultaneous jobs are supported |

Record selected settings with the scene submission. If the requested option is absent, choose an explicitly allowed fallback or report the incompatibility before spending credits. Do not buy an upgrade or switch to the paid API.

## 5. Pilot, submit and reconcile

- For a new voice/set, generate two or three DIFFERENT short lesson fragments only when authorized. Compare actual voice, pronunciation, mic character and face across them. An owner-approved sample becomes an immutable local target with a file hash and relevant time range.
- Use the detailed example in `prompt-example.md`. Estimate words against speaking time, then measure the actual output. Split at complete ideas instead of asking a speaker to rush.
- Before clicking Generate/Submit, record scene ID, attempt, prompt hash, references, settings and `submitting` in a job ledger. One browser controller owns the composer.
- Click once. Capture the returned post/conversation URL and visible generation state. On timeout or interruption, inspect existing Generations/history before retrying. Unknown submission outcome is not permission to create a duplicate.
- Wait for the completed player and native Download action. Save via the browser's supported download mechanism. Keep repeated provider filenames in unique scene/attempt folders, then ingest and hash them immediately.
- A post URL is not a download. A downloaded MP4 is not an accepted clip. Keep `planned`, `submitting`, `submitted`, `downloaded`, `review_pending`, `accepted`, `rejected` and `blocked` distinct in the separate job ledger. The renderer manifest has its own simpler status fields.

## 6. Optional extension

Only extend an approved shot when continuity genuinely helps. Inspect its actual Extend/Continue controls and any offered additional duration. Record whether the downloaded result includes the base prefix or contains only the new tail. Never promise that 15s + 10s is available merely because an earlier UI offered it.

Compare the last seconds of the base with the extension's first spoken words. The owner reported changed audio in a 10-second extension. Check speaker, pitch, accent, room sound, lip sync and repeated dialogue. If changed, keep the extension rejected and create a new authorized independent shot; do not blend two different speakers and call the voice fixed.

If the result contains base + tail, either use that combined result once, or use explicit non-overlapping trims. Do not concatenate both the original base and the entire extended file. Different encoded hashes can still contain the same words/frames, so inspect content and retain lineage.

## 7. Optional batches and safe stopping

Batch size and interval are inputs, not service facts. If asked for 10 jobs every 120 seconds: reconcile completions first; count actual in-flight jobs; submit only distinct ready scenes up to the requested/observed capacity. Never have multiple agents manipulate the same composer. Use the host's supported scheduled continuation only if the user requested recurring operation, with one existing task rather than duplicates.

Retry budget defaults to two attempts per scene. Stop submitting on quota exhaustion, challenge, ambiguous job state, unavailable required references or owner pause. Record the displayed reset time including whether its timezone is known. Preserve downloaded work and the next unsubmitted scene. Pausing generation may still allow a separately requested review assembly, never an automatic public release.
