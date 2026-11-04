.pragma library
// Desktop/icon identities, not window-title scraping. These are semantic symbols,
// not invented monochrome versions of third-party trademarks.
function semantic(icon, name) {
    const key=String(icon || "").toLowerCase();
    const rules=[[/chrome|chromium|firefox|brave|web-browser/,"public"],
        [/kitty|alacritty|konsole|terminal|foot(?:$|-)/,"terminal"],
        [/nautilus|dolphin|thunar|nemo|file-manager|system-file-manager|folder/,"folder"],
        [/vscode|visualstudio|visual-studio|(?:^|\/)code(?:$|\.)|codium/,"code"],
        [/telegram|signal|discord|chat/,"chat"],[/thunderbird|gmail|mail/,"mail"],
        [/gimp|krita|photos|image-viewer|gwenview/,"image"],
        [/(?:^|[\/._-])(?:vlc|mpv|video)(?:$|[\/._-])/,"movie"],[/spotify|music|rhythmbox/,"music_note"],
        [/settings|preferences-system/,"settings"],[/editor|libreoffice|document/,"description"]];
    for (const rule of rules)if(rule[0].test(key))return rule[1];
    return "";
}
function symbolicCandidates(icon, semantic) {
    const values=[];
    if(icon && !icon.includes("/") && !icon.includes(":"))values.push(icon.replace(/-symbolic$/,"")+"-symbolic");
    const category={public:"web-browser",terminal:"utilities-terminal",folder:"folder",code:"text-editor",chat:"user-available",mail:"mail-unread",image:"image-x-generic",movie:"video-x-generic",music_note:"audio-x-generic",description:"text-x-generic",settings:"preferences-system"}[semantic];
    if(category)values.push(category+"-symbolic");
    return values;
}
