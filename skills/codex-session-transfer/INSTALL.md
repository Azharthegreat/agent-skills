# Install on another computer

Copy the `codex-session-transfer` folder from this repository so the destination contains `<CODEX_HOME>/skills/codex-session-transfer/SKILL.md`, or `~/.codex/skills/codex-session-transfer/SKILL.md` when CODEX_HOME is unset. Keep the entire skill directory, including scripts, references and assets. Resolve the current destination user's home; never reuse the source username. Reopen Codex if the skill is not listed.

Python 3.11 or newer is required. The helpers use the Python standard library. Default Google Drive transfer additionally needs a working Playwright connection (for example the Playwright MCP server) signed into the account that owns your backup folder; set that folder as described in `references/google-drive.md`. Reuse an already open browser/tab and inspect only that backup folder. Local-folder transfer requires no browser. Configure the same Drive folder on each machine.

Ask: `Use $codex-session-transfer to import session SESSION_ID into DESTINATION_PROJECT_PATH.` The skill obtains the selected archive, discovers the destination Codex home, validates compatible initialized schemas, maps paths and prepares an import preview. It reports unresolved schedule/identity/schema dependencies rather than silently dropping them. Resolve these before preparing the offline apply command.

Actual import into an existing Codex home requires closing Codex and its app servers, then running the prepared trusted helper. Reopen and verify the task, memory, goals, queued work and any schedule registration separately. A successful data import is not proof of runtime behavior. Read `references/restore.md` before using backups or recovering an interrupted import.

The skill ZIP installs the transfer tool. A `<SESSION_ID>.zip` archive contains a particular chat and its captured dependencies. Neither carries account credentials, browser sign-in or live running processes.
