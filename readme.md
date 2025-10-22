streamlit run app.py

代理启动
mitmweb --listen-port 8082


打开安卓模拟器
~/Library/Android/sdk/emulator
./emulator -avd Medium_Phone_API_36.0 -writable-system -no-snapshot-load


~/Library/Android/sdk/emulator/emulator \
 -avd Medium_Phone_API_36.0 \
 -gpu swiftshader_indirect \
 -memory 4096 \
 -no-snapshot-load \
 -dns-server 8.8.8.8,8.8.4.4 \
 -writable-system


 scp frida-server-17.2.17-android-arm64 root@192.168.3.34:/usr/bin/



第二步：安装或重新安装 Frida
根据你的越狱工具（Dopamine），需要正确安装Frida：

方法一：通过Sileo/Zebra安装

在iOS设备上打开Sileo或Zebra

添加源：https://build.frida.re

搜索并安装 Frida

方法二：通过终端手动安装

bash
# 更新软件源
apt update

# 搜索frida包
apt search frida

# 安装frida
apt install re.frida.server

# 打开列表
 frida-ps -Uai