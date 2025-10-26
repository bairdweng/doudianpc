import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime

# 动态获取今天的日期
today = datetime.now().strftime('%Y-%m-%d')

# 定义URL模板列表，支持多个计划
URL_TEMPLATES = [
    # 计划1的URL模板
    "https://qianchuan.jinritemai.com/uni-prom?aavid=1810367512806403&awemeId=&latestAweme=&videoId=&adId=1846507279345895&productId=&materialId=&ct=1&dr=TODAY%2CTODAY&sourceFrom=&utm_source=qianchuan-origin-entrance&utm_medium=doudian-pc&utm_campaign=top-navigation-qianchuan&utm_content=&utm_term=&liveAwemeId=&liveQcpxMode=0&liveAdId=&ncrAdId=&ncrStartTime=&ncrEndTime=&ncrIsFirstReport=&ncrZhanneixin=&autoShowGrabFirstScreen=&autoShowMaterialHeat=&autoShowROI2Raise=&uniBatchTaskId=&openMaterialDrawer=&uni=%7B%22uniTab%22%3A%22ad%22%7D#adr=%7B%22dateRange%22%3A%5B%22TODAY%22%2C%22TODAY%22%5D%2C%22adDetailTab%22%3A%22creative%22%7D&umg=1&uniVideoTab=&usbt=0&dut=TODAY_TIME&uni=%7B%22ad%22%3A%22%7B%5C%22p%5C%22%3A%5C%221%5C%22%2C%5C%22ps%5C%22%3A%5C%2210%5C%22%2C%5C%22sf%5C%22%3A%5C%22%5C%22%2C%5C%22st%5C%22%3A%5C%22desc%5C%22%2C%5C%22skw%5C%22%3A%5C%22%5C%22%2C%5C%22sd%5C%22%3A%5C%22%7B%5C%5C%5C%22option%5C%5C%5C%22%3A%5C%5C%5C%221%5C%5C%5C%22%2C%5C%5C%5C%22value%5C%5C%5C%22%3A%5C%5C%5C%22%5C%5C%5C%22%7D%5C%22%2C%5C%22act%5C%22%3A%5C%22%5C%22%2C%5C%22asft%5C%22%3A%5C%220%5C%22%2C%5C%22cos%5C%22%3A%5C%22-1%5C%22%7D%22%2C%22bp%22%3A%22%7B%5C%22p%5C%22%3A%5C%221%5C%22%2C%5C%22ps%5C%22%3A%5C%2210%5C%22%2C%5C%22sf%5C%22%3A%5C%22%5C%22%2C%5C%22st%5C%22%3A%5C%22desc%5C%22%2C%5C%22sk%5C%22%3A%5C%22%5C%22%7D%22%7D",
    # 计划2的URL模板（示例，可根据需要添加更多）
    "https://qianchuan.jinritemai.com/uni-prom?aavid=1810367512806403&awemeId=&latestAweme=&videoId=&adId=1846502417050890&productId=&materialId=&ct=1&dr=2025-10-22%2C2025-10-22&sourceFrom=&utm_source=qianchuan-origin-entrance&utm_medium=doudian-pc&utm_campaign=top-navigation-qianchuan&utm_content=&utm_term=&liveAwemeId=&liveQcpxMode=0&liveAdId=&ncrAdId=&ncrStartTime=&ncrEndTime=&ncrIsFirstReport=&ncrZhanneixin=&autoShowGrabFirstScreen=&autoShowMaterialHeat=&autoShowROI2Raise=&uniBatchTaskId=&openMaterialDrawer=&uni=%7B%22uniTab%22%3A%22ad%22%7D#adr=%7B%22dateRange%22%3A%5B%222025-10-22%22%2C%222025-10-22%22%5D%2C%22adDetailTab%22%3A%22creative%22%7D&umg=1&uniVideoTab=&usbt=0&dut=2025-10-22%2016%3A46&uni=%7B%22ad%22%3A%22%7B%5C%22p%5C%22%3A%5C%221%5C%22%2C%5C%22ps%5C%22%3A%5C%2210%5C%22%2C%5C%22sf%5C%22%3A%5C%22%5C%22%2C%5C%22st%5C%22%3A%5C%22desc%5C%22%2C%5C%22skw%5C%22%3A%5C%22%5C%22%2C%5C%22sd%5C%22%3A%5C%22%7B%5C%5C%5C%22option%5C%5C%5C%22%3A%5C%5C%5C%221%5C%5C%5C%22%2C%5C%5C%5C%22value%5C%5C%5C%22%3A%5C%5C%5C%22%5C%5C%5C%22%7D%5C%22%2C%5C%22act%5C%22%3A%5C%22%5C%22%2C%5C%22asft%5C%22%3A%5C%220%5C%22%2C%5C%22cos%5C%22%3A%5C%22-1%5C%22%7D%22%2C%22bp%22%3A%22%7B%5C%22p%5C%22%3A%5C%221%5C%22%2C%5C%22ps%5C%22%3A%5C%2210%5C%22%2C%5C%22sf%5C%22%3A%5C%22%5C%22%2C%5C%22st%5C%22%3A%5C%22desc%5C%22%2C%5C%22sk%5C%22%3A%5C%22%5C%22%7D%22%7D"
]

