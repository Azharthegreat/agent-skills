# Agent Skills

Skills I built and use every day with Claude Code, Codex and Cursor. Each one is a folder with a
`SKILL.md` that tells the agent when to use it and how, plus the references, scripts and templates
it needs. They come out of real work on Android apps and video production: promo videos from
emulator captures, course videos, YouTube publishing, ADB bridging and moving Codex sessions between
machines.

## The skills

| Skill | What it does |
| --- | --- |
| [adb-emulator-phone-bridge](skills/adb-emulator-phone-bridge) | Connects one or more USB phones to a desktop emulator's ADB endpoint through `adb reverse`, one tunnel per serial, with verification and recovery from flaky USB. |
| [app-promo-video-studio](skills/app-promo-video-studio) | Turns emulator captures into a vertical 1080x1920 app promo with motion graphics, English and Urdu neural voice-over, music and thumbnails, then publishes draft-first to YouTube, Facebook, Instagram and TikTok. |
| [create-mobile-app-marketing-video](skills/create-mobile-app-marketing-video) | Plans and produces app marketing videos from screenshots, recordings and store links: storyboard, phone mockups, voice-over, subtitles, sound and platform exports. |
| [course-video-producer](skills/course-video-producer) | Produces long-form course videos with Grok Imagine: consistent presenter, set and logo references, short directed clips assembled into modules, and a verified YouTube-ready package. |
| [youtube-video-seo-publisher](skills/youtube-video-seo-publisher) | Uploads and publishes YouTube videos through a dedicated Playwright profile, with search-focused titles and descriptions, app links, draft recovery and duplicate protection. |
| [codex-session-transfer](skills/codex-session-transfer) | Exports a Codex chat (history, memory, goals, schedules, attachments) to a portable ZIP and imports it on another machine with path mapping. |

## Install

Copy the skill folders you want into your agent's skills directory:

| Agent | Skills directory |
| --- | --- |
| Claude Code | `~/.claude/skills/` (or `.claude/skills/` inside a project) |
| Codex | `~/.codex/skills/` |
| Cursor | `.cursor/skills/` inside a project |

```bash
git clone https://github.com/Azharthegreat/agent-skills.git
cp -r agent-skills/skills/app-promo-video-studio ~/.claude/skills/
```

Some skills ship scripts. Their `SKILL.md` lists what each script needs: Python 3, Node.js with
Playwright, `ffmpeg`, or the Android SDK.

## More skills

My task orchestration, software estimation and Android launch skills are available on
[Agensi](https://www.agensi.io/creators/azharthegreat).

## A few ground rules every skill follows

- **Nothing irreversible without a yes.** Publishing, uploading, submitting and deleting all stop
  for explicit approval.
- **Evidence over claims.** A step counts as done only when the real artifact, page or store state
  confirms it.
- **No secrets in files.** Keys, tokens and passwords stay in the user's own secure storage and are
  never written into a skill, a log or a commit.

## License

MIT. See [LICENSE](LICENSE).

Built by [Muhammad Azhar](https://github.com/Azharthegreat) ·
[MetaCyberGuru](https://www.metacyberguru.com/) ·
[LinkedIn](https://www.linkedin.com/in/azharthegreat/) ·
ORCID [0009-0003-4054-6614](https://orcid.org/0009-0003-4054-6614)
