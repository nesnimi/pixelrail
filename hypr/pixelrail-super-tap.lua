-- XKB codes on the standard evdev keymap: Super_L=133, Super_R=134.
-- No key interception, subprocesses, timers or replacement of chord bindings.
local held, eligible = {}, false
local function is_super(code) return code == 133 or code == 134 end
return {
  key = function(code, _, state)
    if state == 1 then
      if not held[code] then
        eligible = is_super(code) and next(held) == nil
      end
      held[code] = true
    elseif state == 0 then
      held[code] = nil
      -- Keep eligibility until the release bind runs (event ordering independent).
    end
  end,
  cancel = function() eligible = false end,
  release = function()
    local result = eligible
    eligible = false
    return result
  end,
}
