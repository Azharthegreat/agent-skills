---
name: codex-session-transfer
description: Export or import a Codex chat by session ID as a portable ZIP with persisted history, memory, goals, queued work, related schedules, and session attachments. Use for backups or transfers between computers through Google Drive by default or a local folder, with destination path mapping and explicit completeness checks.
---

# Codex Session Transfer

For an explicitly requested active-task backup, add `--live-snapshot` to export. This freezes persisted rollout prefixes and database snapshots during capture. Later messages are outside that backup, and the stores are not one atomic application transaction. Normal export instead rejects source changes. Session ZIPs contain persisted task records and directly linked attachments only. Never copy CLAUDE.md, AGENTS.md, AGENT.md, SKILL.md, workspace trees, other skills/plugins or unowned shared memory. Historical messages/tool results remain intact even if they quote those files; do not rewrite chat history to remove old discussion.

For "import as a new task", first run `python scripts/session_clone.py prepare --zip SOURCE.zip --folder CLONE_FOLDER`. Use the returned new UUID and ZIP with the normal importer. This translates the selected session graph and supported relational identities, and preserves the original archive. The helper rejects unsupported identity formats or incomplete inherited history.

For real isolated verification, run `python scripts/verify_roundtrip.py --zip ZIP --folder VERIFICATION_FOLDER --schema-home LOCAL_CODEX_HOME --codex-binary TRUSTED_INSTALLED_CODEX_BINARY`. It allocates a fresh home, initializes schema from the trusted local installation, restores the full archive, checks rows/assets, and reads native paginated history. It retains the verification folders. This does not replace an import into the user's normal home or prove visual sidebar rendering.

Use `scripts/session_transfer.py` with Python 3.11 or newer. Read [references/storage.md](references/storage.md) for supported state and [references/restore.md](references/restore.md) before import. This helper reconstructs supported persisted local data using inspected storage schemas. It cannot promise every future Codex version or recreate live processes and remote account state.

See [references/verification.md](references/verification.md) for the tested runtime, real task restore evidence and unverified boundaries.

## Parameters

| Parameter | Default / meaning |
| --- | --- |
| `action` | Required: `export` or `import` |
| `session_id` | Required chat UUID; ordinary import preserves it |
| `storage` | `google-drive`; use `local` when a local folder is supplied |
| `folder` | Local export destination or import directory containing `<session_id>.zip` |
| `drive_folder_url` | Your Drive folder URL: passed explicitly, or saved in `<CODEX_HOME>/session-transfer/settings.json` or [assets/defaults.json](assets/defaults.json). Ask once if none is set |
| `project_root` | Export: stored cwd. Import: verified destination checkout; ask only if unresolved |
| `codex_home` | `$CODEX_HOME` if set, otherwise current user's `~/.codex` |
| `project_mode` | `none` only; cwd is mapping metadata, never a request to copy the project |
| `include` | Only a specific user-selected session attachment file; no directories or instruction files |
| `path_map` | Additional `OLD=NEW` path mapping, passed as `--map` |
| `identity_map` | Verified source-to-destination identity binding, passed as `--identity-map OLD=NEW` |
| `conflict` | `abort`; use `replace` only for authorized differing destination data |

Resolve `SCRIPT` to this installed skill's actual `scripts/session_transfer.py`. Never hard-code source usernames, drive letters, workspace roots or the installed skill path on a different computer. Destination identities require evidence from that destination, not guessed replacements.

## Export

1. Find the supplied UUID in the active home's state database and inspect its actual cwd and dependencies. Default graph selection includes descendants discovered from database edges and rollout metadata, then required ancestors; it does not expand those ancestors into unrelated siblings. `--single` deliberately excludes that closure and must be reported as restricted scope.
2. Resolve the stored cwd only for destination path mapping. Do not scan or copy its contents. Do not treat a path mentioned in a prompt/tool output as permission to bundle a repository, rules or skill directory. Use `--include FILE` only for a specific attachment the user identifies as belonging to this task.
3. Prefer an idle source. The helper captures database records, full persisted rollout messages/tools/compaction, memory, goals/queues, selected automation definitions/history, recognized desktop state and directly linked assets. It records source changes, exclusions and blockers. See the storage reference for snapshot limits.