# 生成今天的URL列表
def generate_today_urls():
    today_time = datetime.now().strftime('%Y-%m-%d%20%H%3A%M')
    today_urls = []
    for template in URL_TEMPLATES:
        # 替换日期占位符
        today_url = template.replace('TODAY', today).replace('TODAY_TIME', today_time)
        today_urls.append(today_url)
    return today_urls

# 定义要抓取的URL列表
DEFAULT_URLS = generate_today_urls()  # 使用动态生成的今天URL列表
# 用于存储每个计划的报告数据
reports_data = []
report_counter = 0

# 处理响应的函数
async def handle_response(response):
    global report_counter
    url = response.url
    # URL条件判断
    if "/uni-promotion/material/list-required" in url:
        try:
            # 尝试获取JSON响应
            data = await response.json()
            report_counter += 1
            print(f"✅ 成功捕获计划 {report_counter} 响应数据 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            # 保存报告数据，稍后为每个计划生成独立报告
            reports_data.append((report_counter, data))
        except Exception as e:
            print(f"❌ 处理响应时出错: {e}")

# 主运行函数
async def run(urls):
    # 清空报告数据列表
    global reports_data, report_counter
    reports_data = []
    report_counter = 0
    
    async with async_playwright() as p:
        # 启动浏览器（使用Chrome配置）
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="/Users/bairdweng/Library/Application Support/Google/Chrome/Default",
            channel="chrome",
            headless=False
        )
        page = await browser.new_page()

        # 绑定response事件
        page.on("response", lambda response: asyncio.create_task(handle_response(response)))

        for i, url in enumerate(urls):
            # 验证URL有效性
            if not url.startswith(('http://', 'https://')):
                print(f"❌ 计划 {i+1} URL无效: {url}")
                continue
            
            print(f"🔹 开始访问计划 {i+1} - {url}")
            await page.goto(url)
            await asyncio.sleep(15)  # 等待网络请求触发
            print(f"🔹 计划 {i+1} 访问完成")

        print("✅ 所有计划访问完成")
        await browser.close()
    
    # 为每个计划生成报告并合并到一个文件
    print(f"\n📊 开始生成 {len(reports_data)} 个计划的报告...")
    all_reports = []
    
    # 添加整体报告标题
    all_reports.append("=" * 60)
    all_reports.append(f"📊 {today} 多计划素材数据分析综合报告")
    all_reports.append("=" * 60)
    all_reports.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    all_reports.append("\n")
    
    # 生成并收集每个计划的报告
    for plan_num, data in reports_data:
        print(f"\n\n===========================================")
        print(f"📋 计划 {plan_num} 报告")
        print("===========================================")
        report_text = generate_report(data, plan_num)
        all_reports.append("\n" * 2)
        all_reports.append(report_text)
    
    # 保存合并后的报告
    if all_reports:
        report_filename = f"{today}_素材分析报告.txt"
        try:
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_reports))
            print(f"\n✅ 报告已保存至: {report_filename}")
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")
    
    if not reports_data:
        print("❌ 未捕获到任何计划的响应数据")

