-- Evaluate repository bind registration against a side-effect-free Hyprland stub.
local binds, events, launches = {}, {}, {}
local function dispatcher(name)
  return function(options) return {name = name, options = options} end
end
hl = {
  on = function(name, callback) events[name] = callback end,
  bind = function(key, action, flags)
    local normalized = key:upper():gsub('%s+', '')
    assert(not binds[normalized], 'Duplicate binding: ' .. key)
    binds[normalized] = {action = action, flags = flags or {}}
  end,
  exec_cmd = function(command) table.insert(launches, command) end,
  dispatch = function(_) end,
  dsp = {exec_cmd = function(command) return {command = command} end,
         focus = dispatcher('focus'),
         window = {}, workspace = {toggle_special = dispatcher('special')}}
}
for _, name in ipairs({'close','fullscreen','float','pin','cycle_next','move','drag','resize'}) do
  hl.dsp.window[name] = dispatcher(name)
end
dofile('hypr/pixelrail-end4-keys.lua')
assert(binds['SUPER+SHIFT+S'].action.command:match('pixelrail%-shot$'))
assert(binds['SUPER+A'].action.command:match('pixelrail%-control$'))
assert(binds['SUPER+N'].action.command:match('pixelrail%-notifications open$'))
for _, item in ipairs({{'XF86AUDIORAISEVOLUME','volume-up'}, {'XF86AUDIOLOWERVOLUME','volume-down'}, {'XF86AUDIOMUTE','volume-mute'}, {'XF86MONBRIGHTNESSUP','brightness-up'}, {'XF86MONBRIGHTNESSDOWN','brightness-down'}}) do
  local binding=assert(binds[item[1]], 'Missing physical key: '..item[1])
  assert(binding.action.command:match('pixelrail%-system '..item[2]:gsub('%-','%%-')..'$'), 'Wrong multimedia route: '..item[1])
  if item[2]~='volume-mute' then assert(binding.flags.repeating) end
end
assert(binds['SUPER+Q'].action.name == 'close')
assert(binds['SUPER+D'].action.options.mode == 'maximized')
assert(binds['SUPER+R'].action.command:match('pixelrail%-menu command$'))
assert(binds['SUPER+SPACE'].action.command:match('pixelrail%-launcher$'))
assert(binds['SUPER+SLASH'] and binds['SUPER+F1'] and binds['SUPER+TAB'] and binds['SUPER+V'])
local key = events['input.keyboard.key']
for _, super in ipairs({133,134}) do
  local release = binds[super == 133 and 'SUPER+SUPER_L' or 'SUPER+SUPER_R']
  assert(release.flags.release and not release.flags.locked)
  key(super,0,1); key(super,0,0); release.action()
  local before = #launches
  key(super,0,1); key(50,0,1); key(39,0,1); key(39,0,0); key(50,0,0); key(super,0,0); release.action()
  assert(#launches == before, 'Screenshot chord toggled launcher')
  for _, other in ipairs({24,40,27,65,50,10,111,38,57}) do
    key(super,0,1); key(other,0,1); key(other,0,0); key(super,0,0); release.action()
    assert(#launches == before, 'Chord opened launcher')
  end
end
assert(#launches == 2)
local count = 0; for _ in pairs(binds) do count = count + 1 end
print('Bind registration: ' .. count .. ' unique bindings; Super/Q/D/commands passed')
