# Google Drive transport with Playwright

Resolve the Drive folder in this order: an explicit `drive_folder_url`, then a machine override at `<CODEX_HOME>/session-transfer/settings.json`, then `assets/defaults.json`. The bundled defaults ship empty: create a folder such as `Codex Session Backups` under My Drive, then save its URL and ID in the machine override. A ZIP carries the resolved locator in its manifest, so keep the folder private.

Use the existing signed-in Playwright browser and Drive tab. Do not open another browser, profile, or tab when one is already available. Do not list/read all Drive folders. Navigate the existing tab straight to the configured folder URL; inspect only that folder and the requested archive. If the caller is delegating browser work, keep all actions with the agent owning the working browser connection; another agent may receive a profile-in-use error.

Discover the current `mcp__playwright__*` tool schemas before using them. Take a screenshot and read the current page before using a fresh accessibility snapshot for controls. Never hard-code old element references. A profile-in-use error is not an invitation to kill the user's browser or start an isolated profile. Retry the existing owner/connection. If unavailable, keep staged files and report the connection blocker. If sign-in is shown, let the user sign in manually in that tab; never ask for credentials.

## Folder setup

Go directly to the saved URL. Do not create a new folder during import if the configured backup is unavailable. For a genuinely new export setup, create `Codex Session Backups` at My Drive root using `New > New folder`, then save its actual ID/URL in machine settings. Do not search through other folders. If creating gives a duplicate-name warning, inspect only the exact-name target or ask which backup folder to use. Never substitute another account's similarly named folder silently.

## Upload

Verify the local ZIP first. When a prior `<UUID>.zip` exists, retain it: create a timestamp-named version subfolder under the backup folder for the new archive unless the user explicitly requested replacement. Keep the filename `<UUID>.zip`. Record the version folder URL; future default imports prefer the newest verified version for that UUID, using only this backup folder's metadata.

With the destination visibly open, click `New > File upload`, then call `browser_file_upload` with the absolute ZIP path. That path must exist on the Playwright server's filesystem. Never assume a remote browser server shares the user's local disk. If it does not, use an available permitted file bridge or leave the local ZIP ready for manual upload.

Wait for Drive's completion status and verify exact filename and destination. For a full transport check, download that same file to a separate staging path and compare SHA-256 to the original. Report upload verified separately from checksum round-trip verified. Do not set public sharing or alter permissions.

## Download

In the configured backup folder, locate only `<UUID>.zip` and its explicitly recorded versions. If multiple candidates remain ambiguous, use the recorded latest version/checksum or ask rather than choosing silently. Right-click the observed file row, choose `Download`, and capture the actual completed download path.

When the available Playwright tool supports code and `Download`, register `page.waitForEvent('download')` before the observed click, then call `download.saveAs(localStagingPath)` and check `download.failure()`. Read the tool documentation first. Do not guess a downloads directory. A download on the browser server still needs to reach the destination machine where the importer runs.

Run `inspect`, verify manifest UUID and every checksum, and then preview import. Never execute anything from a downloaded session archive. A Drive error must not be reported as a successful transfer.
