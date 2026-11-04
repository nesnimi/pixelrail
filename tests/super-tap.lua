local function tracker() return dofile('hypr/pixelrail-super-tap.lua') end
local function press(t, key) t.key(key, 0, 1) end
local function release(t, key) t.key(key, 0, 0) end
for _, super in ipairs({133, 134}) do
  local t = tracker()
  press(t, super); release(t, super)
  assert(t.release(), 'single Super')
  assert(not t.release(), 'release cannot launch twice')
  -- Both ordering possibilities between Lua input event and release dispatcher.
  press(t, super); assert(t.release()); release(t, super)
  for _, other in ipairs({24, 40, 27, 65, 10, 50, 64, 37, 134 == super and 133 or 134}) do
    for _, superFirst in ipairs({true, false}) do
      t = tracker()
      press(t, super); press(t, other)
      if superFirst then release(t, super) else release(t, other) end
      assert(not t.release(), 'chord must cancel: ' .. other)
      if superFirst then release(t, other) else release(t, super) end
      press(t, super); release(t, super); assert(t.release(), 'next tap recovers')
    end
    t = tracker()
    press(t, other); press(t, super); release(t, super)
    assert(not t.release(), 'held key must block tap')
  end
  t = tracker(); press(t, super); t.cancel(); release(t, super)
  assert(not t.release(), 'mouse drag/submap cancels')
  t = tracker(); press(t, super); t.key(super, 0, 2); release(t, super)
  assert(t.release(), 'repeat produces one tap')
end
print('Super tap: passed')
