console.log("📱 已安装的应用列表：");

var installedApps = ObjC.classes.NSWorkspace ? ObjC.classes.NSWorkspace.sharedWorkspace().runningApplications() : null;
if (installedApps) {
    for (var i = 0; i < installedApps.count(); i++) {
        var app = installedApps.objectAtIndex_(i);
        console.log("   " + app.localizedName());
    }
} else {
    console.log("无法获取应用列表，但Frida正在运行！");
}