# 简单运行函数（无需定时任务）
async def main():
    global DEFAULT_URLS
    # 重新生成今天的URL列表，确保使用最新时间
    DEFAULT_URLS = generate_today_urls()
    
    print(f"🚀 开始运行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📝 已配置 {len(DEFAULT_URLS)} 个推广计划 (日期: {today})")
    print("📝 URL判断条件已设置为'/uni-promotion/material/list-required'")
    print("🔍 脚本将为每个计划生成独立的今日数据分析报告")
    
    try:
        await run(DEFAULT_URLS)
        print(f"✅ 所有计划运行完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"❌ 运行出错: {e}")

def generate_report(data, plan_num):
    """分析捕获的数据并生成报告，返回报告文本"""
    report_lines = []
    
    report_lines.append(f"📊 计划 {plan_num} - {today} 素材数据分析报告")
    report_lines.append("===========================================")
    report_lines.append(f"📅 数据日期范围: {today}")
    report_lines.append("===========================================")
    
    try:
        # 提取统计数据
        stats_data = data.get('data', {}).get('statsData', {})
        rows = stats_data.get('rows', [])
        totals = stats_data.get('totals', {})
        
        # 输出总体数据
        report_lines.append(f"🔹 素材总数: {len(rows)}")
        report_lines.append(f"🔹 总曝光量: {totals.get('productShowCountForRoi2', {}).get('value', 0):,}")
        report_lines.append(f"🔹 总点击量: {totals.get('productClickCountForRoi2', {}).get('value', 0):,}")
        report_lines.append(f"🔹 总花费: ¥{totals.get('statCostForRoi2', {}).get('value', 0):.2f}")
        report_lines.append(f"🔹 总订单: {totals.get('totalPayOrderCountForRoi2', {}).get('value', 0)}")
        report_lines.append(f"🔹 总GMV: ¥{totals.get('totalPayOrderGmvForRoi2', {}).get('value', 0):.2f}")
        report_lines.append(f"🔹 整体ROI: {totals.get('totalPrepayAndPayOrderRoi2', {}).get('value', 0):.2f}")
        report_lines.append(f"🔹 平均点击率: {totals.get('productCvrRateForRoi2', {}).get('valueStr', '0%')}")
        report_lines.append(f"🔹 平均转化率: {totals.get('productConvertRateForRoi2', {}).get('valueStr', '0%')}")
        
        # 分析各个素材
        report_lines.append("")
        report_lines.append("📋 素材详细分析:")
        report_lines.append("---------------------------------------------------")
        best_roi = None
        best_material = None
        
        for i, row in enumerate(rows):
            dimensions = row.get('dimensions', {})
            metrics = row.get('metrics', {})
            
            material_name = dimensions.get('roi2MaterialVideoName', {}).get('valueStr', 'Unknown')
            roi = metrics.get('totalPrepayAndPayOrderRoi2', {}).get('value', 0)
            orders = metrics.get('totalPayOrderCountForRoi2', {}).get('value', 0)
            cost = metrics.get('statCostForRoi2', {}).get('value', 0)
            show_count = metrics.get('productShowCountForRoi2', {}).get('value', 0)
            click_count = metrics.get('productClickCountForRoi2', {}).get('value', 0)
            ctr = metrics.get('productCvrRateForRoi2', {}).get('valueStr', '0%')
            conv_rate = metrics.get('productConvertRateForRoi2', {}).get('valueStr', '0%')
            
            # 记录最佳ROI的素材
            if roi > (best_roi or 0):
                best_roi = roi
                best_material = material_name
            
            # 输出素材信息
            report_lines.append("")
            report_lines.append(f"素材 {i+1}: {material_name}")
            report_lines.append(f"  • ROI: {roi:.2f}")
            report_lines.append(f"  • 订单: {orders}")
            report_lines.append(f"  • 花费: ¥{cost:.2f}")
            report_lines.append(f"  • 曝光: {show_count:,}")
            report_lines.append(f"  • 点击: {click_count:,}")
            report_lines.append(f"  • 点击率: {ctr}")
            report_lines.append(f"  • 转化率: {conv_rate}")
        
        # 给出建议
        report_lines.append("")
        report_lines.append("💡 关键建议:")
        if best_material:
            report_lines.append(f"1. 重点投放: '{best_material}' ROI表现最佳，建议增加预算")
        
        # 计算无效素材比例
        zero_orders = sum(1 for row in rows if row.get('metrics', {}).get('totalPayOrderCountForRoi2', {}).get('value', 0) == 0)
        if zero_orders > 0:
            report_lines.append(f"2. 优化/暂停: {zero_orders}个素材无转化，建议优化或暂停")
        
        # 检查整体ROI
        overall_roi = totals.get('totalPrepayAndPayOrderRoi2', {}).get('value', 0)
        if overall_roi < 1:
            report_lines.append(f"3. 整体ROI偏低 ({overall_roi:.2f})，建议调整投放策略")
        
        report_lines.append("")
        report_lines.append("===========================================")
        report_lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("===========================================")
        
    except Exception as e:
        report_lines.append(f"❌ 生成报告时出错: {e}")
    
    # 同时打印到控制台和返回报告文本
    report_text = '\n'.join(report_lines)
    print(report_text)
    return report_text

if __name__ == "__main__":
    asyncio.run(main())