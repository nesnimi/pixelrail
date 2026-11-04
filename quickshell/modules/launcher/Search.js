// Pure application search/ranking. No shell execution or background indexer.
function visible(app, metadata, home) {
    var data = metadata && metadata[app.id] || {};
    return !app.hidden && !app.noDisplay && !data.hidden && !data.noDisplay && (!home || data.showInDesktop !== false);
}

function identity(app) {
    // Preserve distinct profiles/actions; merge only identical launch commands.
    var command = (app.command || []).filter(function(arg) { return !/^%[fFuUick]$/.test(arg); });
    return command.length ? JSON.stringify([command,!!app.runInTerminal,app.workingDirectory || '']) : 'id:' + app.id;
}

function unique(entries) {
    var seen = Object.create(null), ids = Object.create(null);
    return entries.filter(function(app) {
        var key = identity(app);
        if (seen[key] || ids[app.id]) return false;
        seen[key] = true; ids[app.id] = true; return true;
    });
}

function search(entries, query, metadata) {
    var words = query.trim().toLocaleLowerCase().split(/\s+/).filter(function(w) { return w.length; });
    return unique(entries.filter(function(app) {
        var haystack = [app.name, app.genericName, app.id, (app.keywords || []).join(' ')].join(' ').toLocaleLowerCase();
        return visible(app, metadata, !words.length) && words.every(function(word) { return haystack.indexOf(word) !== -1; });
    }).sort(function(a, b) {
        var q = words.join(' ');
        var an = a.name.trim().toLocaleLowerCase(), bn = b.name.trim().toLocaleLowerCase();
        var ar = an === q ? 0 : an.indexOf(q) === 0 ? 1 : 2;
        var br = bn === q ? 0 : bn.indexOf(q) === 0 ? 1 : 2;
        return ar - br || a.name.localeCompare(b.name) || a.id.localeCompare(b.id);
    }));
}

function cleanCounts(value) {
    var result = Object.create(null);
    if (!value || typeof value !== 'object' || Array.isArray(value)) return result;
    Object.keys(value).filter(function(id) {
        return id.length > 0 && id.length <= 256 && typeof value[id] === 'number' && isFinite(value[id]) && value[id] > 0;
    }).sort(function(a,b) { return value[b] - value[a] || a.localeCompare(b); }).slice(0,64).forEach(function(id) {
        result[id] = Math.min(1000000, Math.floor(value[id]));
    });
    return result;
}

function record(counts, id) {
    var next = cleanCounts(counts);
    if (typeof id === 'string' && id.length > 0 && id.length <= 256) {
        // A full history must still learn a newly launched application.
        if (!next[id] && Object.keys(next).length >= 64) {
            var weakest=Object.keys(next).sort(function(a,b) {return next[a]-next[b] || a.localeCompare(b);})[0];
            delete next[weakest];
        }
        next[id] = Math.min(1000000, (next[id] || 0) + 1);
    }
    return cleanCounts(next);
}

function homePriority(app, metadata) {
    var data = metadata && metadata[app.id];
    if (metadata && !data) return 0;
    var categories = data && data.categories || app.categories || [];
    function has(group) { return group.some(function(category) { return categories.indexOf(category) !== -1; }); }
    if (has(['Settings','HardwareSettings','DesktopSettings','X-Settings-Panel','PackageManager','Monitor','Mixer'])) return 0;
    if (has(['FileManager','TerminalEmulator','WebBrowser','TextEditor'])) return 3;
    if (has(['FileTools','Filesystem'])) return 0;
    if (has(['Network','Office','Development','Graphics','AudioVideo','Audio','Video','Education','Game','Science'])) return 2;
    return has(['Calculator','Calendar','Clock','Archiving']) ? 1 : 0;
}

function suggestions(entries, counts, limit, metadata) {
    return unique(entries.filter(function(app) {
        // Two deliberate launches may promote a utility; alphabetical order cannot.
        return visible(app, metadata, true) && (homePriority(app,metadata)>0 || (counts[app.id] || 0)>=2);
    }).slice().sort(function(a,b) {
        return (counts[b.id] || 0) - (counts[a.id] || 0) || homePriority(b,metadata)-homePriority(a,metadata) || a.name.localeCompare(b.name) || a.id.localeCompare(b.id);
    })).slice(0,limit);
}
