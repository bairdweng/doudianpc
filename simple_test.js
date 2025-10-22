console.log('✅ 脚本注入成功!');
console.log('进程: ' + Process.name);
console.log('PID: ' + Process.id);
console.log('架构: ' + Process.arch);

// 测试ObjC
if (ObjC.available) {
    console.log('✅ Objective-C 可用');
    var UIApplication = ObjC.classes.UIApplication;
    if (UIApplication) {
        console.log('✅ UIApplication 类找到');
    }
} else {
    console.log('❌ Objective-C 不可用');
}