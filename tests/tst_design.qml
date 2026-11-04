import QtQuick
import QtTest
import "../quickshell/ui/Symbols.js" as Symbols
import "../quickshell/ui/AppIcons.js" as Apps
TestCase {
    name:"PixelDesignSymbols"
    function test_svg_and_bounded_cache() {
        const plain=decodeURIComponent(Symbols.svg("search","#abcdef",false));verify(plain.includes('fill="#abcdef"'));
        verify(Symbols.svg("missing-icon","#abcdef",true).startsWith("data:image/svg+xml,"));
        for(let i=0;i<300;i++)Symbols.svg("wifi","#"+i.toString(16).padStart(6,"0"),i%2===0);
        verify(Symbols.keys.length<=96);compare(Object.keys(Symbols.cache).length,Symbols.keys.length);
        for(const name of ["wifi","power_settings_new","bluetooth","search","volume_up","volume_off","brightness_6","notifications"])verify(!!Symbols.paths[name],name);
    }
    function test_real_semantic_resources() {
        for(const pair of [["/opt/google/chrome/product_logo_256.png","public"],["kitty","terminal"],["org.kde.dolphin","folder"],["code","code"],["org.telegram.desktop","chat"]]) {
            compare(Apps.semantic(pair[0],""),pair[1]);verify(!!Symbols.paths[pair[1]]);
        }
        compare(Apps.semantic("unknown-app","Unknown"),"");
        compare(Apps.semantic("/tmp/tmpv123/music.svg","Music"),"music_note");
        compare(Apps.semantic("/tmp/tmpv123/notes.svg","Notes"),"");
        compare(Apps.semantic("org.kde.vlc","VLC"),"movie");
        verify(Apps.symbolicCandidates("org.kde.dolphin","folder").includes("folder-symbolic"));
    }
}
