console.log("🎬 开始Hook抖音HTTP请求和JSON响应");

// 主要Hook JSON解析方法
function hookJSONParsing() {
    console.log("🔧 设置JSON解析Hook...");

    // Hook NSJSONSerialization - 主要的JSON解析方法
    var NSJSONSerialization = ObjC.classes.NSJSONSerialization;
    if (NSJSONSerialization && NSJSONSerialization['+ JSONObjectWithData:options:error:']) {
        var jsonMethod = NSJSONSerialization['+ JSONObjectWithData:options:error:'];

        Interceptor.attach(jsonMethod.implementation, {
            onEnter: function (args) {
                try {
                    // args[2] = NSData
                    var data = new ObjC.Object(args[2]);
                    if (data && data.length() > 100) { // 只处理足够大的数据
                        var dataString = ObjC.classes.NSString.alloc().initWithData_encoding_(data, 4); // UTF-8
                        if (dataString) {
                            var jsonText = dataString.toString();

                            // 检查是否是抖音API的响应
                            if (jsonText.includes('aweme') || jsonText.includes('status_code') ||
                                jsonText.includes('douyin') || jsonText.includes('item_list')) {

                                console.log("\n" + "=".repeat(100));
                                console.log("✅ JSON响应捕获:");
                                console.log("📦 原始URL: https://mon.snssdk.com/monitor/collect/batch/");

                                try {
                                    // 尝试解析和格式化JSON
                                    var jsonObj = JSON.parse(jsonText);
                                    console.log("📊 格式化JSON:");
                                    var formattedJson = JSON.stringify(jsonObj, null, 2);

                                    // 截断过长的输出，但显示关键信息
                                    if (formattedJson.length > 1500) {
                                        console.log(formattedJson.substring(0, 1500) + "...\n(输出截断，完整响应约 " + formattedJson.length + " 字符)");
                                    } else {
                                        console.log(formattedJson);
                                    }

                                    // 提取关键信息
                                    if (jsonObj.status_code !== undefined) {
                                        console.log("🟢 Status Code: " + jsonObj.status_code);
                                    }
                                    if (jsonObj.aweme_list) {
                                        console.log("🎬 视频数量: " + jsonObj.aweme_list.length);
                                    }
                                    if (jsonObj.has_more !== undefined) {
                                        console.log("📄 还有更多: " + jsonObj.has_more);
                                    }

                                } catch (parseError) {
                                    console.log("📋 原始响应文本:");
                                    console.log(jsonText.substring(0, 800) + "...");
                                }

                                console.log("=".repeat(100));
                            }
                        }
                    }
                } catch (e) {
                    // 静默处理错误，避免被检测
                }
            }
        });
        console.log("✅ NSJSONSerialization Hook 已设置");
    }
}

// Hook 网络请求以获取完整URL
function hookNetworkRequests() {
    var NSURLSession = ObjC.classes.NSURLSession;
    if (NSURLSession && NSURLSession['- dataTaskWithRequest:completionHandler:']) {
        Interceptor.attach(NSURLSession['- dataTaskWithRequest:completionHandler:'].implementation, {
            onEnter: function (args) {
                try {
                    var request = new ObjC.Object(args[2]);
                    var url = request.URL().absoluteString().toString();

                    if (url && url.includes('snssdk.com') || url.includes('douyin.com')) {
                        console.log("\n🌐 HTTP请求:");
                        console.log("📍 URL: " + url.split('?')[0]); // 显示基础URL，避免参数过长
                        console.log("⚡️ Method: " + (request.HTTPMethod() ? request.HTTPMethod().toString() : 'GET'));
                    }
                } catch (e) {
                    // 忽略错误
                }
            }
        });
    }
}

// 延迟执行以避免被检测
setTimeout(function () {
    hookNetworkRequests();
    hookJSONParsing();
    console.log("🚀 所有Hook设置完成，开始监控抖音API...");
    console.log("💡 请在抖音中浏览视频、刷新推荐等操作来产生网络请求");
}, 2000);

// 保持脚本运行
setInterval(function () {
    // 空函数保持活跃
}, 30000);