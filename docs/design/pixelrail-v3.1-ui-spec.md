# PixelRail v3.1 RC1 — UI specification

База: текущий v3.0 candidate; незакоммиченные изменения сохранены. Референсы
pixelrail_1.png / pixelrail_2.png задают тональные поверхности, rounded controls,
крупные пиктограммы и компактные группы. Геометрия и backend важнее рисунка.

- Sidebar: rail 54, zone 66; Power/Wi-Fi/Battery; низ workspace/apps/P сохранён.
- CC: 400 logical px, default 50%, resize 30–75%, один Window/две вкладки,
  без scrollbar и верхнего close. Две Wi-Fi/BT плитки с Rounded symbols,
  EN/RU + профиль, два live sliders, battery/time, условный MPRIS, power/settings.
- Launcher: прежние 540 px, bottom-left, поиск без замены backend.
- Единый Palette → ThemeManager; MD3 JSON роли остаются прежними, QML aliases
  surfaceText/primaryText сохраняются (onX имена имеют особую семантику QML).
- Space 4/8/12/16/20/24, radius 8/12/16/20/26/pill. Text 11/12/14/16/20/26.
- Motion: hover 120, state 160, panel 200 ms, OSD timeout 1300 ms; reduced motion
  обнуляет duration. Никакого постоянного движения или shader blur.
- Material Symbols Rounded SVG subset, outlined/filled, Apache-2.0, bundled offline.
- App icons: original по умолчанию; themed использует только *-symbolic либо
  собственный Material app fallback на tonal container, не tint полноцветного PNG.
- Settings: lazy page существующего CC, реальные theme/ui/profile/panel controls.
  XDG theme.json получает versioned UI поля с сохранением старых/неизвестных ключей.
- GoogleDot: проверенный источник/лицензия, системная интеграция только opt-in;
  без установки/записи живых конфигов при разработке. При отсутствии установленной
  темы никаких фиктивных переключателей.

Проверки после этапов: lint + UI/runtime; затем полный regression и sandbox
benchmark. Аппаратные Bluetooth/Fn/HiDPI/cursor/suspend проверяет владелец вручную.

Лицензии: [Material Symbols](https://developers.google.com/fonts/docs/material_symbols),
[Roboto OFL](https://github.com/google/fonts/tree/main/ofl/roboto),
[Google Sans Flex OFL](https://github.com/googlefonts/googlesans-flex),
[GoogleDot GPL](https://github.com/ful1e5/Google_Cursor). Бинарники GoogleDot
не включены; fonts/icons загружены из официальных источников, лицензии сохранены.
