# Inputs, commands and state

## Invocation from any tool-enabled LLM

```text
Read course-video-producer/SKILL.md and its routed references. Produce the video
specified by project/input.json using my authorized Grok browser subscription.
Use the supplied script, Character, Location, Logo and approved voice sample.
Keep the original assets, preserve the exact teaching sequence, generate only
missing approved scenes, assemble selected clips and verify the final package.
Do not call it production-ready without full audiovisual review.
Output only to the directory in the brief. Do not upload unless this brief and
my latest instruction explicitly authorize that destination and visibility.
```

Codex can invoke `$course-video-producer`. Another LLM can read this same folder; it must map browser actions to its actual available tools, not invent MCP names or shell access. A skill file alone does not grant an LLM those capabilities.

## Brief structure

Copy `assets/input.example.json` into the project's own work folder as `input.json`, with `assets/script.example.txt` as `script.txt`. Supply the three referenced images at the declared paths or change the paths to real approved assets. The example is a template, not a ready asset pack: no portrait, voice sample or brand rights are bundled.

| Parameter | Meaning and handling |
|---|---|
| `topic` | Course/module or standalone topic, audience, objectives, full/partial scope |
| `reference_material` | Actual local files with roles, saved browser aliases, rights notes; add approved voice sample when available |
| `final_script` | Exact narration file. Scene dialogue must cover it once in order |
| `code_demo_assets` | Dataset, runnable code, real capture files and test evidence. Empty only when the declared scope includes no code |
| `visual_style` | Presenter identity/clothing, location, logo appearance/placement, voice target, teaching media and camera direction |
| `output` | Dedicated output folder, unused MP4 name, width/height/fps, discovered FFmpeg/FFprobe paths and justified duration |
| `generation` | Provider, browser subscription mode, actual selected clip duration; retry/batch limits are agent-enforced policies |
| `scenes` | Ordered safe unique IDs, unique nonempty coverage IDs, medium, objective, visual direction, exact dialogue and timed beats |
| `publication` | Agent-enforced authority record: upload authorized or not, channel, visibility and stop boundary. Not an automatic upload command |

`presenter_description`, `clothing`, `logo_description` and `audio_direction` make prompts project-specific. `presenter_reference: "none"` explicitly selects narration/visual-only mode. Preserve an approved voice target when changing visual mode. The bundled prompt generator creates source-shot instructions for later authored teaching overlays, not fake technical graphics or recordings.

## Local commands

Discover Python 3.10+ and FFmpeg/FFprobe first. Run from the skill folder; quote paths with spaces. On Windows use the actual Python executable or `python`; on another host substitute its verified command. These commands do not call the provider or spend credits.

```powershell
python scripts/produce.py plan "D:/VideoProject/input.json"
python scripts/produce.py ingest "D:/VideoProject/input.json" S001 "D:/VideoProject/downloads/S001.mp4" --job-url "https://grok.com/imagine/post/ACTUAL_COMPLETED_POST"
python scripts/produce.py ingest "D:/VideoProject/input.json" S002 "D:/VideoProject/downloads/S002.mp4" --job-url "https://grok.com/imagine/post/ACTUAL_COMPLETED_POST"
python scripts/produce.py render "D:/VideoProject/input.json" --draft
python scripts/produce.py verify "D:/VideoProject/input.json"
```

The URLs above must be replaced with observed job URLs. Ingest requires completed audio+video files and copies them to the output's immutable attempt paths. For corrective editing, ingest selected corrected media into a new assembly version and retain the raw lineage sidecar. `--replace-pending` is only for an unaccepted attempt and preserves its previous record/file; it is not a way to overwrite accepted work.

`plan` creates `out/prompts/` and `out/manifest.json`; manually inspect/refine prompts before submitting. Re-running unchanged inputs is idempotent. Changing script, order or input options requires a NEW dedicated output version. Do not re-plan old work to change its facts.

`render --draft` requires every declared scene to exist; it does not silently omit missing scenes. For owner-approved Part 1, create a separate truthful partial script/input containing exactly that coverage and no promise of a finished full module. Each draft gets a unique filename. Raw clips remain untouched.

## Recording real scene reviews

The agent updates only mutable production fields in `out/manifest.json`; canonical dialogue, coverage, order and input hashes remain frozen. After actually viewing/listening to a selected clip, record its `review` values for `dialogue`, `voice`, `identity`, `lip_sync`, `logo`, `visuals`, `review_evidence` (relative file path) and `status`. Never set pass from prompt text or an ASR score alone.

The JSON evidence file must identify `sha256` (the selected file), `in`, `out`, `reviewer`, `method`, `observations` and per-check results. Use the actual trim boundaries. `status: accepted` requires each applicable check to pass; for presenter-free scenes record why identity/lip-sync checks pass as explicitly not applicable to the approved medium, rather than pretending a face was reviewed.

For a final render, only after scene approval:

```powershell
python scripts/produce.py render "D:/VideoProject/input.json"
```

The final filename must be unused. This writes a master but leaves `upload_ready` false and `full_playback` not verified. It is not a production-ready certification.

## Final package and release checks

Follow `editing-and-release.md`. Create the actual thumbnail, chapters, captions, metadata and review report. Update `delivery.review`, `review_evidence`, `reviewed_sha256` and `full_playback` only after the final media has actually passed those checks. The final review evidence path points to a real reviewer report; hash-bind it to the current master.

```powershell
python scripts/produce.py verify "D:/VideoProject/input.json"
```

Read the returned `upload_ready` and `problems`; a successful command invocation alone is not approval. The helper returns exit status 2 when readiness fails. It does not generate captions/metadata, apply loudness mastering, compare actual voices, control Grok or upload to YouTube. Those are agent-operated stages explicitly documented in this skill.

After any final processing outside this renderer, reconcile the delivered filename, hash, measured duration, timeline and assembly provenance before new review. Do not preserve a stale pass for a changed master.

## Recovery checkpoint

Keep `jobs.json` separately from the renderer manifest, with scene/attempt, submitted prompt hash, actual chips/settings, post/conversation URL, source hash, status, failure reason and next action. It is agent-maintained, not a built-in scheduler. Never store tokens/cookies. On resume read the brief, manifest, jobs and upload-attempt record first; verify hashes and reconcile unknown external states. Do not generate completed scenes again, upload a known ID twice or resume a paused batch without authority.
