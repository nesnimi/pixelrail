# Third-party materials

PixelRail's original source code and documentation are MIT licensed, copyright
2026 **nesnimi**. This does not relicense third-party fonts, SVGs or cursor themes.

| Material | Location / source | License / distribution |
| --- | --- | --- |
| Material Symbols Rounded SVG paths | `quickshell/assets/symbols/`, [Google repository](https://github.com/google/material-design-icons/tree/10ecc14790612ca8fd164e3f4ffe9c16fc50d5b7/symbols/web) | Apache-2.0, included `LICENSE` and `SOURCE.md`; paths embedded in `quickshell/ui/Symbols.js` retain these terms. Runtime changes fill only. |
| Roboto | `quickshell/assets/fonts/Roboto.ttf`, [Google Fonts](https://github.com/google/fonts/tree/main/ofl/roboto) | SIL Open Font License 1.1, included `OFL.txt` and `SOURCE.md`. |
| GoogleDot Black / White | Optional downloads from [ful1e5/Google_Cursor v2.0.0](https://github.com/ful1e5/Google_Cursor/releases/tag/v2.0.0) | GPL-3.0; full license in `quickshell/assets/cursors/GoogleDot-LICENSE.txt`. Cursor binaries are **not** bundled in Git/source releases. Preparation caches selected upstream files locally and records source/checksums. |
| Installed application icons | Linux icon themes and `.desktop` entries | Owned/licensed by their respective packages. Not copied into PixelRail resources. |
| Google Sans Flex | Used only if installed with suitable glyph coverage | Not downloaded/bundled; its installation/license remains separate. Roboto is the bundled fallback. |
| PixelRail vector mark and screenshot fixtures | Original project QML / fixture code | MIT, nesnimi. Public documentation captures use fixture content, not personal desktop data. Material Symbols/font notices still apply to their rendered content. |

`pixelrail_1.png`, `pixelrail_2.png` and historical local design captures are private
development references with no asserted redistribution rights. They are excluded
from public packaging and ignored by Git; they have not been deleted locally.

Google, Google Pixel, Chrome and application names are trademarks of their owners.
PixelRail is an independent project, not affiliated with or endorsed by Google or
end-4. Visual/workflow inspiration is credited without claiming their code or assets.

The native plugin uses system Qt/Quickshell libraries; their licenses remain with
the installed packages. Source releases do not bundle Qt, Quickshell, drivers or
precompiled native binaries. Build the plugin against your installed Qt.
