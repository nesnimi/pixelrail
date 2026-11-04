"""Desktop metadata reader: isolated XDG directories, no executable or service calls."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path.cwd()/'scripts'))
from launcher_entries import catalog


class Entries(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(dir=Path.cwd()/'.cache');self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name)
        self.env={'HOME':str(self.base),'XDG_DATA_HOME':str(self.base/'user'),'XDG_DATA_DIRS':str(self.base/'system'),'XDG_CURRENT_DESKTOP':'Hyprland:TestDesktop'}

    def entry(self,name,extra='',system=False):
        root=self.base/('system' if system else 'user')/'applications'
        path=root/(name+'.desktop');path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('[Desktop Entry]\nType=Application\nName=Тест ✓\nExec=never-executed %U\n'+extra+'\n')
        return path

    def test_visibility_and_categories(self):
        for name,extra in {'normal':'Categories=Office;Utility;','hidden':'Hidden=true','nodisplay':'NoDisplay=true','native':'OnlyShowIn=Hyprland;','foreign':'OnlyShowIn=GNOME;','excluded':'NotShowIn=Hyprland;','second':'OnlyShowIn=TestDesktop;'}.items():self.entry(name,extra)
        data=catalog(self.env)['entries']
        self.assertEqual(data['normal']['categories'],['Office','Utility'])
        self.assertTrue(data['hidden']['hidden']);self.assertTrue(data['nodisplay']['noDisplay'])
        self.assertTrue(data['native']['showInDesktop']);self.assertTrue(data['second']['showInDesktop'])
        self.assertFalse(data['foreign']['showInDesktop']);self.assertFalse(data['excluded']['showInDesktop'])

    def test_override_hidden_tombstone_nested_and_bad_files(self):
        self.entry('overridden','Categories=Network;',system=True);self.entry('overridden','Hidden=true')
        self.entry('vendor/inside','OnlyShowIn=Hyprland;')
        bad=self.entry('invalid');bad.write_text('invalid desktop file')
        self.entry('wrongtype','Type=Link')
        data=catalog(self.env)['entries']
        self.assertTrue(data['overridden']['hidden']);self.assertTrue(data['invalid']['hidden']);self.assertTrue(data['wrongtype']['hidden'])
        self.assertIn('vendor-inside',data)

    def test_missing_directories_and_desktop_fallback(self):
        self.assertEqual(catalog(self.env)['entries'],{})
        self.entry('native','OnlyShowIn=Hyprland;')
        self.env['XDG_CURRENT_DESKTOP']=''
        self.assertTrue(catalog(self.env)['entries']['native']['showInDesktop'])


if __name__=='__main__':unittest.main()
