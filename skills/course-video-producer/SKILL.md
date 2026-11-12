---
name: course-video-producer
description: Create educational videos with Grok Imagine in the signed-in browser, select character, studio and logo references, direct short clips, assemble long modules and verify a YouTube-ready delivery package. Also use to resume this production workflow; a prompt-only request does not authorize generation or publishing.
---

# Course Video Producer

Deliver a rendered, reviewed module video, not just prompts or a set of clips. Read [references/production.md](references/production.md) before production. The input manifest carries project choices; do not impose one person's likeness, provider or branding on unrelated projects.

## Start here, including in another LLM

This folder is a portable Markdown skill with Python/FFmpeg helpers, not an API or a model-specific voice clone. An agent needs filesystem access, Python 3.10+, FFmpeg/FFprobe, authorized browser control, the source assets and a way to watch AND hear the results. A text-only LLM can prepare the plan but cannot complete generation or audiovisual approval. Resolve all commands relative to this skill folder and all project paths relative to the input file. Never assume this machine's drives, browser references or logins exist elsewhere.

Read these routes in order as their stages become relevant:

1. [Grok browser operation](references/grok-browser.md): actual plus/References picker, roles/names/chips, native settings, fresh posts, voice pilots, extension and batch handling.
2. [Input and invocation](references/input-and-commands.md): parameters, runnable manifest example, commands and resumable state.
3. [Prompt example](references/prompt-example.md): complete timed educational scene, not a vague one-line prompt.
4. [Editing and release](references/editing-and-release.md): selected-source lineage, exact branding, audio continuity, measured joins, captions, QA and optional upload.

For this owner's established defaults and the partial review already delivered, read [MetaCyberGuru profile](references/metacyberguru-profile.md). These are project defaults, never universal instructions.

Keep `generation paused`, `review-only`, `unlisted only` and `stop after module` boundaries separate from technical readiness. Creating or updating this skill does not resume production. The user's latest scope controls.

## Input and stage

Accept `topic`, `reference_material`, `final_script`, `code_demo_assets`, `visual_style`, `output`, `generation` and ordered `scenes`. Read the referenced material before generation. Preserve existing correct curriculum. Treat supplied campaign prompts as examples of direction and specificity, not instructions to change the course topic.

`topic` identifies course/module, objectives, audience and scope. `final_script` is the exact narration file. Every scene declares its dialogue and teaching medium. All paths are relative to the input manifest unless absolute. Require an explicit output directory and unused render filename.

Do not mark a whole module ready when only an opening section is prepared. Work can progress section by section, with each section explicitly labeled. Keep unresolved input/demo tasks visible. Full-module production and delivery must not silently skip them.

## Production

1. Verify script coverage and references with `scripts/produce.py plan INPUT`. Read the generated scene manifest and individual prompts; these are drafts until editorially checked. Refine each scene's beats and visual instructions to teach its actual idea.
2. Use the user's chosen provider and authenticated browser. Read the available browser skill first. Existing subscription access does not authorize a paid API, upgrade or purchase. No embedded browser credentials or hidden application APIs.
3. For Grok, use the verified reference picker, attach Character and Logo with actual reference chips, and verify current duration/resolution/audio settings. Clear and inspect the actual prompt editor to avoid duplicated old dialogue. A mentioned name or submitted job is not evidence of a completed generation. Follow [references/production.md](references/production.md) for detailed prompting and retries.
4. Download to the requested drive, preserve raw sources, and record each completed post URL, source hash and clip duration using `scripts/produce.py ingest INPUT SCENE_ID FILE --job-url URL`. Downloads with repeated provider filenames must be retained under unique scene IDs before the next download.
5. Combine presenter with progressive whiteboard explanations, original diagrams, real datasets and genuine editor/terminal/application captures. Do not create a talking-head-only module. Technical writing must be authored or captured accurately; generative code/text is not execution evidence.
6. Review each segment for dialogue, voice identity, face, logo, lip sync and teaching accuracy. Record per-segment findings in the manifest. `accepted` requires actual relevant evidence, not a successful download. A repeated voice prompt is not a voice lock. Keep failed clips rejected and unchanged.
7. Assemble in explicit scene order with `scripts/produce.py render INPUT --draft` for diagnostic work or without `--draft` only after all required checks pass. The helper refuses missing/rejected scenes and duplicate content coverage. It preserves original sources and writes a separate master. An extension containing its base must represent combined coverage once, or use explicit nonoverlapping in/out ranges.
8. Review the complete rendered result with sound, checking every join, technical text, caption and exercise. Inspect sampled frames and media measurements as additional evidence, never as a substitute for audiovisual review. Repair actual defects, then record final review tied to the output hash.
9. Produce exact timeline-derived chapters, title, description, thumbnail/source assets, captions and upload metadata. Call `scripts/produce.py verify INPUT` to assess delivery readiness. No fabricated chapter times, unrecorded results or false completion claims. Upload only within the user's specific authorization and verified channel/visibility settings.
10. If the user pre-authorizes sequential module publishing, record that bounded authorization in the project and proceed after quality checks without asking again between modules. Verify the active account/channel, record each upload ID/master hash before continuing, and reconcile interrupted uploads in Studio to avoid duplicates. Use the product's same-thread recurring continuation mechanism when ongoing automated work is requested; retain real login, quota and review dependencies and stop after the authorized course is verified complete.

## Definition of done

A complete master exists at the requested output path; script/lesson coverage is intact; ordered sources and hashes are recorded; required code runs are verified; logo, identity, voice, lip sync, audio, captions and full playback have passed review; and the YouTube package is present. If any check is missing, label the exact limitation and the current artifact as draft. Do not call a comparison reel a module.

The tool is a reusable agent-operated workflow with local rendering helpers. Browser generation, provider quota and audiovisual review remain real dependencies. Do not describe it as an unattended provider API or guarantee voice cloning, monetization or exact generative typography.

## Before the first run

`assets/input.example.json` points at `references/presenter.png`, `studio.png` and `logo.png`. They are not shipped: add your own authorized portrait, set and logo there first (see `references/input-and-commands.md`).
