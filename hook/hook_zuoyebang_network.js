console.log("🌐 开始捕获所有网络请求");
console.log("📱 进程ID: " + Process.id);

// 1. Hook NSURLSession - 最常用的网络API
var NSURLSession = ObjC.classes.NSURLSession;

if (NSURLSession && NSURLSession['- dataTaskWithRequest:completionHandler:']) {
    Interceptor.attach(NSURLSession['- dataTaskWithRequest:completionHandler:'].implementation, {
        onEnter: function (args) {
            try {
                var request = new ObjC.Object(args[2]);
                var url = request.URL().absoluteString().toString();

                if (url && url.length > 10) { // 过滤掉无效URL
                    console.log("\n" + "=".repeat(50));
                    console.log("🎯 NSURLSession 请求:");
                    console.log("📍 URL: " + url);

                    var method = request.HTTPMethod();
                    if (method) console.log("⚡️ Method: " + method.toString());

                    // 打印所有Headers
                    var headers = request.allHTTPHeaderFields();
                    if (headers) {
                        console.log("📋 Headers:");
                        var headerDict = ObjC.Object(headers);
                        var keys = headerDict.allKeys();
                        for (var i = 0; i < keys.count(); i++) {
                            var key = keys.objectAtIndex_(i).toString();
                            var value = headerDict.objectForKey_(keys.objectAtIndex_(i)).toString();
                            console.log("   " + key + ": " + value);
                        }
                    }
                }
            } catch (e) {
                console.log("❌ NSURLSession错误: " + e.message);
            }
        }
    });
    console.log("✅ NSURLSession Hook 已设置");
}

// 2. Hook NSURLConnection - 较老的网络API
var NSURLConnection = ObjC.classes.NSURLConnection;
if (NSURLConnection && NSURLConnection['- initWithRequest:delegate:']) {
    Interceptor.attach(NSURLConnection['- initWithRequest:delegate:'].implementation, {
        onEnter: function (args) {
            try {
                var request = new ObjC.Object(args[2]);
                var url = request.URL().absoluteString().toString();
                if (url && url.length > 10) {
                    console.log("\n🔗 NSURLConnection 请求: " + url);
                }
            } catch (e) {
                // 忽略错误
            }
        }
    });
    console.log("✅ NSURLConnection Hook 已设置");
}

// 3. Hook CFNetwork - 底层网络库
var symbols = Module.enumerateImports('CFNetwork');
var httpSymbols = symbols.filter(s => s.name.includes('HTTP'));
httpSymbols.forEach(symbol => {
    console.log("🔍 CFNetwork 符号: " + symbol.name);
});

// 4. Hook Socket连接 - 底层网络
var connectFunc = Module.findExportByName(null, 'connect');
if (connectFunc) {
    Interceptor.attach(connectFunc, {
        onEnter: function (args) {
            // args[1] = sockaddr结构体
            try {
                var family = Memory.readU8(args[1].add(1));
                if (family === 2) { // AF_INET IPv4
                    var port = Memory.readU16(args[1].add(2));
                    var addr = Memory.readU32(args[1].add(4));
                    var ip = (addr & 0xff) + '.' + ((addr >> 8) & 0xff) + '.' +
                        ((addr >> 16) & 0xff) + '.' + ((addr >> 24) & 0xff);
                    console.log("🔌 Socket连接: " + ip + ":" + port);
                }
            } catch (e) {
                // 忽略错误
            }
        }
    });
    console.log("✅ Socket连接 Hook 已设置");
}

// 5. Hook DNS解析
var getaddrinfo = Module.findExportByName(null, 'getaddrinfo');
if (getaddrinfo) {
    Interceptor.attach(getaddrinfo, {
        onEnter: function (args) {
            var hostname = Memory.readCString(args[0]);
            if (hostname && hostname.length > 3) {
                console.log("📡 DNS解析: " + hostname);
            }
        }
    });
    console.log("✅ DNS解析 Hook 已设置");
}

console.log("✅ 所有网络Hook已设置完成！");
console.log("🚀 开始在作业帮中操作以产生网络流量...");

// 保持脚本运行
setInterval(function () {
    // 空函数保持活跃
}, 30000);