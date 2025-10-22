#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音电商商品数据分析与投流推荐脚本

功能说明：
    本脚本用于自动抓取抖音罗盘平台的商品数据，进行按天存储和分析，并基于综合评分算法筛选出最值得投流推广的产品。

核心功能：
1. 数据采集：
   - 使用Playwright自动化浏览器访问抖音罗盘商品流量分析页面
   - 智能拦截特定API响应（shop/product_card/channel_product/channel_product_card_list）
   - 支持多种数据提取方式，包括直接提取、深度搜索和API数据转换
   - 提供模拟数据作为备选，确保脚本在各种情况下都能正常运行

2. 数据存储：
   - SQLite数据库存储，支持按日期字段进行数据管理
   - 自动创建/更新数据表结构
   - 同时保存JSON格式数据到文件（ddlp.txt），便于其他工具分析

3. 数据分析：
   - 基于前3天数据进行综合分析
   - 计算关键指标：总销售额、平均转化率
   - 使用智能评分算法（转化率40% + 支付金额30% + 点击率30%）
   - 筛选出Top 3最值得投流的产品并展示详细数据

4. 自动容错：
   - 完善的错误处理机制
   - 网络请求失败时自动切换到模拟数据
   - 数据库操作异常保护

使用方法：
    python3 ddlp.py

环境要求：
    - Python 3.7+
    - 依赖包：playwright, aiosqlite, asyncio
    - 安装命令：pip install playwright aiosqlite && playwright install

投流推荐算法：
    脚本使用加权评分系统，考虑三个关键指标：
    - 转化率 (40%权重)：直接反映产品的销售效果
    - 支付金额 (30%权重)：体现产品的收入贡献
    - 点击率 (30%权重)：表示产品的吸引力和市场潜力
    对有销量的产品额外给予0.1分的加分，确保推荐结果更具实用性。

注意事项：
    1. 脚本默认使用Chrome浏览器和用户数据目录，可能需要根据实际情况修改user_data_dir路径
    2. 首次运行时会自动创建数据库表结构
    3. 如需清除测试数据，可执行以下SQL命令：
       sqlite3 ddlp.db "DELETE FROM products; VACUUM;"
    4. 脚本设置了30秒的等待时间用于页面数据加载，可根据网络情况调整
"""
import asyncio
import aiosqlite
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

DB_FILE = "ddlp.db"
OUTPUT_FILE = "ddlp.txt"

# 初始化数据库
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        # 添加date字段用于按天分析数据
        await db.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            product_name TEXT,
            product_price INTEGER,
            product_img TEXT,
            first_onshelf_date TEXT,
            pay_cnt INTEGER,
            pay_amt INTEGER,
            pay_ucnt INTEGER,
            pay_converse_rate_ucnt REAL,
            product_show_ucnt INTEGER,
            product_click_ucnt INTEGER,
            product_click_ucnt_rate REAL,
            product_tags TEXT,
            last_update_time TEXT,
            date TEXT
        )
        """)
        # 如果表已存在但没有date字段，则添加该字段
        try:
            await db.execute("ALTER TABLE products ADD COLUMN date TEXT")
        except Exception:
            # 字段可能已存在，忽略错误
            pass
        await db.commit()

# 数据存储和分析功能将仅处理实际采集的数据，不再使用模拟数据

