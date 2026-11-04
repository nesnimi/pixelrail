# Uninstall and restore

Use the same checkout that provides `install.sh`, or the retained release's
`scripts/uninstall.sh`. It delegates to `deployment.py`, not a second installer.

```bash
./scripts/uninstall.sh
./scripts/uninstall.sh --apply
```

The preview validates the whole active deployment chain, including backup hashes,
before changes. Apply restores original files newest-to-oldest through the existing
rollback function. A recovery snapshot protects the installed state if file
restoration fails. Later user edits are a conflict, never silently overwritten.
Backups, immutable releases, preferences, wallpaper choice and clipboard history
are retained. There is intentionally no automatic data purge or backup deletion.

Without a Wayland session, explicitly use `--no-start`: it restores files only,
without inspecting, starting or stopping processes. It does not make an already
running old shell disappear. Nonstandard target HOME tests also require this flag.

Normal live uninstall switches an owned native notification server to SwayNC before
retiring only registered PixelRail Quickshell instances. If native notifications
are active but SwayNC is missing, it refuses process teardown until a notification
fallback is available (or the owner explicitly chooses offline handling).
Foreign notification servers and unregistered Waybar/Quickshell processes remain
untouched. An owned Waybar is stopped; a restored original Waybar configuration can
be started without taking over a foreign instance.

Only a clipboard watcher explicitly spawned and recorded by PixelRail is stopped,
with UID/session/PID-start/argv revalidation. Adopted/legacy unrecorded watchers are
preserved. The current standalone swaybg wallpaper is retained to avoid blanking
the desktop; it does not run PixelRail code. No process-name `pkill` is used.

For **one update** instead of full uninstall:

```bash
./scripts/rollback.sh
./scripts/rollback.sh --apply
```

If a foreign/main config already contained manual PixelRail hooks before its first
recorded deployment, restoration faithfully restores that original file. Review
those pre-existing hooks yourself; uninstall does not guess which original lines
were yours. Keep releases/backups until recovery is verified.

If process cleanup reports an error after files were restored, do not delete the
backup or kill all qs processes. Inspect `qs list --all --json`; the retained release
scripts and manifests identify the exact PixelRail config/ID for manual recovery.
See [recovery](recovery.md) and [installation](installation.md).
