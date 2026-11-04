.pragma library
// Logical pixels; the caller supplies the actual Sidebar/Waybar inset on its screen.
function bottom(mode) { return ["launcher", "command", "clipboard", "windows", "emoji"].includes(mode); }
function left(screenWidth, inset) { return Math.max(0, Math.min(inset, Math.max(0, screenWidth - 24))); }
function width(desired, screenWidth, inset) { return Math.max(1, Math.min(desired, screenWidth - left(screenWidth, inset) - 12)); }
function height(desired, screenHeight) { return Math.max(1, Math.min(desired, screenHeight - 24)); }
