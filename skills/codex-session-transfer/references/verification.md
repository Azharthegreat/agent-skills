# Session-only release verification

The current release supersedes the earlier workspace-inclusive archive scope.

41 tests passed on Windows with the installed Codex 0.153.1 native runtime fixture enabled. A new real export of a live task was validated: exactly 9 related rollout files and 3 session metadata files. It contains no project file payloads, CLAUDE.md, AGENTS.md, AGENT.md, SKILL.md, other skill directories or unowned shared memory.

The new ZIP was restored into a fresh isolated Codex home. Native list/read/history verified the root task with 5 turns and 391 items. The source task remains unchanged. This export has a capture cutoff; later messages are outside that backup.

Regression coverage verifies default session-only scope even when workspace instructions, project source, other skills and unowned memory exist. Explicit attachment inputs accept files only. Instruction payloads are rejected during archive import as well.

Historical message/tool-result text is preserved, including any old quotations of instructions. Those quotations are part of the conversation, not additional copied files. Scheduled tasks, goals and memory are included only when linked to the selected session scope.

Visual sidebar rendering, live schedule execution on another computer and arbitrary future runtime schemas are not certified by these tests.
