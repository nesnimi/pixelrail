# Acceptance on a second computer

No second physical machine has been tested by this preparation. Target **Arch
Linux, Hyprland 0.57.x Lua, Quickshell 0.3.2**; other distributions remain unverified.
Record versions, CPU/GPU, display/scale, battery names and missing devices. Do not
copy an owner's username, monitor name, GPU policy, theme cache or clipboard data.

- [ ] Verify source SHA256SUMS, MIT/third-party notices and no prebuilt native binary.
- [ ] Build with local matching Qt/private headers; `install.sh --check` passes.
- [ ] Missing optional backend/device is diagnosed; no fabricated working control.
- [ ] `install.sh --diff` leaves HOME unchanged; foreign Lua and `.conf` conflicts
  require `--accept-config-changes`; arbitrary dotfiles are backed up/preserved.
- [ ] Fresh install, existing config integration and repeated update use one qs.
  Startup/IPC failure preserves the old shell and allows rollback.
- [ ] Existing input layouts are unchanged. The new sample's us/ru + Alt+Shift
  works; Super-tap/95 binds, Chrome/Kitty commands are adjusted only by the owner.
- [ ] Sidebar workspaces/windows/last vector mark, primary/secondary monitor,
  hotplug, changed resolution and HiDPI; no assumption about eDP-1 or 1366×768.
- [ ] Desktop with no battery, laptop with one differently named battery, and
  weighted multiple batteries display correctly; missing EPP/NVIDIA is harmless.
- [ ] Launcher grid/list fallback, RU/EN, Tab/arrows/Enter/Escape/outside click,
  original/themed icons, frequency state and same-app command deduplication.
- [ ] Quick Settings/Notifications tabs, resize, Wi-Fi/Bluetooth, audio sink,
  volume/mute, brightness if present, Fn/XF86/OSD and MPRIS.
- [ ] One notification D-Bus owner, DND/history/actions/clear; switch back to SwayNC.
- [ ] Clipboard text/Unicode/PNG/JPEG/WebP restores original data/MIME; watcher dedup.
- [ ] Wallpaper list/cache/apply/cancel and Dark/Light/Auto/accent persist.
- [ ] Super+Shift+S with open panels: selector, cancel/repeat/reset; normal Escape
  and outside click return; no regression to slurp pipe stdin or brightnessctl -n.
- [ ] Battery/Performance changes graphics only; no driver/service/power tuning.
- [ ] Rollback, full uninstall, user-edit conflict and injected install failure;
  original files and user data survive. Foreign qs/Waybar/server are untouched.
- [ ] GoogleDot is optional: backup current cursor, manual Black/White test in
  Qt/GTK/XWayland, restore; never necessary for shell startup.
- [ ] Measure idle RSS/interval CPU with the existing Power Audit/benchmark under
  comparable conditions. Do not infer laptop watts from an unmapped test.

Record PASS/FAIL/NOT AVAILABLE per item and attach redacted logs before declaring
v3.1.0 stable or expanding the compatibility statement.
