# Installation — PixelRail v3.1.0 preparation

[Русское введение](../README.ru.md) · [English overview](../README.md).
Validated target: Arch Linux, Hyprland 0.57.x Lua, Quickshell 0.3.2. Other distros
and a second physical computer have not been certified. No installer command
runs a package manager, sudo, service management, GPU/CPU tuning or a reboot.

## Dependencies and build

Core: Python >=3.10, Bash, user D-Bus/busctl, Hyprland 0.57.x Lua and Quickshell
0.3.2. Build with g++, pkg-config, Qt6 Core/Gui/Qml/DBus, moc and Qt private headers
matching the installed Qt. Review distro package names/versions yourself; install
missing dependencies through your own package-management procedure.

Feature backends: PipeWire/WirePlumber and pw-dump, NetworkManager, BlueZ, UPower,
brightnessctl, matugen, swaybg, cliphist/wl-clipboard, grim/slurp, playerctl.
Waybar/SwayNC are optional recovery fallbacks; their initial modes are the defaults.
The legacy Waybar sample uses Nerd Font glyphs; native PixelRail uses bundled
Rounded SVGs/Roboto. GoogleDot is optional, not a startup requirement.

```bash
./scripts/build-native.sh
./scripts/install.sh --check
./scripts/install.sh --check --json
```

The build writes only repository native/cache files. It records the native hash
and local Qt version in ignored build-info.json. A stale/missing stamp blocks live
activation until rebuilt. Releases carry no precompiled plugin; do not reuse a
binary from another machine or Qt version. After a Qt update, rebuild locally.

Checks distinguish required errors from unavailable optional commands. They do
not prove that a service is running, an audio sink exists, or a laptop supports
backlight adjustment. Do not start/reinstall PipeWire or BlueZ from autostart just
because a device is temporarily unavailable.

## Plan and approve integration

```bash
./scripts/install.sh --diff
./scripts/install.sh --apply
```

Dry-run is default and does not create release/backup directories or start processes.
Install is per-user, never root. Existing dotfiles, locally modified managed targets
and legacy links without verifiable fingerprints are conflicts. Review the exact
paths/diff before using the separate explicit confirmation:

```bash
./scripts/install.sh --apply --accept-config-changes
```

This approval is not implied by --apply. Existing Hyprland Lua is preserved apart
from the reviewed keybind/autostart additions; input layouts, monitors and app
rules are not replaced. A fresh sample defaults to us/ru + Alt+Shift and generic
monitor settings. If only a foreign hyprland.conf exists, creating hyprland.lua
would shadow it: that requires explicit approval and manual Lua migration review.
Never enable both independent autostarts. The installer does not reload Hyprland.

Existing pre-publication installations need one rebuild/review if their native
stamp or target fingerprints are absent; their settings/history are preserved.

## Install layout and transactions

- Links: HOME/.local/bin/pixelrail-* and reviewed HOME/.config/hypr entrypoints.
- Immutable payload: HOME/.local/share/pixelrail/releases/ID.
- Backups/manifests: HOME/.local/state/pixelrail/deployments/ID.
- Preferences: HOME/.config/pixelrail, runtime caches/state outside releases.

The current installer supports these standard per-user persistent roots. It
refuses nonstandard XDG_CONFIG_HOME/DATA_HOME/STATE_HOME for live apply rather than
silently writing the wrong locations. Runtime components honor their documented
XDG settings; a full alternative install layout has not been validated.

Apply checks required dependencies, snapshots originals, prepares the new shell
and verifies IPC before retiring only the old owned release. Failure preserves
backups and the old shell. Foreign Quickshell instances are not killed. Symlink
parents escaping the target HOME are refused. A saved panel/notification choice
is not changed by deploy. First install leaves Waybar/SwayNC modes selected.

## Offline / isolated staging

```bash
mkdir -p "$PWD/.cache/staging-home"
./scripts/install.sh --target-home "$PWD/.cache/staging-home" --no-start --diff
./scripts/install.sh --target-home "$PWD/.cache/staging-home" --no-start --apply
./scripts/rollback.sh --target-home "$PWD/.cache/staging-home" --no-start
```

--no-start skips all process changes and activation readiness checks; it is not a
claim that staged QML works on real devices. File-only staging still requires a
locally built plugin for deployment. Tests may use explicit foreign-file approval
only inside their fixture HOME.

## Start native modes after review

```bash
pixelrail-panel mode sidebar
pixelrail-notifications mode pixelrail
pixelrail-panel status
pixelrail-notifications status
```

These are manual session actions, not automatic installation steps. A foreign
Waybar/notification server is preserved; resolve ownership through its own setup.
Fallback: pixelrail-panel mode waybar; pixelrail-notifications mode swaync.
Existing Chrome/Kitty shortcut commands remain; customize absent apps explicitly.

## Update, rollback, uninstall

Existing deploy.sh remains the same engine and accepts the new safety flags.
For one update: ./scripts/rollback.sh, then --apply after reviewing its plan.
For full integration removal: ./scripts/uninstall.sh, then --apply. Both preserve
user settings/data and all recovery material. Later user edits block restoration
rather than being overwritten. See [uninstall](uninstall.md), [recovery](recovery.md)
and the [second-machine checklist](second-computer-checklist.md).
