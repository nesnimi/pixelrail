-- PixelRail End4-like shortcuts for Hyprland 0.57 (Lua).
-- Compatible with PixelRail v0.2. Lightweight replacements for Quickshell features.
-- This file is loaded by ~/.config/hypr/hyprland.lua via dofile().
local home = os.getenv('HOME') or '/home'
local source = debug.getinfo(1, 'S').source:sub(2)
local directory = source:match('^(.*)/') or '.'
local superTap = dofile(directory .. '/pixelrail-super-tap.lua')
hl.on('input.keyboard.key', superTap.key)
hl.on('keybinds.submap', superTap.cancel)
local function path_command(cmd)
  local prefix = home .. '/.local/bin/'
  if cmd:sub(1, #prefix) == prefix and home:find('[^%w%._/%-]') then
    local name, arguments = cmd:sub(#prefix + 1):match('^(%S+)(.*)$')
    return "'" .. (prefix .. name):gsub("'", "'\\''") .. "'" .. arguments
  end
  return cmd
end
local function exec(cmd) return hl.dsp.exec_cmd(path_command(cmd)) end
local function tool(action)
  return exec(home .. '/.local/bin/pixelrail-end4 ' .. action)
end
local function bind(key, dispatcher, desc, flags)
  flags = flags or {}
  flags.description = desc
  hl.bind(key, dispatcher, flags)
end

-- Shell: native Quickshell menus with script-level recovery fallback.
bind('SUPER + Slash', tool('keys'), 'Система: Все сочетания')
bind('SUPER + F1', tool('keys'), 'Система: Все сочетания (работает при русской раскладке)')
bind('SUPER + Tab', tool('windows'), 'Обзор: Переключатель окон')
bind('SUPER + A', exec(home .. '/.local/bin/pixelrail-control'), 'Оболочка: Pixel Control Center')
bind('SUPER + N', exec(home .. '/.local/bin/pixelrail-notifications open'), 'Оболочка: Уведомления')
bind('SUPER + M', tool('media'), 'Медиа: Управление плеером')
bind('SUPER + G', tool('controls'), 'Оболочка: Панель действий')
bind('SUPER + J', tool('bar'), 'Оболочка: Показать/скрыть панель Waybar')
bind('CTRL + ALT + Delete', tool('session'), 'Сеанс: Выход, сон, перезагрузка')
bind('SUPER + V', exec(home .. '/.local/bin/pixelrail-clipboard'), 'Утилиты: История буфера обмена')
bind('SUPER + Period', tool('emoji'), 'Утилиты: Эмодзи в буфер обмена')
bind('CTRL + SUPER + T', tool('wallpaper'), 'Внешний вид: Выбрать обои')
bind('CTRL + SUPER + P', exec(home .. '/.local/bin/pixelrail-profile toggle'), 'Внешний вид: Battery/Performance (эффекты)')

-- Applications
bind('SUPER + Return', exec('kitty'), 'Приложения: Терминал')
bind('SUPER + T', exec('kitty'), 'Приложения: Терминал')
bind('CTRL + ALT + T', exec('kitty'), 'Приложения: Терминал')
bind('SUPER + E', exec('thunar'), 'Приложения: Файловый менеджер')
bind('SUPER + W', tool('browser'), 'Приложения: Chrome / браузер')
bind('SUPER + C', tool('code'), 'Приложения: Редактор кода')
bind('SUPER + X', exec('kitty -e nano'), 'Приложения: Текстовый редактор')
bind('SUPER + I', tool('controls'), 'Приложения: Настройки и действия')
bind('CTRL + SHIFT + Escape', tool('taskmanager'), 'Приложения: Диспетчер задач')

-- Windows and mouse. Match end-4 instead of PixelRail's original Super+D launcher.
bind('SUPER + Q', hl.dsp.window.close(), 'Окна: Закрыть активное')
bind('SUPER + SHIFT + Q', hl.dsp.window.close(), 'Окна: Закрыть (совместимость со старым PixelRail)')
bind('SUPER + F', hl.dsp.window.fullscreen({ mode = 'fullscreen', action = 'toggle' }), 'Окна: Полный экран')
bind('SUPER + D', hl.dsp.window.fullscreen({ mode = 'maximized', action = 'toggle' }), 'Окна: Развернуть')
bind('SUPER + ALT + Space', hl.dsp.window.float({ action = 'toggle' }), 'Окна: Плавающее/плиточное')
bind('SUPER + P', hl.dsp.window.pin(), 'Окна: Закрепить поверх')
-- Explicit launcher shortcuts remain available alongside the guarded Super tap.
bind('SUPER + R', exec(home .. '/.local/bin/pixelrail-menu command'), 'Приложения: Выполнить команду')
bind('SUPER + SPACE', exec(home .. '/.local/bin/pixelrail-launcher'), 'Приложения: Поиск приложений (доп.)')
bind('ALT + Tab', hl.dsp.window.cycle_next(), 'Окна: Следующее окно')
local arrows = { {'Left','l'}, {'Right','r'}, {'Up','u'}, {'Down','d'} }
for _, v in ipairs(arrows) do
  bind('SUPER + ' .. v[1], hl.dsp.focus({ direction = v[2] }), 'Окна: Фокус ' .. v[1])
  bind('SUPER + SHIFT + ' .. v[1], hl.dsp.window.move({ direction = v[2] }), 'Окна: Переместить ' .. v[1])
end
hl.bind('SUPER + mouse:272', function() superTap.cancel(); hl.dispatch(hl.dsp.window.drag()) end, { mouse = true, description = 'Окна: Переместить мышью' })
hl.bind('SUPER + mouse:273', function() superTap.cancel(); hl.dispatch(hl.dsp.window.resize()) end, { mouse = true, description = 'Окна: Изменить размер мышью' })

-- Workspaces, 1..10. In end-4 Super+Alt+number moves a window.
for i = 1, 10 do
  local key = tostring(i % 10)
  local ws = tostring(i)
  bind('SUPER + ' .. key, hl.dsp.focus({ workspace = ws }), 'Рабочие столы: Перейти на ' .. ws)
  bind('SUPER + ALT + ' .. key, hl.dsp.window.move({ workspace = ws, follow = false }), 'Рабочие столы: Отправить окно на ' .. ws)
  bind('SUPER + SHIFT + ' .. key, hl.dsp.window.move({ workspace = ws, follow = false }), 'Рабочие столы: Переместить (старое сочетание) ' .. ws)
end
bind('CTRL + SUPER + Left', hl.dsp.focus({ workspace = 'r-1' }), 'Рабочие столы: Предыдущий')
bind('CTRL + SUPER + Right', hl.dsp.focus({ workspace = 'r+1' }), 'Рабочие столы: Следующий')
bind('SUPER + S', hl.dsp.workspace.toggle_special('special'), 'Рабочие столы: Показать scratchpad')
bind('SUPER + ALT + S', hl.dsp.window.move({ workspace = 'special:special', follow = false }), 'Рабочие столы: Убрать окно в scratchpad')

-- Capture and utilities
bind('SUPER + SHIFT + S', exec(home .. '/.local/bin/pixelrail-shot'), 'Снимки: Выделить область и сохранить')
bind('SUPER + SHIFT + C', tool('picker'), 'Утилиты: Цвет пикселя в буфер')
bind('Print', tool('screenshot'), 'Снимки: Весь экран в буфер')
bind('CTRL + Print', tool('screenshot-save'), 'Снимки: Весь экран в файл')
bind('SUPER + SHIFT + R', tool('record-region'), 'Запись: Начать/остановить выделенную область')
bind('CTRL + ALT + R', tool('record-screen'), 'Запись: Начать/остановить экран')

-- Media, lock and power
bind('SUPER + SHIFT + N', exec('playerctl next'), 'Медиа: Следующий трек')
bind('SUPER + SHIFT + B', exec('playerctl previous'), 'Медиа: Предыдущий трек')
bind('SUPER + SHIFT + P', exec('playerctl play-pause'), 'Медиа: Пауза/воспроизвести')
bind('SUPER + SHIFT + M', exec('wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle'), 'Медиа: Выключить звук')
bind('SUPER + ALT + M', exec('wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle'), 'Медиа: Выключить микрофон')
bind('SUPER + L', exec('hyprlock'), 'Сеанс: Блокировка экрана')
bind('SUPER + SHIFT + L', exec('systemctl suspend'), 'Сеанс: Сон')
hl.bind('XF86AudioRaiseVolume', exec(home .. '/.local/bin/pixelrail-system volume-up'), { repeating = true })
hl.bind('XF86AudioLowerVolume', exec(home .. '/.local/bin/pixelrail-system volume-down'), { repeating = true })
hl.bind('XF86AudioMute', exec(home .. '/.local/bin/pixelrail-system volume-mute'))
hl.bind('XF86MonBrightnessUp', exec(home .. '/.local/bin/pixelrail-system brightness-up'), { repeating = true })
hl.bind('XF86MonBrightnessDown', exec(home .. '/.local/bin/pixelrail-system brightness-down'), { repeating = true })

-- Release binding keeps lock-screen inhibition under Hyprland's control.
-- Every other key press cancels the tap, including unbound keys and modifiers.
for _, key in ipairs({ 'SUPER_L', 'SUPER_R' }) do
  bind('SUPER + ' .. key, function()
    if superTap.release() then hl.exec_cmd(path_command(home .. '/.local/bin/pixelrail-launcher')) end
  end, 'Приложения: Поиск по одиночному Super', { release = true })
end
