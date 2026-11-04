.pragma library

function clamp(value) { return Math.max(0, Math.min(100, value)); }
function battery(devices, display) {
    const present = devices.filter(device => device.isPresent && device.isLaptopBattery);
    let percent = null;
    if (present.length && present.every(d => d.energyCapacity > 0 && Number.isFinite(d.energy) && d.energy >= 0)) {
        percent = clamp(100 * present.reduce((sum, d) => sum + d.energy, 0)
                        / present.reduce((sum, d) => sum + d.energyCapacity, 0));
    } else if (display && display.isPresent && Number.isFinite(display.percentage) && display.percentage >= 0 && display.percentage <= 1) {
        percent = clamp(display.percentage * 100); // Quickshell normalizes UPower Percentage to 0..1.
    } else if (present.length === 1 && Number.isFinite(present[0].percentage) && present[0].percentage >= 0 && present[0].percentage <= 1) {
        percent = clamp(present[0].percentage * 100);
    }
    return {percent: percent, devices: present};
}
function application(toplevel, entries) {
    const data = toplevel.lastIpcObject || {};
    const key = String(data.class || data.initialClass || (toplevel.wayland ? toplevel.wayland.appId : "") || "");
    const normalized = key.toLowerCase().replace(/\.desktop$/, "");
    const entry = entries.find(app => [app.id, app.startupClass].some(value =>
        value && String(value).toLowerCase().replace(/\.desktop$/, "") === normalized));
    return {key: key, entry: entry || null};
}
function windows(values, appId, workspace) {
    return values.filter(window => {
        if (!workspace || !window.workspace || window.workspace.id !== workspace.id) return false;
        const data = window.lastIpcObject || {};
        const key = String(data.class || data.initialClass || (window.wayland ? window.wayland.appId : "") || "").toLowerCase();
        return !(key && ["quickshell", "org.quickshell", String(appId || "").toLowerCase()].includes(key)) && !key.startsWith("org.quickshell.");
    });
}
function svg(kind, color) {
    const paths = {
        home: '<path d="M6 18V6h7a4 4 0 0 1 0 8H6m0-4h7"/>',
        battery: '<rect x="4" y="7" width="15" height="10" rx="3"/><path d="M21 10v4M7 10v4m4-4v4m4-4v4"/>',
        wifi: '<path d="M3 8a15 15 0 0 1 18 0M6 12a10 10 0 0 1 12 0m-9 4a5 5 0 0 1 6 0"/><circle cx="12" cy="20" r=".7"/>',
        wired: '<rect x="6" y="3" width="12" height="11" rx="2"/><path d="M9 7v3m3-3v3m3-3v3m-3 4v6m-7 0h14"/>',
        offline: '<path d="m4 4 16 16M3 8a15 15 0 0 1 18 0M6 12a10 10 0 0 1 3-2m6 1 3 1m-9 4a5 5 0 0 1 6 0"/>',
        volume: '<path d="M4 9h4l5-5v16l-5-5H4Zm12-1a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/>',
        muted: '<path d="M4 9h4l5-5v16l-5-5H4Zm13 0 5 6m0-6-5 6"/>',
        bell: '<path d="M5 17h14l-2-3V9a5 5 0 0 0-10 0v5Zm5 3h4M12 2v2"/>',
        power: '<path d="M12 2v9m-5-6a8 8 0 1 0 10 0"/>',
        leaf: '<path d="M5 18C1 7 10 3 21 3c0 12-4 17-12 15m-5 3L16 9"/>',
        app: '<rect x="4" y="4" width="16" height="16" rx="4"/><path d="M4 9h16m-11 0v11"/>'
    };
    return 'data:image/svg+xml;utf8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="' + color + '" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + (paths[kind] || paths.app) + '</svg>');
}

function targetScreen(screens, name, primary) {
    return screens.find(screen => screen.name === name)
        || screens.find(screen => primary && screen.name === primary.name) || screens[0] || null;
}

function workspaces(values, active) {
    const ids = [1, 2, 3, 4, 5];
    if (active && !ids.includes(active.id)) ids.push(active.id);
    return ids.map(id => {
        const live = values.find(workspace => workspace.id === id);
        return {id: id, name: live ? live.name : String(id), active: !!active && active.id === id,
            occupied: !!live && live.toplevels.values.length > 0, urgent: !!live && live.urgent};
    });
}
function luaString(value) {
    return '"' + String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"')
        .replace(/\n/g, "\\n").replace(/\r/g, "\\r") + '"';
}
function workspaceSelector(workspace) {
    return workspace.id > 0 ? String(workspace.id) : workspace.name.startsWith("special:") ? workspace.name : "name:" + workspace.name;
}
function workspaceCommand(workspace, monitor, lua) {
    const selector = workspaceSelector(workspace);
    if (lua) return ["hyprctl", "eval", (monitor ? "hl.dispatch(hl.dsp.focus({ monitor = " + luaString(monitor) + " })); " : "")
        + "hl.dispatch(hl.dsp.focus({ workspace = " + luaString(selector) + " }))"];
    if ((monitor && !/^[a-zA-Z0-9_.:-]+$/.test(monitor)) || !/^[a-zA-Z0-9_.:-]+$/.test(selector)) return [];
    return ["hyprctl", "--batch", (monitor ? "dispatch focusmonitor " + monitor + "; " : "") + "dispatch workspace " + selector];
}
function windowCommand(window, lua) {
    const address = String(window.address).replace(/^0x/, "");
    if (!/^[0-9a-fA-F]+$/.test(address)) return [];
    return lua ? ["hyprctl", "eval", "hl.dispatch(hl.dsp.focus({ window = " + luaString("address:0x" + address) + " }))"]
        : ["hyprctl", "dispatch", "focuswindow", "address:0x" + address];
}
