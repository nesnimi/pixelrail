# GoogleDot dependency

Official source/release: https://github.com/ful1e5/Google_Cursor/tree/v2.0.0
GPLv3: GoogleDot-LICENSE.txt. No cursor binary is shipped in this tracked directory.

Run `python scripts/prepare-cursor-assets.py --download` from the repository once.
It downloads only Black/White Linux release assets, verifies pinned SHA256, keeps
24/28/32 image chunks and all roles/aliases, writes `.cache/cursor-assets` only.
No system installation or activation. Later runs are offline without --download.
Pixels, hotspots, animation delays/frames for retained sizes remain unchanged.
The generated theme includes LICENSE/SOURCE.txt and an integrity manifest.

These are privately staged external dependencies, not a bundled binary release.
For redistribution, include corresponding upstream source/build inputs and the
PixelRail size-filter script as required by GPL; a URL alone is not a source offer.
