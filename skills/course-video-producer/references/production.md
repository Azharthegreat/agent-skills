# Detailed direction and quality controls

## Parameter contract

Required input keys:

- `topic`: object with title, module_id, scope, objectives and audience.
- `reference_material`: list of objects with role, path, optional browser_reference and rights note. Include actual images/audio/source material, not only links to a conversation. An image is not a voice model.
- `final_script`: path to exact spoken text for the declared scope.
- `code_demo_assets`: list of path/evidence objects, or an empty list only when no code appears in that scope. Actual module code must have execution evidence.
- `visual_style`: presenter_reference, logo_reference, voice_direction, studio, framing, palette, logo_box and teaching_media. Set presenter-free explicitly if chosen.
- `output`: directory, filename, width, height, fps and duration_rationale. Put retained files and downloads on the owner's requested drive. Do not label upscale as native resolution.
- `generation`: provider, browser_subscription, clip_seconds, retry_limit. Set the limit before dispatch and respect visible quota/permission limits. Never buy around a quota failure.
- `scenes`: ordered records with id, dialogue, objective, medium, visual, beats (time/action/dialogue), and unique coverage IDs. Do not repeat covered text when joining an extended shot.

Production manifest adds file, sha256, job_url, measured_duration, in/out trim times, status, and review evidence per scene. It never stores cookies, access tokens or session exports.

## Detailed prompt standard

Use the structure of the example in `prompt-example.md`, with project-relevant detail rather than copying their campaign:

1. Name the educational purpose and the scene's place in the story. This is not a product teaser or repeated introduction.
2. Map each reference to Character, exact Logo/Prop, voice target or verified visual input. @names are attachment commands, not text to speak/display.
3. Specify the permitted person, reference likeness, age/skin tone/hair/facial hair, outfit, framing, eye contact, blinking, restrained gesture, posture and edit handles. Use consistent pronouns for the presenter character. No generic substitute, beautification or unrequested voice.
4. Explicitly instruct use of the supplied logo once at top-left, static flat 2D, precise proportion/size/margins, original black background, white geometry and red center. No duplicate, redraw, morph, new symbol, glow or 3D reveal. Attach the actual @Logo reference. Empty space is not the normal instruction. Inspect the output and repair exact branding if generation fails; do not claim the provider copied it correctly when editing repaired it.
5. State format, actual selected native resolution, duration, safe areas, consistent light and camera behavior. Avoid unsupported 1080p claims, excessive motion or a permanent talking-head-only layout.
6. State the exact approved voice target, pronunciation, pace, emphasis and pause placement. Do not describe a portrait as a saved voice or silently substitute a preset voice after rejection. No filler, extra speech, soundtrack or second narrator unless requested.
7. Write timed beats with exact dialogue and purposeful visible changes. Finish speech before the cut. Split overlong speech at a complete idea, not arbitrary syllables; measure actual output rather than trusting prompt timing.
8. Define permitted technical text, data and claims. No fake execution results. When the generator cannot reliably reproduce technical writing, use exact authored overlays/diagrams and actual screen capture in editing, with truthful provenance.
9. Add targeted negatives, including identity drift, distorted hands, logo substitutes, invented statistics, unreadable text, duplicated speech and cut-off endings. Give quality priorities that favor learning and correctness over spectacle.

## Lecturer-style visual teaching

The presenter introduces, questions, points and recaps. Alternate with a whiteboard/diagram view, dataset close-ups, editor construction, terminal output, debugging and practice. Do not require the presenter to stand on screen continuously.

On the whiteboard, reveal one idea at a time: records, group membership, numerator, denominator, calculation and interpretation. For six deliveries with late IDs 1, 3 and 6, show the selected IDs before `3 / 6`, then `3 / 6 * 100`, then `50%`. Retain the synthetic-data label and the denominator. These are six teaching records, not evidence of a real courier's performance.

Match gestures and gaze to the authored board reveal where practical. Never claim the generated presenter's hand physically writes exact technical content if it does not. A clean synchronized digital board with accurate writing is preferable to fabricated or malformed marker writing. Do not animate hand contact that does not align.

Use the original program/data for live code, inputs and outputs. Record actual failures and repairs. Authored diagrams may illustrate those verified facts but must not masquerade as a real terminal or app.

## Browser and retry boundaries

The authorized Grok workflow uses the existing signed-in browser, not its separate paid API. Snapshot before actions. Verify References, Character/Prop roles and selected settings in the current UI. Do not edit unrelated account/reference entries.

Clear the contenteditable with select-all/delete, then fill. Re-read the editor after inserting reference chips. It has retained prior text despite a fill call; never submit two competing dialogue blocks. Download completion is required before recording a job as ingested. Preserve each unique file immediately because provider filenames can repeat.

When a reference photograph's background leaks into a newly requested set, do not keep extending that unwanted scene. If the owner requests a fresh post, start from the empty Imagine home composer, attach the character as identity only, explicitly discard the source environment, and describe the required studio from frame zero. Verify the new conversation ID and first/middle/end frames before scaling production. A course test with this combination replaced an unwanted cafe with a studio and teaching board; it did not prove fresh conversation alone was the cause, lock the original voice, or fix generated logos. Preserve the approved voice target separately and review it again after a context reset. Do not impose fresh-post generation on intentional extensions that already satisfy the user's set requirements.

Default maximum is two attempts per scene, then record the unresolved defect and continue independent preparation rather than consuming unlimited generations. A user can change that budget. Never repeat an accepted scene only because the session resumed. Do not bypass login, challenge or quota limits.

## Assembly and delivery

Assemble by manifest order and coverage, not filenames. Validate every path/hash/trim range. Keep base+extension duplication out of the final timeline. Use hard cuts at finished ideas or purposeful short transitions; do not overlap instructional words. Silence is allowed only when it serves reading or practice and is declared.

Normalize dimensions/frame rate without distorting the source. Exact logo/captions must stay readable and away from code. Loudness finishing is a separate mastering step and does not establish speaker identity. Preserve raw sources and intermediate versions.

Draft labels must survive delivery metadata. Final review must include full playback, voice boundaries, words/pronunciation, lip sync, logo geometry, diagrams/code, pauses, chapter boundaries and captions. Have review evidence refer to the current rendered hash. A changed master invalidates earlier final acceptance.

Upload package: rendered MP4, ordered source manifest, exact script/transcript, aligned captions, actual timeline chapters, title, description including applicable synthetic presenter/data disclosure, thumbnail plus source assets and metadata. Verify destination requirements at release time. No public upload or guaranteed watch-hour claim follows automatically from an invocation.
