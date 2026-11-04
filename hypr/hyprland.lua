-- PixelRail sample for Hyprland 0.57 Lua. No GPU-specific environment settings.
-- Existing hyprland.conf remains backed up and unused when hyprland.lua exists.
hl.env("XCURSOR_SIZE", "24")
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })

local home = os.getenv("HOME") or "/home"
local profile = "battery"
local cache = os.getenv("XDG_CACHE_HOME") or (home .. "/.cache")
local file = io.open(cache .. "/pixelrail/profile", "r")
if file then
  local value = file:read("*l")
  if value == "performance" then profile = value end
  file:close()
end
local fancy = profile == "performance"

hl.config({
  general = { gaps_in = 8, gaps_out = 12, border_size = 2, resize_on_border = true },
  decoration = {
    rounding = 14,
    blur = { enabled = fancy, size = 3, passes = 1 },
    shadow = { enabled = fancy },
  },
  input = {
    kb_layout = "us,ru",
    kb_options = "grp:alt_shift_toggle",
    follow_mouse = 1,
    touchpad = { natural_scroll = true, tap_to_click = true },
  },
  misc = { disable_hyprland_logo = true, disable_splash_rendering = true },
})

hl.curve("pixelrail", { type = "bezier", points = { {0.22, 1.0}, {0.36, 1.0} } })
hl.animation({ leaf = "global", enabled = fancy, speed = 3.5, bezier = "pixelrail" })
if fancy then
  hl.animation({ leaf = "windows", enabled = true, speed = 3.5, bezier = "pixelrail", style = "popin 92%" })
  hl.animation({ leaf = "workspaces", enabled = true, speed = 4.0, bezier = "pixelrail", style = "slidefade 15%" })
  hl.animation({ leaf = "fade", enabled = true, speed = 3.0, bezier = "pixelrail" })
end

-- One autostart script; never changes GPU drivers or system services.
hl.on("hyprland.start", function()
  local command = string.format("%q", home .. "/.local/bin/pixelrail-start")
  command = command:gsub("%$", "\\$"):gsub("`", "\\`")
  hl.exec_cmd(command)
end)

-- PIXELRAIL END4 KEYS v0.3
-- Most common end-4 keybinds, implemented with lightweight PixelRail apps.
-- Edit ~/.config/hypr/pixelrail-end4-keys.lua to customize individual binds.
dofile((os.getenv("HOME") or "") .. "/.config/hypr/pixelrail-end4-keys.lua")
