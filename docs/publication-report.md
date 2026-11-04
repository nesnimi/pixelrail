# PixelRail v3.1 — public packaging report

Prepared in the repository/private fixtures only. No live install, service or
driver change, commit, tag, push, GitHub repository or public release was made.

## Publication and licensing

- Owner chose **MIT**, copyright **2026 nesnimi**; LICENSE and separate third-party
  notices are included. Roboto/OFL and Rounded Symbols/Apache-2.0 keep their terms.
  GoogleDot/GPL-3.0 remains an optional download, not a bundled binary/theme requirement.
- Pattern audit of the worktree and all reachable blobs/messages in **10 commits**
  found no credential/private-key patterns or owner absolute home paths. Binary
  artwork and identities require human review; a scanner is not a proof of absence.
- One historical author/committer email is not a GitHub noreply address. It was
  not printed in public files and history was not rewritten. The recommended
  clean-export publication procedure keeps the original local repository intact.
- Raw reference images, historical local captures, caches, build stamps and native
  binaries are excluded. Public screenshots are reviewed QML fixture captures;
  text/EXIF metadata is checked. Original files were not deleted locally.

## Installer and portability

- install.sh/uninstall.sh use existing deployment.py, deploy.sh, rollback.sh and
  lifecycle ownership checks. Dry-run is default; --apply does not approve foreign
  files. --diff + explicit --accept-config-changes are required for that list.
- Exact manifest/target fingerprints distinguish managed files from user edits.
  File permissions, original layouts and backed-up files/symlinks are preserved.
  Parent-symlink escapes and root install are refused. Temporary restore copies
  are private before contents are written; replacements are atomic.
- Dependency checks never install packages/start services. Native build stamps
  compare library hash, source, Qt version and architecture. Build on each machine.
- Full uninstall preflights the chain, restores originals through rollback, keeps
  recovery snapshots/data and avoids foreign qs/Waybar/notification processes.
  Only recorded, identity-checked clipboard workers are stopped; adopted workers
  and the standalone wallpaper remain. Native notification fallback is explicit.
- No runtime dependency on the original username/T480/GPU/battery name/resolution.
  Battery audit supports arbitrary names and weighted energy; old BAT1 JSON keys
  remain for compatibility. Only path quoting changed in Lua commands; the 95
  shortcuts/actions and Super-tap remain, including screenshot/XF86 routes.
- Current live installer supports standard persistent HOME/XDG roots; custom
  roots are refused with an explanation. Other distributions are not certified.
  UI labels remain primarily Russian; full internationalization was not added.

## Validation

23 selected regression commands passed, including a corrected/retried Power Audit
test assertion. Final targeted tests cover fresh install/update/rollback/uninstall,
foreign-file refusal/approval, edited targets, failure recovery, file modes,
Unicode/spaces, process ownership and source archive reproducibility/redaction.
Portable bind argv are tested with spaces, Unicode, apostrophes, dollar/backtick.
QML lint and QtTest, existing UI/IPC, notification, clipboard, wallpaper, system,
material resources, lifecycle and screenshot tests pass. No performance/energy
improvement is claimed; no long benchmark or soak was run.

Source-archive build/install validation and final counts are recorded in
`.cache/publication-results/`. The archive includes RELEASE.json and SHA256SUMS,
without Git history or prebuilt native libraries. Second physical machine testing
is **pending**, using [the checklist](second-computer-checklist.md).

Final counts: portable install 7, publication/redaction/reproducibility/PNG checks 3,
release reliability 3, read-only power fixtures 22, QtTest 14; QML lint exit 0 with
known dynamic-type metadata warnings. A clean extracted source archive was built
with local Qt, dependency-checked and staged in a separate HOME with spaces:
dry-run → fresh install → update → rollback → whole-chain uninstall all passed.
The tested runtime source/asset digest is retained in archive-install.json; final
archive checksums may change when this report is added, not its tested payload.

## Files and next steps

Main additions: MIT/third-party notices, bilingual README, SECURITY/CONTRIBUTING,
public screenshots, preflight/audit/package tools, install/uninstall wrappers,
portable tests, installation/uninstall/publication guides and release draft.
Deployment/lifecycle integration was extended; UI architecture/design was not changed.
All earlier uncommitted v3.1 sources remain. Include reviewed new source files,
not just the previously tracked diff, when preparing a public commit.

Owner commands: [install/recovery](installation.md), [clean GitHub publication and
draft v3.1.0 release](publication.md), [GoogleDot opt-in/backup](design/cursor.md).
Do not label the build stable or broaden compatibility until hardware acceptance.
