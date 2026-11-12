# Storage contract and limits

Archive format 2 uses `manifest.json`, selected `records.json`, selected `indices.json` and explicitly listed file payloads. Format 1 archives are readable for compatibility but do not gain memory/schedule dependencies that were never captured. Storage schemas are Codex implementation details. The original inspection used Windows desktop runtime 0.153.1 on 2026-09-09; compatibility must be checked against the actual source and destination.

| Persisted data | Export and import treatment |
| --- | --- |
| Root `state_*.sqlite` | Selected threads, dynamic tools, artifacts, spawn edges and project/section records; import uses primary-key upserts and destination project/section matching |
| `sessions` / `archived_sessions` JSONL | Full persisted record stream including compaction, messages, tools and opaque encrypted fields; paths and history offsets remapped |
| `thread_history_*.sqlite` | Selected turns, items, realtime items and projection state; required paginated history and UTF-8 line-boundary offsets validated |
| `memories_*.sqlite` | Selected `stage1_outputs`; worker jobs/leases are not restored as running processes |
| `memories/` files | Only files whose path identifies a selected session; unowned shared memory is excluded |
| `goals_*.sqlite` | Selected goals and continuation deferrals are restored, including persisted status, budgets and usage |
| `queue_*.sqlite` | Selected queued items and revisions are restored; revision values adapt to the destination database |
| `automations/<id>/` | Selected definition directory including `automation.toml` and memory/assets, excluding instruction files; UTF-8 text/TOML paths and explicit identity fields remapped |
| `sqlite/codex-dev.db` | Selected automations, session-linked automation runs/inbox rows and timeline ledger records; identity bindings require verified mappings |
| `sqlite/codex-thread-summaries-dev.db` | Selected turn summaries; principal/host bindings require verified destination mappings |
| `.codex-global-state.json` | Recognized selected project assignments/entities/order, drafts/client bindings, descriptions, routes, workspace and pinned/unread state are merged; unrelated destination entries retained |
| `session_index.jsonl`, `history.jsonl` | Selected UUID records merged while preserving unrelated entries |
| Images, visualizations, attachments | Session directories plus detected referenced local files; explicit external dependencies can be added with `--include` |
| Project | No project tree is copied. Only cwd/root metadata is retained for mapping |

Default graph discovery combines database spawn edges with rollout `parent_thread_id`, `forked_from_id` and subagent spawn metadata. It includes descendants of the selected task and required ancestors without expanding those ancestors into unrelated siblings. `--single` deliberately restricts this scope. Other cwd roots and external references require inspection and explicit capture/mapping.

Schedule membership is the union of TOML target IDs, database target IDs and selected automation-run ownership. The helper preserves both definition representations. Disagreement, a missing representation or a required target outside the captured closure is a blocker. It does not guess which representation controls the running scheduler. Only runs/inbox/timeline/summary rows belonging to captured session IDs are included. ACTIVE schedule status and stored next-run values remain active/preserved; actual destination scheduler registration and timezone/overdue/duplicate-run behavior need separate verification.

Account, user, installation, environment, host and principal values are binding metadata, not portable credentials. Use explicit verified destination identity mappings. Unsupported session-linked desktop state blocks full reconstruction. Capability/permission entries become required destination setup notes and are not imported as grants. Browser cookies, `auth.json`, secret stores, global configuration, remote enrollment and live process/lock state must not be copied into an archive to force access.

The exporter takes temporary SQLite snapshots of supported root stores, selects rows, checks selected source state for changes, and compares supplemental dependency collection at export completion. Files are checked for size/mtime changes. These checks detect supported changes but are not a cross-process freeze or a guarantee of one atomic snapshot across every storage backend. Export idle sessions and inspect all reported limits. Unsupported/new stores, opaque remote state and references in unusual formats need additional inspection.

Primary-key upserts preserve destination-only columns and do not delete absent session metadata through a parent-row replacement. Existing projects are matched by mapped roots; sections are matched by name. Colliding foreign IDs can be translated. Selected desktop project references are reconciled with the resolved destination mapping. Existing destination project metadata is retained when reused. Review ambiguous matches rather than guessing.

Path mapping supports source aliases, embedded JSON and Windows/POSIX separators. Explicit `--map` wins over an automatic mapping of the same root, and longer roots match first. Additional external dependencies are stored beneath `attachments/session-transfer/<session-id>/...` with exact file mappings. Binary files, including ordinary project source/config files, are copied byte-for-byte. Only designated rollout/text/TOML payloads are rewritten; inspect project runtime configuration before claiming cross-platform executability.

The manifest records selected IDs, roots/aliases, file hashes/sizes, extra paths, supplemental records/files, binding metadata, source timezone, exclusions and unresolved references. Validation rejects unsafe ZIP paths, duplicates, unsupported routes/tables, unrelated selected records, checksum mismatches and size-limit violations. SHA-256 verifies integrity, not provenance or encryption. Never execute archive-supplied SQL, scripts or installers.

Complete persisted reconstruction cannot include unavailable files, unsaved process state, pending tool execution, hidden server state, inaccessible remote blobs, lost encryption keys or external service authorization. A zero-blocker archive still needs review of exclusions/references and actual app/scheduler verification before a source-equivalent claim.

Session-only scope supersedes earlier workspace-inclusive backups. CLAUDE.md, AGENTS.md, AGENT.md and SKILL.md are never additional file payloads. Other skills/plugins and project directories are not automatically captured. Explicit attachment inputs must be files, not directories.