```text
python SCRIPT export --session-id UUID --project-root SOURCE_PROJECT --folder LOCAL_STAGING
python SCRIPT inspect --zip LOCAL_STAGING/UUID.zip
```

4. Inspect `supplemental`, `completeness`, exclusions and unresolved references. Resolve missing related dependencies, source schedule disagreements and unsupported stores before describing a full transfer. Re-export to a new staging/version directory after corrections. Default size limit is 2 GiB including archive metadata. Raise `--max-bytes` deliberately if needed. The ZIP is neither encrypted nor redacted; transcript text and session memory may contain sensitive information.
5. Local storage: deliver ZIP/checksum and remaining limits. Default Drive storage: follow [references/google-drive.md](references/google-drive.md), reuse the existing signed-in Playwright browser/tab, navigate directly to the saved backup folder, and inspect only that folder. Never list all Drive folders or create another browser when the existing connection is available. A staged ZIP is not a completed upload. Verify the upload and preferably download/checksum round-trip. Release the browser connection when finished, without closing the user's browser.

## Import

1. Resolve exactly `folder/UUID.zip` for local input or the requested UUID/version in the saved Drive folder. An explicit ZIP path is accepted. Inspect the ZIP before extraction; never execute code from a session archive.
2. Discover the destination's actual Codex home and project checkout. Confirm repository identity when matching a checkout. An old path such as `C:/old-checkout` does not establish the new project location. Inspect compatible initialized destination schemas and any required account/host bindings.
3. Preview while Codex is open:

```text
python SCRIPT import --zip ZIP --session-id UUID --project-root DESTINATION_PROJECT
```

Preview validates archives and schemas, maps paths and history offsets, prepares selective row/global-state merges, and reports conflicts. Explicit path mappings take precedence over automatic mappings for the same source root; more-specific roots take precedence. Exact relocated attachment mappings retain their physical destination. Identity mappings are separate from filesystem mappings.

4. Resolve completeness blockers. Examples include conflicting schedule representations, missing schedule target sessions, unmapped account/host/principal bindings, timezone differences and unsupported session-linked desktop state. Do not silently remove schedules, pause ACTIVE schedules, discard goals/queues or select one conflicting source representation. Permission/capability setup is separately reported as destination setup; importing a chat does not grant access or reproduce credentials. `--allow-incomplete` is diagnostic only, requires an explicitly requested partial restore, and must be reported as incomplete.
5. Prepare the exact offline command/runner and preserve the verified ZIP, paths, preview and conflicts before the user closes Codex. The trusted installed helper performs the final apply:

```text
python SCRIPT import --zip ZIP --session-id UUID --project-root DESTINATION_PROJECT --apply --offline-confirmed
```

Use destination Python and proper shell quoting. Include all verified `--map`, `--identity-map`, `--codex-home` and authorized conflict flags. Real-home apply requires Codex desktop, CLI, IDE app servers and other writers to be closed. Do not kill the current app or claim a prepared command is an applied import. An explicit import request already authorizes a nonconflicting import; request a choice only for an unresolved conflict or required missing information.

6. Inspect the apply result/journal, reopen Codex and verify the exact UUID, project/section placement, title, earliest/latest turns, tool results, assets and memory. Goals and queued work are restored as persisted records; verify their destination behavior and ordering. Selected schedules retain their stored status, recurrence and history; verify scheduler registration, target, timezone, next run and duplicate/overdue execution behavior before claiming source-equivalent scheduling. An `imported` result establishes successful local persistence only, not app visibility or scheduler execution.

## Requests and reporting

```text
Use $codex-session-transfer to export session SESSION_ID.
Use $codex-session-transfer to import session SESSION_ID into D:\projects\my-app.
Use $codex-session-transfer to export session SESSION_ID to local folder D:\Backups\Codex.
Use $codex-session-transfer to import session SESSION_ID from D:\Backups\Codex into D:\projects\my-app.
```

Report action, UUID, archive/checksum or verified Drive link, destination mappings, included counts, blockers/required setup and omissions. Distinguish archive validation, import apply, app visibility and scheduler verification as separate PASS or Not verified outcomes. Do not say all scenarios are perfect. If asked to transfer the skill itself, package the entire trusted skill directory including helpers/references/defaults, verify it, and upload to the same saved backup folder; that ZIP is separate from a chat backup.
