import QtQuick
import QtTest
import "../quickshell/modules/launcher/Search.js" as Search

TestCase {
    name: "LauncherSearch"
    property var apps: [
        {id: "chrome", name: "Google Chrome", genericName: "Web Browser", keywords: ["Internet"],categories:["Network","WebBrowser"]},
        {id: "kitty", name: "Kitty", genericName: "Terminal", keywords: [],categories:["System","TerminalEmulator"]},
        {id: "files", name: "Файлы", genericName: "File manager", keywords: ["Папки"],categories:["System","FileTools","FileManager"]},
        {id: "hidden", name: "Hidden", noDisplay: true}
    ]
    function test_search() {
        compare(Search.search(apps, "").length, 3);
        compare(Search.search(apps, "  CHROME  ")[0].id, "chrome");
        compare(Search.search(apps, "google internet")[0].id, "chrome");
        compare(Search.search(apps, "terminal")[0].id, "kitty");
        compare(Search.search(apps, "ФАЙ")[0].id, "files");
        compare(Search.search(apps, "папки")[0].id, "files");
        compare(Search.search(apps, "hidden").length, 0);
        compare(Search.search(apps, "no such application").length, 0);
        compare(Search.search(apps, "$(touch sentinel)").length, 0);
    }
    function test_relevance() {
        const entries=[{id:"1",name:"Chrome Canary"},{id:"2",name:"Chrome"},{id:"3",name:"Google Chrome"},
                       {id:"4",name:"Web",keywords:["chrome"]},{id:"5",name:"Файлы проекта"},{id:"6",name:"Файлы"}];
        compare(Search.search(entries,"chrome").map(app=>app.id),["2","1","3","4"]);
        compare(Search.search(entries,"ФАЙЛЫ").map(app=>app.id),["6","5"]);
    }
    function test_suggestions_and_bounded_usage() {
        const listed=Search.search(apps,"");
        compare(Search.suggestions(listed,{},8).map(app=>app.id),listed.map(app=>app.id));
        let counts=Search.record({},"files");counts=Search.record(counts,"files");
        compare(Search.suggestions(listed,counts,8)[0].id,"files");compare(counts.files,2);
        counts=Search.record(counts,"uninstalled");
        verify(!Search.suggestions(listed,counts,8).some(app=>app.id==="uninstalled"));
        let large={};for(let i=0;i<100;i++)large["app-"+i]=i+1;
        large.invalid="99";large.negative=-10;large.infinite=Infinity;
        const clean=Search.cleanCounts(large);compare(Object.keys(clean).length,64);
        verify(clean.invalid===undefined && clean.negative===undefined && clean.infinite===undefined);
        compare(Object.keys(Search.cleanCounts([])).length,0);
        compare(Search.cleanCounts({large:100000000}).large,1000000);
        const extended=Search.record(clean,"new-app");compare(Object.keys(extended).length,64);compare(extended["new-app"],1);
    }
    function test_home_categories_and_explicit_utility_search() {
        const entries=[{id:"settings",name:"AA Settings",categories:["Settings","HardwareSettings"]},
                       {id:"rename",name:"AA Rename",categories:["Utility","Filesystem"]},
                       {id:"mixer",name:"AA Volume",categories:["AudioVideo","Mixer"]},
                       {id:"filemanager",name:"Files",categories:["System","FileTools","FileManager"]},
                       {id:"unknown",name:"Unknown",categories:[]}];
        compare(Search.suggestions(entries,{},8).map(app=>app.id),["filemanager"]);
        compare(Search.suggestions(entries,{mixer:1},8).map(app=>app.id),["filemanager"]);
        compare(Search.suggestions(entries,{mixer:2},8).map(app=>app.id),["mixer","filemanager"]);
        compare(Search.search(entries,"volume")[0].id,"mixer");
        compare(Search.suggestions([entries[0],entries[1],entries[4]],{},8).length,0);
    }
    function test_visibility_and_command_dedup() {
        const entries=[{id:"primary",name:"App",command:["editor","%U"],categories:["Office"]},
                       {id:"alias",name:"App Alias",command:["editor","%F"],categories:["Office"]},
                       {id:"profile",name:"Other profile",command:["editor","--profile","work"],categories:["Office"]},
                       {id:"hidden",name:"Hidden",hidden:true}, {id:"nodisplay",name:"Hidden helper",noDisplay:true}];
        compare(Search.search(entries,"").length,2);
        compare(Search.search(entries,"alias")[0].id,"alias");
        compare(Search.suggestions(entries,{alias:3},8)[0].id,"alias");
        const metadata={primary:{showInDesktop:false,categories:["Office"]},alias:{hidden:true},profile:{noDisplay:true}};
        compare(Search.search(entries,"",metadata).length,0);
        compare(Search.suggestions(entries,{primary:100},8,metadata).length,0);
        compare(Search.search(entries,"app",metadata)[0].id,"primary");
    }
}
