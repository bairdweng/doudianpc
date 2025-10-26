print("测试脚本运行中...")
print("当前时间:", __import__('datetime').datetime.now())

# 写入测试文件
with open('test_output.txt', 'w', encoding='utf-8') as f:
    f.write("测试输出文件创建成功")

print("测试完成，检查是否生成了test_output.txt文件")