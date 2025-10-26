#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import datetime
import re
import os

# 获取脚本所在目录的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_growth_score(growth_rate):
    """根据增长率字符串计算排序分数"""
    if not growth_rate or growth_rate == '':
        return 0
    
    try:
        # 尝试匹配数字部分
        match = re.search(r'([-+]?\d+\.?\d*)%', growth_rate)
        if not match:
            return 0
            
        rate_value = float(match.group(1))
        
        # 根据增长率范围返回不同的优先级分数
        if rate_value >= 100:
            return 3  # 最高优先级
        elif rate_value >= 50:
            return 2
        elif rate_value >= 20:
            return 1
        elif rate_value >= -15:
            return 0  # 零分，但仍可能出现在结果中
        else:
            return -1  # 不推荐显示的
    except Exception:
        return 0

def connect_to_database():
    """连接到SQLite数据库"""
    try:
        # 使用脚本目录下的数据库文件
        db_path = os.path.join(SCRIPT_DIR, 'product_data.db')
        
        # 检查数据库文件是否存在
        conn = None
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            print(f"✅ 成功连接到数据库: {db_path}")
        else:
            # 如果路径不存在，尝试创建
            conn = sqlite3.connect(db_path)
            print(f"⚠️  数据库文件不存在，尝试创建: {db_path}")
        
        # 调试：检查是否有包含非空二维码的产品
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM products WHERE qr_code IS NOT NULL AND qr_code != ''")
            qr_code_count = cursor.fetchone()[0]
            print(f"🔍 数据库中有 {qr_code_count} 条产品记录包含非空二维码")
        except sqlite3.Error as e:
            print(f"⚠️  查询二维码数据时出错: {e}")
        
        return conn
    except Exception as e:
        print(f"❌ 连接数据库失败: {e}")
        return None

def get_date_filter():
    """获取最近1天的日期过滤条件"""
    one_day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
    return one_day_ago.strftime('%Y-%m-%d %H:%M:%S')

def analyze_top_growth_products(return_data=False):
    """分析最近1天采集的数据，增长速度率最高的前5个产品"""
    conn = connect_to_database()
    if not conn:
        return None if return_data else None
    
    try:
        cursor = conn.cursor()
        date_filter = get_date_filter()
        
        # 查询最近1天的所有产品数据
        cursor.execute(
            "SELECT p.product_id, p.product_name, p.product_pic, p.pay_amount_growth_rate, s.shop_name, p.qr_code "
            "FROM products p LEFT JOIN shops s ON p.shop_id = s.shop_id "
            "WHERE p.captured_at >= ?",
            (date_filter,)
        )
        products = cursor.fetchall()
        
        if not products:
            print("❌ 未找到最近1天的产品数据")
            return None if return_data else None
        
        # 计算每个产品的增长率分数并排序
        products_with_score = []
        for product in products:
            product_id, product_name, product_pic, growth_rate, shop_name, qr_code = product
            score = get_growth_score(growth_rate)
            if score >= 0:  # 只考虑分数为0或以上的产品
                products_with_score.append({
                    'id': product_id,
                    'name': product_name,
                    'pic': product_pic,
                    'growth_rate': growth_rate,
                    'growth_score': score,
                    'shop_name': shop_name or "未知店铺",
                    'qr_code': qr_code if qr_code else ''
                })
        
        # 按照增长率分数和增长率值排序
        for x in products_with_score:
            # 添加安全的增长率值提取
            if x['growth_rate']:
                match = re.search(r'([-+]?\d+\.?\d*)%', x['growth_rate'])
                x['growth_value'] = float(match.group(1)) if match else 0
            else:
                x['growth_value'] = 0
        
        products_with_score.sort(key=lambda x: (x['growth_score'], x['growth_value']), reverse=True)
        
        # 根据产品ID去重，保留第一个出现的产品
        unique_products = []
        seen_ids = set()
        for product in products_with_score:
            if product['id'] not in seen_ids:
                seen_ids.add(product['id'])
                unique_products.append(product)
        
        # 取前5个不重复的产品
        top_products = unique_products[:5]
        
        # 如果需要返回数据，直接返回
        if return_data:
            return top_products
        
        # 打印结果
        print("\n📊 最近1天增长速度率最高的前5个产品：")
        print("=" * 120)
        print(f"{'序号':<4} {'店铺名称':<20} {'产品名称':<40} {'增长率':<10} {'图片URL':<30}")
        print("=" * 120)
        
        for i, product in enumerate(top_products, 1):
            # 显示产品信息
            print(f"{i:<4} {product['shop_name'][:20]:<22} {product['name'][:40]:<42} {product['growth_rate']:<12} {product['pic']}")
            print(f"{'    ':<4} {'产品ID':<20} {product['id']}")
            print()
        
    except Exception as e:
        print(f"❌ 分析产品数据时出错: {e}")
        return None if return_data else None
    finally:
        conn.close()

