"""Redaction and reproducible source archives; no Git writes, network or publication."""
from pathlib import Path
import sys
import tarfile
import tempfile
import struct
import unittest
sys.path.insert(0,str(Path.cwd()/'scripts'))
from publication_audit import findings
from package_release import package


class Publication(unittest.TestCase):
    def test_public_pngs_have_no_personal_text_or_exif_metadata(self):
        for path in (Path.cwd()/'docs/screenshots').glob('*.png'):
            data=path.read_bytes();self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n')
            offset=8
            while offset<len(data):
                length=struct.unpack('!I',data[offset:offset+4])[0];kind=data[offset+4:offset+8]
                self.assertNotIn(kind,[b'tEXt',b'iTXt',b'zTXt',b'eXIf'],str(path))
                offset+=12+length
    def test_redaction(self):
        secret='gh'+'p_'+'a'*40
        hits=findings(secret.encode(),'fixture')
        self.assertEqual(hits[0]['kind'],'github-token');self.assertNotIn(secret,str(hits))
        self.assertTrue(findings(('/'+'home/'+'private-owner/file').encode(),'fixture'))
        self.assertFalse(findings(b'/home/user/example','fixture'))

    def test_reproducible_archive_no_cache_history_native_or_refs(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/'.cache') as tmp:
            root=Path(tmp)
            for name in ['LICENSE','THIRD_PARTY_NOTICES.md','README.md','README.ru.md']:(root/name).write_text('fixture\n')
            for name in ['scripts/example.py','quickshell/shell.qml','quickshell/native/plugin.so','quickshell/native/build-info.json','.cache/private','pixelrail_1.png','docs/design/screenshots/private.png','scripts/.env']:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture\n')
            first=package(root,root/'.cache/dist','3.1.0');second=package(root,root/'.cache/dist','3.1.0')
            self.assertEqual(first['sha256'],second['sha256'])
            with tarfile.open(root/first['archive']) as archive:names=archive.getnames()
            self.assertTrue(any(name.endswith('/scripts/example.py') for name in names))
            self.assertFalse(any('.cache/' in name or name.endswith(('.so','.env','build-info.json','pixelrail_1.png','private.png')) for name in names))


if __name__=='__main__':unittest.main()
