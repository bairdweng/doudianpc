#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import datetime
import webbrowser
import glob

# 获取脚本所在目录的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def generate_html_report():
    """生成美观的HTML格式分析报告"""
    # 导入数据分析模块
    import sys
    import os
    # 将当前脚本目录添加到Python路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.append(script_dir)
    
    # 导入数据分析函数
    from analyze_data import analyze_top_growth_products, analyze_top_growth_by_shop, SCRIPT_DIR
    
    # 获取分析数据
    print("📊 正在生成HTML报告...")
    print("🔄 正在获取平台增长率TOP5产品数据...")
    top5_products = analyze_top_growth_products(return_data=True)
    
    print("🔄 正在获取各店铺增长率TOP5产品数据...")
    shop_top_products = analyze_top_growth_by_shop(return_data=True)
    
    try:
        # 获取当前时间作为报告生成时间
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        report_date = datetime.datetime.now().strftime('%Y%m%d')
        
        # 生成报告文件名，按日期生成唯一报告
        report_filename = os.path.join(SCRIPT_DIR, f'竞品分析报告_{report_date}.html')
        
        print(f"📊 正在生成HTML报告: {report_filename}")
        
        # 构建HTML内容
        html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>产品数据分析报告 - ''' + report_date + '''</title>
    <style>
        /* 商业主题CSS样式 */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: white;
            padding: 40px 0;
            text-align: center;
            margin-bottom: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .section {
            background: white;
            padding: 30px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        
        .section h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
            font-size: 1.8em;
        }
        
        .section h3 {
            color: #34495e;
            margin: 25px 0 15px 0;
            font-size: 1.4em;
        }
        
        .info-box {
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
        
        .info-item {
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
        }
        
        .info-label {
            font-weight: 600;
            color: #2c3e50;
            min-width: 120px;
        }
        
        .table-container {{
            overflow-x: auto;
            margin: 20px 0;
        }}
        
        img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            border: 1px solid #ddd;
        }}
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95em;
        }
        
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        th {
            background-color: #3498db;
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        tr:hover {
            background-color: #f1f1f1;
        }
        
        .conclusion {
            background-color: #e8f4f8;
            border-left: 4px solid #3498db;
            padding: 20px;
            margin: 20px 0;
            border-radius: 0 6px 6px 0;
        }
        
        .conclusion h4 {
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .conclusion ul {
            padding-left: 20px;
        }
        
        .conclusion li {
            margin-bottom: 8px;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 30px;
        }
        
        .highlight {
            background-color: #fff3cd;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
        }
        
        /* 响应式设计 */
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .section {
                padding: 20px;
            }
            
            .info-item {
                flex-direction: column;
            }
            
            .info-label {
                margin-bottom: 4px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>产品数据分析报告</h1>
            <p>基于最近1天采集的数据生成</p>
        </div>
        
        <div class="section">
            <h2>报告信息</h2>
            <div class="info-box">
                <div class="info-item">
                    <span class="info-label">生成时间:</span>
                    <span>'''
        
        html_content += current_time
        html_content += '''</span>
                </div>
                <div class="info-item">
                    <span class="info-label">分析范围:</span>
                    <span>最近1天采集的数据</span>
                </div>
                <div class="info-item">
                    <span class="info-label">数据来源:</span>
                    <span>product_data.db</span>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>1. 平台增长率TOP5产品</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>店铺名称</th>
                            <th>产品名称</th>
                            <th>增长率</th>
                            <th>产品图片</th>
                            <th>二维码</th>
                            <th>产品ID</th>
                        </tr>
                    </thead>
                    <tbody>'''
        
        # 添加平台TOP5产品表格内容
        if top5_products:
            for i, product in enumerate(top5_products, 1):
                shop_name = product['shop_name'][:30]  # 限制长度
                product_name = product['name'][:50]    # 限制长度
                growth_rate = product['growth_rate'] if product['growth_rate'] else "-"
                
                # 处理图片显示
                pic_html = '<img src="' + product['pic'] + '" width="100" height="100">' if product['pic'] else '-'
                qr_html = '<img src="' + product['qr_code'] + '" width="100" height="100">' if product['qr_code'] else '-'
                
                # 拼接HTML
                html_content += "\n                        <tr>"
                html_content += "\n                            <td>" + str(i) + "</td>"
                html_content += "\n                            <td>" + shop_name + "</td>"
                html_content += "\n                            <td>" + product_name + "</td>"
                html_content += "\n                            <td>" + growth_rate + "</td>"
                html_content += "\n                            <td>" + pic_html + "</td>"
                html_content += "\n                            <td>" + qr_html + "</td>"
                html_content += "\n                            <td>" + product['id'] + "</td>"
                html_content += "\n                        </tr>"
        else:
            html_content += '''
                        <tr>
                            <td>-</td>
                            <td>暂无数据</td>
                            <td>暂无数据</td>
                            <td>-</td>
                            <td>-</td>
                            <td>-</td>
                            <td>-</td>
                        </tr>'''
        
        html_content += '''
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="section">
            <h2>2. 各店铺增长率TOP5产品</h2>'''
        
        # 添加店铺产品分析部分
        if shop_top_products:
            for shop_id, shop_info in shop_top_products.items():
                shop_name = shop_info['name']
                products = shop_info['products']
                
                html_content += '''
            <h3>2.1 ''' + shop_name + '''</h3>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                                <th>排名</th>
                                <th>产品名称</th>
                                <th>增长率</th>
                                <th>产品图片</th>
                                <th>二维码</th>
                                <th>产品ID</th>
                            </tr>
                    </thead>
                    <tbody>'''
                
                if products:
                    for i, product in enumerate(products, 1):
                        product_name = product['name'][:50]  # 限制长度
                        growth_rate = product['growth_rate'] if product['growth_rate'] else "-"
                        
                        # 处理图片显示
                        pic_html = '<img src="' + product['pic'] + '" width="100" height="100">' if product['pic'] else '-'
                        qr_html = '<img src="' + product['qr_code'] + '" width="100" height="100">' if product['qr_code'] else '-'
                        
                        # 拼接HTML
                        html_content += "\n                        <tr>"
                        html_content += "\n                            <td>" + str(i) + "</td>"
                        html_content += "\n                            <td>" + product_name + "</td>"
                        html_content += "\n                            <td>" + growth_rate + "</td>"
                        html_content += "\n                            <td>" + pic_html + "</td>"
                        html_content += "\n                            <td>" + qr_html + "</td>"
                        html_content += "\n                            <td>" + product['id'] + "</td>"
                        html_content += "\n                        </tr>"
                else:
                    html_content += '''
                        <tr>
                            <td>-</td>
                            <td>暂无数据</td>
                            <td>-</td>
                            <td>-</td>
                            <td>-</td>
                            <td>-</td>
                        </tr>'''
                
                html_content += '''
                    </tbody>
                </table>
            </div>'''
        else:
            html_content += '''
            <p>暂无店铺数据</p>'''
        
        # 添加结论和建议部分
        html_content += '''
        </div>
        
        <div class="section">
            <h2>3. 结论与建议</h2>
            <div class="conclusion">
                <p>根据对最近1天产品数据的分析，我们得出以下结论和建议：</p>
                
                <h4>热门产品趋势</h4>
                <p>平台增长率较高的产品主要集中在<span class="highlight">[根据实际数据填写相关品类]</span>。</p>
                
                <h4>店铺竞争力</h4>
                <p>从店铺维度看，<span class="highlight">[根据实际数据填写表现较好的店铺]</span>在增长率方面表现突出。</p>
                
                <h4>产品优化建议</h4>
                <ul>
                    <li>关注增长率较高的产品特点，借鉴其成功经验</li>
                    <li>定期更新产品信息，保持数据的时效性</li>
                    <li>结合市场趋势，适时调整产品策略</li>
                </ul>
                
                <h4>数据质量评估</h4>
                <p>本次分析基于<span class="highlight">[具体数据量]</span>条产品数据，数据完整性良好。</p>
            </div>
        </div>
        
        <div class="footer">
            <p>报告生成工具: 产品数据分析助手 v1.0 | 数据更新频率: 每日自动更新</p>
        </div>
    </div>
</body>
</html>'''
        
        # 写入HTML文件
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 打印成功信息
        report_path = os.path.abspath(report_filename)
        print(f"✅ HTML分析报告已成功生成！")
        print(f"📄 报告文件：{report_filename}")
        print(f"📍 文件位置：{report_path}")
        print(f"💡 提示：可以用浏览器打开查看HTML报告")
        
        return report_filename
        
    except Exception as e:
        print(f"❌ 生成HTML报告失败: {e}")
        return None

def open_report(report_file):
    """使用默认浏览器打开报告"""
    if report_file and os.path.exists(report_file):
        print(f"🌐 正在使用默认浏览器打开报告...")
        try:
            webbrowser.open(f"file://{report_file}")
            print("✅ 报告已成功在浏览器中打开！")
            return True
        except Exception as e:
            print(f"❌ 无法打开浏览器: {e}")
            print(f"💡 请手动打开报告文件: {report_file}")
            return False
    else:
        # 尝试查找最新的报告文件
        report_files = glob.glob(os.path.join(SCRIPT_DIR, '竞品分析报告_*.html'))
        if report_files:
            latest_report = max(report_files, key=os.path.getmtime)
            print(f"🔍 找到最新报告: {latest_report}")
            return open_report(latest_report)
        else:
            print("❌ 未找到生成的HTML报告文件")
            return False

if __name__ == "__main__":
    # 导入数据准备模块并生成报告
    # 注意：这里需要确保analyze_data.py已经更新为只返回数据
    import analyze_data
    
    print("📊 正在获取产品数据...")
    top5_products = analyze_data.analyze_top_growth_products(return_data=True)
    shop_top_products = analyze_data.analyze_top_growth_by_shop(return_data=True)
    
    report_file = generate_html_report(top5_products, shop_top_products)
    open_report(report_file)