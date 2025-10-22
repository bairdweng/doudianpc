console.log("🎯 Frida脚本成功注入到Safari！");
console.log("📱 进程ID: " + Process.id);
console.log("📦 进程架构: " + Process.arch);

// 简单的函数Hook演示 - 拦截NSString的创建
var NSString = ObjC.classes.NSString;

// Hook stringWithFormat: 方法
NSString['+ stringWithFormat:'].implementation = function () {
    console.log("📝 NSString.stringWithFormat() 被调用了！");

    // 调用原始方法
    var result = this['+ stringWithFormat:'].apply(this, arguments);

    // 打印结果
    console.log("✅ 创建字符串: " + result.toString());

    return result;
};

console.log("🚀 等待Safari操作...");