def analyze_top_growth_by_shop(return_data=False):
    """分析最近1天采集的数据，每个店铺增长率最高的前5个产品"""
    conn = connect_to_database()
    if not conn:
        return None if return_data else None
    
    try:
        cursor = conn.cursor()
        date_filter = get_date_filter()
        
        # 获取最近1天有数据的所有店铺
        cursor.execute(
            "SELECT DISTINCT s.shop_id, s.shop_name "
            "FROM shops s JOIN products p ON s.shop_id = p.shop_id "
            "WHERE p.captured_at >= ?",
            (date_filter,)
        )
        shops = cursor.fetchall()
        
        if not shops:
            print("❌ 未找到最近1天的店铺数据")
            return None if return_data else None
        
        # 准备返回数据结构
        shop_data = {}
        
        # 如果不需要返回数据，先打印标题
        if not return_data:
            print(f"\n📊 最近1天每个店铺增长率最高的前5个产品：")
            print("=" * 120)
        
        for shop_id, shop_name in shops:
            # 查询该店铺最近1天的产品数据
            cursor.execute(
                "SELECT product_id, product_name, product_pic, pay_amount_growth_rate, qr_code "
                "FROM products WHERE shop_id = ? AND captured_at >= ?",
                (shop_id, date_filter)
            )
            products = cursor.fetchall()
            
            if not products:
                if not return_data:
                    print(f"❌ 店铺 {shop_name} 未找到最近1天的产品数据")
                continue
            
            # 计算每个产品的增长率分数并排序
            products_with_score = []
            for product in products:
                product_id, product_name, product_pic, growth_rate, qr_code = product
                score = get_growth_score(growth_rate)
                if score >= 0:  # 只考虑分数为0或以上的产品
                    products_with_score.append({
                        'id': product_id,
                        'name': product_name,
                        'pic': product_pic,
                        'growth_rate': growth_rate,
                        'growth_score': score,
                        'qr_code': qr_code if qr_code else ''
                    })
            
            # 按照增长率分数和增长率值排序
            for x in products_with_score:
                # 添加安全的增长率值提取
                if x['growth_rate']:
                    match = re.search(r'([-+]?\d+\.?\d*)%', x['growth_rate'])
                    x['growth_value'] = float(match.group(1)) if match else 0
                else:
                    x['growth_value'] = 0
            
            products_with_score.sort(key=lambda x: (x['growth_score'], x['growth_value']), reverse=True)
            
            # 根据产品ID去重，保留第一个出现的产品
            unique_products = []
            seen_ids = set()
            for product in products_with_score:
                if product['id'] not in seen_ids:
                    seen_ids.add(product['id'])
                    unique_products.append(product)
            
            # 取前5个不重复的产品
            top_products = unique_products[:5]
            
            # 保存店铺数据
            shop_data[shop_id] = {
                'name': shop_name,
                'products': top_products
            }
            
            # 如果不需要返回数据，则打印该店铺的结果
            if not return_data:
                print(f"\n🏪 店铺: {shop_name} (ID: {shop_id})")
                print("-" * 120)
                print(f"{'序号':<4} {'产品名称':<40} {'增长率':<10} {'图片URL':<30}")
                print("-" * 120)
                
                for i, product in enumerate(top_products, 1):
                    # 显示产品信息
                    print(f"{i:<4} {product['name'][:40]:<42} {product['growth_rate']:<12} {product['pic']}")
                    print(f"{'    ':<4} {'产品ID':<20} {product['id']}")
                    print()
        
        # 如果需要返回数据，返回shop_data
        if return_data:
            return shop_data
        
    except Exception as e:
        print(f"❌ 分析店铺数据时出错: {e}")
        return None if return_data else None
    finally:
        conn.close()

