import QtQuick
import QtTest
import Quickshell
import "../../quickshell/components" as Parts
Item {
    id:root
    Parts.WallpaperView {
        id:view;anchors.fill:parent
        backend:Quickshell.env("PIXELRAIL_TEST_THUMB_HELPER")
        entries:[{id:"lost",title:"Удалённая миниатюра.png",subtitle:"Test",thumbnail:"file:///pixelrail-test-evicted-thumbnail.png"}]
    }
    TestCase {id:tc;when:false}
    function run() {
        let count=0;
        while(!view.canApply && count++<50)tc.wait(20);
        if(!view.missingCached.lost || !view.thumbnails.lost || !view.canApply)throw new Error("evicted thumbnail not regenerated "+JSON.stringify({missing:view.missingCached,thumbs:view.thumbnails,failures:view.failures,canApply:view.canApply}));
        if(view.failures.lost)throw new Error("duplicate error marked regenerated preview failed");
    }
}