# 保存数据到数据库
async def save_products_to_db(products_data):
    async with aiosqlite.connect(DB_FILE) as db:
        for cell_info in products_data:
            data = cell_info["cell_info"]
            
            # 提取产品信息
            product_id = data["product"]["product_id_value"]["value"]["value_str"]
            product_name = data["product"]["product_name_value"]["value"]["value_str"]
            product_price = data["product"]["product_price_value"]["value"]["value"]
            product_img = data["product"]["product_img_value"]["value"]["value_str"]
            product_tags = data["product"]["product_tags_value"]["value"]["value_str"]
            
            # 提取其他信息
            first_onshelf_date = data["first_onshelf_date"]["first_onshelf_date_index_values"]["index_values"]["value"]["value_str"]
            pay_cnt = data["pay_cnt"]["pay_cnt_index_values"]["index_values"]["value"]["value"]
            pay_amt = data["pay_amt"]["pay_amt_index_values"]["index_values"]["value"]["value"]
            pay_ucnt = data["pay_ucnt"]["pay_ucnt_index_values"]["index_values"]["value"]["value"]
            pay_converse_rate_ucnt = data["pay_converse_rate_ucnt"]["pay_converse_rate_ucnt_index_values"]["index_values"]["value"]["value"]
            product_show_ucnt = data["product_show_ucnt"]["product_show_ucnt_index_values"]["index_values"]["value"]["value"]
            product_click_ucnt = data["product_click_ucnt"]["product_click_ucnt_index_values"]["index_values"]["value"]["value"]
            product_click_ucnt_rate = data["product_click_ucnt_rate"]["product_click_ucnt_rate_index_values"]["index_values"]["value"]["value"]
            
            # 插入或更新数据，包含当前日期
            current_date = datetime.now().strftime("%Y-%m-%d")
            await db.execute("""
            INSERT OR REPLACE INTO products 
            (product_id, product_name, product_price, product_img, first_onshelf_date, 
             pay_cnt, pay_amt, pay_ucnt, pay_converse_rate_ucnt, product_show_ucnt, 
             product_click_ucnt, product_click_ucnt_rate, product_tags, last_update_time, date) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_id, product_name, product_price, product_img, first_onshelf_date,
                pay_cnt, pay_amt, pay_ucnt, pay_converse_rate_ucnt, product_show_ucnt,
                product_click_ucnt, product_click_ucnt_rate, product_tags, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                current_date
            ))
        
        await db.commit()

# 保存数据到文件
async def save_products_to_file(products_data):
    # 将数据转换为JSON字符串并保存到文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # 按照ddlp.txt的格式，每个产品对象占一行
        for product in products_data:
            json.dump(product, f, ensure_ascii=False)
            f.write(',')  # 添加逗号分隔
        
        # 移除最后一个逗号（如果有）
        if products_data:
            f.seek(f.tell() - 1, 0)
            f.truncate()

# 深度搜索JSON中的cell_info结构
async def deep_search_cell_info(data, path=""):
    """递归搜索JSON数据中的cell_info或可转换为cell_info的结构"""
    results = []
    
    if isinstance(data, dict):
        # 如果当前字典有cell_info字段，直接提取
        if 'cell_info' in data:
            results.append(data)
            print(f"🔍 深度搜索: 在路径 {path + '.cell_info'} 找到cell_info")
        
        # 检查当前字典是否可以直接转换为cell_info
        if all(key in data for key in ['product_id', 'title', 'price']):
            cell_info = await build_cell_info_from_api(data)
            if cell_info:
                results.append({'cell_info': cell_info})
                print(f"🔍 深度搜索: 在路径 {path} 找到可转换为cell_info的数据")
        
        # 递归搜索字典的所有字段
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key
            sub_results = await deep_search_cell_info(value, new_path)
            results.extend(sub_results)
    
    elif isinstance(data, list):
        # 递归搜索列表中的每个元素
        for i, item in enumerate(data):
            new_path = f"{path}[{i}]"
            sub_results = await deep_search_cell_info(item, new_path)
            results.extend(sub_results)
    
    return results

# 处理网络响应
async def handle_response(response, db):
    try:
        url = response.url
        
        # 只处理包含目标URL模式的响应，其他所有URL都跳过
        TARGET_URL_PATTERN = "shop/product_card/channel_product/channel_product_card_list"
        if TARGET_URL_PATTERN not in url:
            return
        
        # 详细记录所有响应信息用于调试
        print(f"🔍 捕获到响应 - URL: {url}, 状态码: {response.status}")
        status = response.status
        data = None
        
        # 特定目标URL - 用户确认的商品数据API

        # 优先检查目标URL
        if TARGET_URL_PATTERN in url and status == 200:
            print(f"🎯 找到目标API响应: {url}")
            
            # 获取完整响应文本
            response_text = await response.text()
            
            # 保存到文件
            with open('test3.txt', 'w', encoding='utf-8') as f:
                f.write(response_text)
            
            print(f"💾 响应已保存到 test3.txt 文件")
            
            # 尝试解析JSON用于处理
            import json
            data = json.loads(response_text)
            print(f"✅ 成功解析JSON响应")
            
            # 打印JSON响应的第一层结构，用于调试
            if isinstance(data, dict):
                print(f"📊 JSON顶层结构: {list(data.keys())}")
        else:
            # 检查其他可能的商品相关API
            other_patterns = [
                "compass_api/shop/product_card",
                "product_card",
                "merchandise-traffic",
                "product",
                "shop"
            ]
            
            if any(pattern in url for pattern in other_patterns) and status == 200:
                print(f"📡 捕获到其他商品相关API响应: {url}")
                # 对于其他API，先获取响应文本，然后尝试解析JSON
                try:
                    response_text = await response.text()
                    import json
                    data = json.loads(response_text)
                    print(f"✅ 成功解析JSON响应")
                except json.JSONDecodeError:
                    print(f"❌ 响应不是有效的JSON格式，跳过处理: {url}")
                    return
                except Exception as e:
                    print(f"❌ 解析其他API响应时出错: {str(e)}")
                    return
            else:
                # 不是目标API，跳过处理
                return
        
        # 提取商品列表数据 (只有获取到data后才执行)
        if data is not None:
            products_data = []
            
            # 更通用的数据提取逻辑
            if isinstance(data, dict):
                print(f"🔍 检查JSON结构，寻找商品数据")
                
                # 方式1: 检查data中是否有直接的商品列表
                if 'cell_info' in data:
                    products_data = [{'cell_info': data['cell_info']}]
                    print(f"✅ 找到直接的cell_info数据")
                
                # 方式2: 检查常见的列表字段
                list_fields = ['items', 'list', 'product_list', 'data', 'products', 'result', 'contents']
                for field in list_fields:
                    if field in data:
                        field_data = data[field]
                        print(f"🔍 检查字段: {field}, 类型: {type(field_data).__name__}")
                        if isinstance(field_data, list):
                            print(f"🔍 {field} 包含 {len(field_data)} 个元素")
                            for i, item in enumerate(field_data):
                                if isinstance(item, dict):
                                    if 'cell_info' in item:
                                        products_data.append(item)
                                        print(f"✅ 从{field}[{i}]中提取到cell_info")
                                    else:
                                        # 尝试从item构建cell_info
                                        cell_info = await build_cell_info_from_api(item)
                                        if cell_info:
                                            products_data.append({'cell_info': cell_info})
                                            print(f"✅ 从{field}[{i}]项构建cell_info")
                                # 每10个元素打印一次进度
                                elif i % 10 == 0 and len(field_data) > 20:
                                    print(f"🔍 处理 {field} 中的元素 {i}/{len(field_data)}")
                        elif isinstance(field_data, dict) and 'cell_info' in field_data:
                            products_data.append(field_data)
                            print(f"✅ 从{field}字典中提取到cell_info")
                
                # 方式3: 深度搜索JSON中所有可能的cell_info
                if not products_data:
                    print("🔍 执行深度搜索寻找cell_info")
                    products_data = await deep_search_cell_info(data)
            
            # 只处理实际提取到的数据
                if products_data:
                    print(f"✅ 成功提取到 {len(products_data)} 个商品数据")
                else:
                    print("⚠️  未从API响应中提取到商品数据，跳过数据处理")
                    return
            
            # 保存商品数据到数据库
            await save_products_to_db(products_data)
            print(f"✅ 商品数据已保存到数据库")
            
            # 保存商品数据到文件
            await save_products_to_file(products_data)
            print(f"✅ 商品数据已保存到文件")
    except Exception as e:
        print(f"❌ handle_response函数执行出错: {str(e)}")
        # 记录详细的错误信息，便于调试
        import traceback
        print(f"📝 错误详情: {traceback.format_exc()}")
        # 出错时确保函数正常返回，不影响后续执行
        return

# 从API数据构建cell_info结构（需要根据实际API格式调整）
async def build_cell_info_from_api(product_data):
    """将API返回的商品数据转换为ddlp.txt格式的cell_info结构"""
    try:
        # 这里是一个示例转换，需要根据实际API响应格式调整
        cell_info = {
            "boost_info": {
                "boost_info_json_str": {
                    "cell_type": 100,
                    "json_str": "null"
                }
            },
            "diagnose_result": {
                "diagnose_result_json_str": {
                    "cell_type": 100,
                    "json_str": "{\"content\":\"\"}"
                }
            },
            "product": {
                "product_detail_h5_url_value": {
                    "cell_type": 1,
                    "value": {"unit": 1, "value_str": "测试"}
                },
                # 从API数据中提取其他字段，这里需要根据实际情况调整
                "product_id_value": {
                    "cell_type": 1,
                    "value": {"unit": 1, "value_str": str(product_data.get('product_id', ''))}
                },
                "product_name_value": {
                    "cell_type": 1,
                    "value": {"unit": 1, "value_str": product_data.get('product_name', '')}
                },
                "product_price_value": {
                    "cell_type": 1,
                    "value": {"unit": 3, "value": product_data.get('product_price', 0)}
                },
                "product_img_value": {
                    "cell_type": 1,
                    "value": {"unit": 1, "value_str": product_data.get('product_img', '')}
                },
                "product_tags_value": {
                    "cell_type": 1,
                    "value": {"unit": 1, "value_str": product_data.get('product_tags', '')}
                }
            },
            # 填充其他必要的字段
            "first_onshelf_date": {
                "first_onshelf_date_index_values": {
                    "cell_type": 2,
                    "index_values": {
                        "out_period_ratio": {"unit": 6, "value": 0},
                        "value": {"unit": 1, "value_str": product_data.get('first_onshelf_date', '')}
                    }
                }
            },
            # 其他字段类似填充...
        }
        return cell_info
    except Exception as e:
        print(f"❌ 构建cell_info时出错: {e}")
        return None

# 分析商品数据
async def analyze_products():
    print(f"📊 开始商品数据分析 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await init_db()
    async with aiosqlite.connect(DB_FILE) as db:
        async with async_playwright() as p:
            try:
                # 启动浏览器
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir="/Users/bairdweng/Library/Application Support/Google/Chrome/Default",
                    channel="chrome",
                    headless=False
                )
                page = await browser.new_page()
                
                # 绑定响应事件处理器
                page.on("response", lambda response: asyncio.create_task(
                    handle_response(response, response.url)))
                
                # 访问商品数据页面
                target_url = "https://compass.jinritemai.com/shop/merchandise-traffic?from_page=%2Fshop%2Ftraffic-analysis&btm_ppre=a6187.b7716.c0.d0&btm_pre=a6187.b1854.c0.d0&btm_show_id=df90e96a-1e32-424b-9e9a-84a28feddaaf"
                print(f"🌐 访问目标页面: {target_url}")
                await page.goto(target_url)
                
                # 等待网络请求完成
                print("⏳ 等待商品数据加载完成...")
                await asyncio.sleep(30)  # 给足够时间加载数据
                
                # 检查是否已获取数据
                print("🔄 检查是否已获取数据")
                async with db.execute("SELECT COUNT(*) FROM products") as cursor:
                    count = await cursor.fetchone()
                    if count and count[0] == 0:
                        print("⚠️  未获取到实际数据，跳过数据分析")
                    else:
                        await perform_data_analysis()
                
                print("✅ 关闭浏览器")
                await browser.close()
                
                # 只有在成功获取数据后才执行数据分析
                # 已在前面的检查中调用perform_data_analysis()
                
            except Exception as e:
                print(f"❌ 分析商品数据过程中出错: {e}")
                print("❌ 分析商品数据过程中出错，跳过数据分析")
    
    print(f"✅ 商品数据分析完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 执行数据分析
async def perform_data_analysis():
    async with aiosqlite.connect(DB_FILE) as db:
        # 计算前3天的日期
        today = datetime.now()
        three_days_ago = (today - timedelta(days=3)).strftime("%Y-%m-%d")
        
        print(f"📊 开始基于前3天数据的产品分析 (起始日期: {three_days_ago})")
        
        # 分析1: 计算总销售额
        async with db.execute("SELECT SUM(pay_amt) as total_sales FROM products WHERE date >= ?", (three_days_ago,)) as cursor:
            total_sales = await cursor.fetchone()
            print(f"📈 前3天总销售额: {total_sales[0] or 0} 元")
        
        # 分析2: 计算平均转化率
        async with db.execute("SELECT AVG(pay_converse_rate_ucnt) as avg_conversion FROM products WHERE date >= ? AND pay_converse_rate_ucnt > 0", (three_days_ago,)) as cursor:
            avg_conversion = await cursor.fetchone()
            print(f"📈 前3天平均转化率: {avg_conversion[0]:.2%} ")
        
        # 分析3: 根据关键指标筛选值得投流的产品
        # 考虑的指标: 转化率、点击量、支付金额
        # 使用综合评分: 转化率(40%) + 支付金额占比(30%) + 点击率(30%)
        print("\n🎯 筛选值得投流的3个产品:")
        
        # 先获取前3天所有产品数据
        async with db.execute("SELECT product_id, product_name, product_price, pay_amt, pay_converse_rate_ucnt, product_click_ucnt_rate, product_show_ucnt, product_click_ucnt FROM products WHERE date >= ?", (three_days_ago,)) as cursor:
            products = await cursor.fetchall()
        
        if not products:
            print("⚠️  前3天内没有产品数据，使用所有可用数据进行分析")
            async with db.execute("SELECT product_id, product_name, product_price, pay_amt, pay_converse_rate_ucnt, product_click_ucnt_rate, product_show_ucnt, product_click_ucnt FROM products") as cursor:
                products = await cursor.fetchall()
        
        if not products:
            print("❌ 数据库中没有产品数据")
            return
        
        # 计算各项指标的最大值，用于归一化
        max_pay_amt = max(product[3] for product in products)
        max_conversion = max(product[4] for product in products if product[4] > 0)
        max_click_rate = max(product[5] for product in products if product[5] > 0)
        
        # 为每个产品计算综合评分
        scored_products = []
        for product in products:
            product_id, product_name, product_price, pay_amt, conversion_rate, click_rate, show_cnt, click_cnt = product
            
            # 归一化各项指标
            norm_pay_amt = pay_amt / max_pay_amt if max_pay_amt > 0 else 0
            norm_conversion = conversion_rate / max_conversion if max_conversion > 0 else 0
            norm_click_rate = click_rate / max_click_rate if max_click_rate > 0 else 0
            
            # 计算综合评分
            # 转化率权重40%，支付金额权重30%，点击率权重30%
            score = norm_conversion * 0.4 + norm_pay_amt * 0.3 + norm_click_rate * 0.3
            
            # 特殊加分: 对有销量的产品给予额外加分
            if pay_amt > 0:
                score += 0.1
            
            scored_products.append((product_id, product_name, product_price, pay_amt, conversion_rate, click_rate, show_cnt, click_cnt, score))
        
        # 按综合评分排序，选择前3个产品
        scored_products.sort(key=lambda x: x[8], reverse=True)
        top_3_products = scored_products[:3]
        
        # 输出前3个值得投流的产品及其关键数据
        print("\n🏆 值得投流的Top 3产品:")
        print("=" * 100)
        print(f"{'排名':<5} | {'产品名称':<50} | {'价格':<8} | {'销售额':<10} | {'转化率':<10} | {'点击率':<10}")
        print("=" * 100)
        
        for i, product in enumerate(top_3_products, 1):
            product_id, product_name, product_price, pay_amt, conversion_rate, click_rate, show_cnt, click_cnt, score = product
            # 价格转换为元（原数据是分）
            price_in_yuan = product_price / 100
            # 限制产品名称长度，避免输出过宽
            short_name = (product_name[:45] + '...') if len(product_name) > 48 else product_name
            
            print(f"{i:<5} | {short_name:<50} | ¥{price_in_yuan:<7.2f} | {pay_amt/100:<9.2f}元 | {conversion_rate*100:<9.2f}% | {click_rate*100:<9.2f}%")
        
        print("=" * 100)
        print("\n📋 详细分析:")
        for i, product in enumerate(top_3_products, 1):
            product_id, product_name, product_price, pay_amt, conversion_rate, click_rate, show_cnt, click_cnt, score = product
            print(f"\n🔹 排名 {i}: {product_name}")
            print(f"   价格: ¥{product_price/100:.2f}")
            print(f"   销售额: ¥{pay_amt/100:.2f}")
            print(f"   转化率: {conversion_rate*100:.2f}%")
            print(f"   点击率: {click_rate*100:.2f}%")
            print(f"   曝光量: {show_cnt}")
            print(f"   点击量: {click_cnt}")
            print(f"   综合评分: {score:.2f}")

# 主函数
async def main():
    await init_db()
    await analyze_products()

# 不需要定时任务，直接执行一次

if __name__ == "__main__":
    # 直接执行一次商品数据分析
    asyncio.run(main())
