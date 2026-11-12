# Editing, quality gates and release

## Select the right sources before joining

Keep original downloads immutable. Record a selection for every scene: raw file/hash, chosen edited file/hash, job URL, attempt, approved dialogue/coverage, trim in/out, reason for replacement and review evidence. Reject missing IDs, repeated coverage, reversed order and overlapping source ranges. Matching hashes catch identical files; they do not catch a re-encoded repeated clip or an extension containing its base. Check those by actual frames and speech.

When branding or generated writing fails, compose the ORIGINAL logo and accurate authored graphics into a separate edited file. Preserve its aspect ratio. Remove/cover the incorrect generated logo at its actual location, then add the original at a stable safe-area location. Do not merely add a correct logo while leaving a wrong one elsewhere. Inspect the first/middle/last frames and every visual reveal. A generated model name or successful overlay command does not prove the asset is exact.

A narration-only diagram insert can preserve the approved source audio while replacing the entire image. A lecturer shot may instead use an authored board overlay. Match the overlay's perspective/occlusion to the set or deliberately use a clean full-screen diagram. Never claim the presenter physically wrote the authored text if the footage does not show that. Keep real code capture provenance separate from explanatory illustrations.

The bundled `produce.py` ingests the chosen file, not magically both raw and corrected variants. Ingest only the selected edited media into a new versioned assembly input/output; preserve its raw-to-edited selection sidecar and reference it in scene evidence. Do not mutate a previously accepted raw file or silently replace the manifest path with an unrelated clip.

## Timing, transitions and sound

1. Listen to every chosen clip with the exact script. Check missing words, extra speech, pronunciation, end clipping and speaker changes. ASR is a useful discrepancy detector but cannot prove voice identity, intelligibility or lip sync. Review regional spelling differences rather than blindly accepting/rejecting them.
2. Choose trims on complete phrases with a small natural handle. Keep declared reading/thinking pauses, remove only surplus tails. Document any deliberate silence. Trim audio and video from the same time origin.
3. Normalize dimensions, sample aspect ratio and frame rate without stretching faces. Convert audio to a common sample rate/channel layout. Use frame-aligned parts and derive chapter timing from encoded parts, not `15 * scene_count`.
4. Prefer clean cuts at finished thoughts. A short dissolve can help a visual change but must not overlap spoken instructional words. Avoid fading every clip to black, which makes a lesson feel repeatedly restarted. The bundled renderer uses hard cuts; authored transitions must be included in selected edits and measured once, not claimed as automatic crossfades.
5. Keep intermediate audio lossless and encode AAC once in the final master to avoid accumulating per-clip AAC priming/padding. Ensure each part's audio duration matches its video frame duration. Verify the full decode, stream durations and every join afterward.
6. Choose a consistent loudness target in the brief, for example approximately -16 LUFS integrated and at most -1.5 dBTP for a stereo speech-led master as a production choice, not a YouTube requirement. Measure first, then use two-pass mastering if correction is needed. Listen again for pumping, noise, clipped consonants and ambience jumps. Loudness normalization does not make different speakers identical. The bundled renderer does NOT perform loudness mastering.
7. If voice changes persist, regenerate only the failed scene within the authorized budget. Replacing all narration or using a different voice requires a changed brief and lip-sync validation. Do not silently change an owner-approved voice.

## Evidence that permits production-ready status

Each scene's `review_evidence` must be a real file relative to the output folder, tied to the selected scene hash and trim range. Include reviewer/tool, date, observations and defects resolved. A string saying `reviewed` is not evidence.

After final render, record `delivery.reviewed_sha256`, `full_playback: pass`, a real review-evidence path and all required review fields. Watch AND hear the whole master at normal speed, including every join. Record timecoded findings for dialogue, voice, identity, lip sync, logo, visuals, captions, chapters, thumbnail, audio mastering and teaching coverage. If a reviewer cannot hear/watch it, keep the relevant fields `not_verified`; never manufacture them to satisfy the helper.

Run a full FFmpeg decode and inspect representative frames plus join-adjacent frames as technical evidence. These complement, not replace, audiovisual review. If a final encode or sound correction changes the master hash, regenerate its delivery measurements and review that new file. Re-run readiness checks after metadata/caption changes too.

The helper's verification is a structural consistency check. Even a passing JSON result is not proof that a reviewer actually listened, or that two different files do not repeat the same content. Preserve the human/agent evidence behind each assertion.

## YouTube-ready package

- Final MP4 and current SHA256; selected-source manifest and measured `timeline.json`.
- `title.txt`, `description.txt` with accurate scope and applicable synthetic presenter/data disclosure.
- `chapters.txt` built from actual section start times. Start at 00:00; if using YouTube chapters, inspect current minimum-count/length rules. Do not create a chapter for every 15-second clip.
- `captions.srt`: align to the actual final audio, check cue timings/readability and terminology. A canonical transcript is not aligned captions; auto-generated captions are not a reviewed substitute.
- `thumbnail.png` plus editable source/reference assets, checked at small display size.
- `upload-metadata.json`: title, description, tags, video hash, channel URL/ID, playlist ID, module order, visibility, language, audience and AI disclosure.
- A release report stating full/partial scope, passed checks, unresolved checks and the authorized publication boundary.

`verify INPUT` does not create these assets or upload them; the agent must produce/review the package. Do not conflate rendered, production-ready, uploaded and published.

## Optional authorized upload

1. Confirm the current user's authorization for THIS artifact, channel and visibility. Creating a video/skill alone does not authorize publishing. If full QA is unavailable, an owner-authorized **Unlisted review** is a separate deliverable clearly labelled partial/draft; keep production-ready false.
2. Open Studio in the authorized account. Inspect channel identity and existing content before upload. Reconcile an existing upload ID after interruption, never upload the same master again simply because a prior call timed out.
3. Check browser file access before starting. Prefer output in the approved project and upload roots. On access denial, request a supported access grant or owner-directed export location. Do not change security policy, use traversal/symlinks or hidden API/file injection. If the owner explicitly asks for an upload copy in another folder, keep the authoritative original, use a unique destination and verify byte-identical hashes. Record that destination as a transfer copy, not a new source project.
4. Create > Upload videos > Select files, then choose the reviewed master. As soon as the UI returns an ID, save `upload-attempt.json` with channel, master hash, ID, intended visibility and status before any retry.
5. Fill title/description/chapters, upload the thumbnail, choose the existing intended playlist/order, language/category, appropriate audience, tags and the current AI use/altered content disclosure. Verify fields after saving. Do not invent a sponsorship or claim a course is complete when this is Part 1.
6. Wait for available copyright/community checks and video processing. On an issue, inspect it; do not blindly choose Publish anyway. Use the authorized visibility, never Public for an Unlisted request. Subscriber notifications are unnecessary for a review copy.
7. Verify saved visibility from Studio or the watch page, correct channel/title, actual resolution options, duration and a brief decoded playback check. Record URL and limitations; do not repeatedly play to inflate engagement.
8. Respect the stop boundary and keep generation paused if requested. Do not activate another module or duplicate a paused scheduler. Publication does not guarantee views, watch hours, monetization eligibility or approval.
