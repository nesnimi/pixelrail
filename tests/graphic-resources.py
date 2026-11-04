"""Offline assets integrity, semantic app icons and native XCursor decode; no apply."""
import ctypes as C
import ctypes.util
import hashlib
import importlib.util
import json
import os
from unittest.mock import patch
from pathlib import Path
import struct
import unittest
ROOT=Path.cwd()
spec=importlib.util.spec_from_file_location('cursor_prepare',ROOT/'scripts/prepare-cursor-assets.py');cursor=importlib.util.module_from_spec(spec);spec.loader.exec_module(cursor)
class Image(C.Structure):
    _fields_=[(name,C.c_uint) for name in ('version','size','width','height','xhot','yhot','delay')]+[('pixels',C.POINTER(C.c_uint32))]
class Images(C.Structure):
    _fields_=[('nimage',C.c_int),('images',C.POINTER(C.POINTER(Image))),('name',C.c_char_p)]
class Resources(unittest.TestCase):
    def test_material_and_font_checksums(self):
        hashes=json.loads((ROOT/'quickshell/assets/checksums.json').read_text())
        for relative,sha in hashes.items():self.assertEqual(hashlib.sha256((ROOT/'quickshell/assets'/relative).read_bytes()).hexdigest(),sha,relative)
        for name in ('public','terminal','folder','code','mail','chat','image','movie','music_note'):
            for suffix in ('','_fill1'):self.assertTrue((ROOT/'quickshell/assets/symbols'/(name+suffix+'.svg')).is_file())
        # The actual offline PixelIcon JS must contain the same paths as assets;
        # otherwise a newly copied SVG can leave the running UI on an old icon.
        script=(ROOT/'quickshell/ui/Symbols.js').read_text()
        paths=json.loads(script.split('var paths=',1)[1].split(';\nvar cache',1)[0])
        for name in ('wifi','wifi_fill1','wifi_off','wifi_off_fill1','light_mode'):
            self.assertEqual(paths[name],(ROOT/'quickshell/assets/symbols'/(name+'.svg')).read_text())
    def test_prune_rejects_invalid(self):
        for data in (b'',b'bad'*20,struct.pack('<4I',0x72756358,16,1,100)):
            with self.assertRaises(ValueError):cursor.prune(data)
    def test_prepared_cursor_dependency(self):
        directory=ROOT/'.cache/cursor-assets'
        if not (directory/'manifest.json').exists():self.skipTest('Run python scripts/prepare-cursor-assets.py --download once')
        manifest=json.loads((directory/'manifest.json').read_text());self.assertFalse(manifest['installed'])
        for theme,info in manifest['themes'].items():
            for name,sha in info['files'].items():self.assertEqual(hashlib.sha256((directory/theme/'cursors'/name).read_bytes()).hexdigest(),sha)
            for alias in info['aliases']:self.assertTrue((directory/theme/'cursors'/alias).resolve().is_file(),alias)
        library=ctypes.util.find_library('Xcursor')
        if not library:self.skipTest('libXcursor not installed; binary structure validated only')
        lib=C.CDLL(library);lib.XcursorFilenameLoadImages.argtypes=[C.c_char_p,C.c_int];lib.XcursorFilenameLoadImages.restype=C.POINTER(Images);lib.XcursorImagesDestroy.argtypes=[C.POINTER(Images)]
        lib.XcursorLibraryLoadImages.argtypes=[C.c_char_p,C.c_char_p,C.c_int];lib.XcursorLibraryLoadImages.restype=C.POINTER(Images)
        for theme in manifest['themes']:
            for role in ('default','text','pointer','ew-resize','ns-resize','move','wait','progress','not-allowed'):
                for size in (24,28,32):
                    images=lib.XcursorFilenameLoadImages(str(directory/theme/'cursors'/role).encode(),size)
                    self.assertTrue(images,(theme,role,size))
                    try:
                        self.assertGreater(images.contents.nimage,0)
                        for index in range(images.contents.nimage):
                            image=images.contents.images[index].contents
                            self.assertEqual(image.size,size);self.assertLess(image.xhot,image.width);self.assertLess(image.yhot,image.height)
                    finally:lib.XcursorImagesDestroy(images)
                    with patch.dict(os.environ,{'XCURSOR_PATH':str(directory)}):
                        named=lib.XcursorLibraryLoadImages(role.encode(),theme.encode(),size)
                        self.assertTrue(named,('theme lookup',theme,role,size))
                        lib.XcursorImagesDestroy(named)
if __name__=='__main__':unittest.main()