def generate_markdown_report():
    """生成美观的Markdown格式分析报告"""
    try:
        # 获取当前时间作为报告生成时间
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        report_date = datetime.datetime.now().strftime('%Y%m%d')
        
        # 生成报告文件名，按日期生成唯一报告
        report_date = datetime.datetime.now().strftime('%Y%m%d')
        report_filename = os.path.join(SCRIPT_DIR, f'产品分析报告_{report_date}.txt')
        
        # 获取分析数据
        print("📊 正在生成Markdown报告...")
        print("🔄 正在获取平台增长率TOP5产品数据...")
        top5_products = analyze_top_growth_products(return_data=True)
        
        print("🔄 正在获取各店铺增长率TOP5产品数据...")
        shop_top_products = analyze_top_growth_by_shop(return_data=True)
        
        # 开始构建报告内容
        report_content = f"""# 产品数据分析报告

## 报告信息
- **生成时间**: {current_time}
- **分析范围**: 最近1天采集的数据
- **数据来源**: product_data.db

## 1. 平台增长率TOP5产品

| 排名 | 店铺名称 | 产品名称 | 增长率 | 产品ID |
|------|----------|----------|--------|--------|"""
        
        # 添加平台TOP5产品表格
        if top5_products:
            for i, product in enumerate(top5_products, 1):
                shop_name = product['shop_name'][:30]  # 限制长度
                product_name = product['name'][:50]    # 限制长度
                growth_rate = product['growth_rate'] if product['growth_rate'] else "-"
                report_content += f"\n| {i} | {shop_name} | {product_name} | {growth_rate} | {product['id']} |"
        else:
            report_content += "\n| - | 暂无数据 | 暂无数据 | - | - |"
        
        # 添加店铺产品分析部分
        report_content += """

## 2. 各店铺增长率TOP5产品

"""
        
        if shop_top_products:
            for shop_id, shop_info in shop_top_products.items():
                shop_name = shop_info['name']
                products = shop_info['products']
                
                report_content += f"\n### 2.1 {shop_name}\n\n"
                report_content += "| 排名 | 产品名称 | 增长率 | 产品ID |\n"
                report_content += "|------|----------|--------|--------|\n"
                
                if products:
                    for i, product in enumerate(products, 1):
                        product_name = product['name'][:50]  # 限制长度
                        growth_rate = product['growth_rate'] if product['growth_rate'] else "-"
                        report_content += f"| {i} | {product_name} | {growth_rate} | {product['id']} |\n"
                else:
                    report_content += "| - | 暂无数据 | - | - |\n"
        else:
            report_content += "暂无店铺数据\n"
        
        # 添加结论和建议部分
        report_content += """

## 3. 结论与建议

根据对最近1天产品数据的分析，我们得出以下结论和建议：

1. **热门产品趋势**：平台增长率较高的产品主要集中在[根据实际数据填写相关品类]。

2. **店铺竞争力**：从店铺维度看，[根据实际数据填写表现较好的店铺]在增长率方面表现突出。

3. **产品优化建议**：
   - 关注增长率较高的产品特点，借鉴其成功经验
   - 定期更新产品信息，保持数据的时效性
   - 结合市场趋势，适时调整产品策略

4. **数据质量评估**：本次分析基于[具体数据量]条产品数据，数据完整性良好。

---

**报告生成工具**: 产品数据分析助手 v1.0
**数据更新频率**: 每日自动更新
"""
        
        # 写入报告文件
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # 打印成功信息
        report_path = os.path.abspath(report_filename)
        print(f"✅ Markdown分析报告已成功生成！")
        print(f"📄 报告文件：{report_filename}")
        print(f"📍 文件位置：{report_path}")
        print(f"📊 报告内容：包含平台TOP5产品和各店铺TOP5产品")
        print(f"💡 提示：可以用Markdown查看器或文本编辑器打开报告")
        
    except Exception as e:
        print(f"❌ 生成Markdown报告失败: {e}")

def main():
    """主函数，调用HTML生成模块生成报告并打开"""
    print("📊 本工具将分析 product_data.db 数据库中的产品数据")
    print("===============================================")
    print("🔄 正在调用HTML生成模块...")
    
    # 导入并调用HTML生成模块
    try:
        from generate_html_report import generate_html_report
        report_filename = generate_html_report()
        
        if report_filename:
            # 获取最新生成的HTML报告文件
            import glob
            import os
            import webbrowser
            
            # 查找竞品分析脚本目录下的HTML报告文件，按修改时间排序
            report_files = glob.glob(os.path.join(SCRIPT_DIR, '竞品分析报告_*.html'))
            if report_files:
                # 按修改时间排序，获取最新的报告
                latest_report = max(report_files, key=os.path.getmtime)
                print(f"\n🔍 找到最新报告: {latest_report}")
                print(f"🌐 正在使用默认浏览器打开报告...")
                
                # 使用默认浏览器打开报告
                try:
                    webbrowser.open(f"file://{latest_report}")
                    print("✅ 报告已成功在浏览器中打开！")
                except Exception as e:
                    print(f"❌ 无法打开浏览器: {e}")
                    print(f"💡 请手动打开报告文件: {latest_report}")
            else:
                print("❌ 未找到生成的HTML报告文件")
        else:
            print("❌ HTML报告生成失败")
    except ImportError:
        print("❌ 无法导入generate_html_report模块")
    except Exception as e:
        print(f"❌ 运行时错误: {e}")
    
    print("\n✅ 操作完成！")

if __name__ == "__main__":
    main()