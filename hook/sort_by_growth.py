import json
from datetime import datetime
import os

print("当前工作目录:", os.getcwd())
print("文件是否存在:", os.path.exists('raw_response_20251026_141657.json'))

# 读取JSON文件
try:
    with open('raw_response_20251026_141657.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print("成功读取JSON文件")
    print("数据结构:", list(data.keys()))
    
    # 提取产品列表
    if 'data' in data and 'peer_shop_top_sale_goods_info_list' in data['data']:
        products = data['data']['peer_shop_top_sale_goods_info_list']
        print(f'共提取到 {len(products)} 个产品\n')
    else:
        print("数据结构不符合预期")
        print("data内容:", data.get('data', {}).keys())
        products = []
except Exception as e:
    print(f"读取JSON文件时出错: {e}")
    products = []

# 增长率排序的关键函数
def growth_rate_key(growth_str):
    if growth_str == '-':
        return (-1, 0)  # 没有增长率数据排在最后
    
    # 检查是否为负增长
    is_negative = growth_str.startswith('-')
    
    # 处理范围值
    if '-' in growth_str and (is_negative and growth_str.count('-') > 1 or not is_negative):
        # 提取数字部分
        try:
            # 对于负增长，格式可能是 "-10%--15%"
            if is_negative:
                # 去掉开头的负号和最后的百分号，然后分割
                parts = growth_str[1:-1].split('--')
                low = float(parts[0])
                high = float(parts[1])
                # 负增长取较低的负值（更负）作为排序依据
                avg = (low + high) / 2
                return (-2, avg)  # 负增长排在没有数据之前
            else:
                # 对于正增长，格式是 "100%-200%"
                parts = growth_str[:-1].split('-')
                low = float(parts[0])
                high = float(parts[1])
                # 正增长取较高的值作为排序依据
                avg = (low + high) / 2
                return (1, -avg)  # 注意这里用负值，因为Python的sort是升序
        except:
            return (-1, 0)
    else:
        # 单个值的情况
        try:
            value = float(growth_str.replace('%', ''))
            if value < 0:
                return (-2, value)  # 负增长
            else:
                return (1, -value)  # 正增长，用负值实现降序
        except:
            return (-1, 0)

# 按增长率排序
products_sorted = sorted(products, key=lambda x: growth_rate_key(x['pay_amount_growth_rate']), reverse=True)

# 显示前5个产品
print('===== 按增长率排序的前5个产品 =====')
for i, product in enumerate(products_sorted[:5], 1):
    print(f'\n{i}. 产品名称: {product["product_name"]}')
    print(f'   产品ID: {product["product_id"]}')
    print(f'   价格范围: {product["price_range"]}')
    print(f'   支付金额: {product["pay_amount"]}')
    print(f'   增长率: {product["pay_amount_growth_rate"]}')
    print(f'   曝光人数: {product["impressions_people_num"]}')
    print(f'   产品图片URL: {product["product_pic"]}')

# 生成报告
print('\n正在生成报告...')
with open('growth_sorted_top5.txt', 'w', encoding='utf-8') as f:
    f.write(f'产品增长率排序报告\n')
    f.write(f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
    
    f.write('===== 按增长率排序的前5个产品 =====\n\n')
    for i, product in enumerate(products_sorted[:5], 1):
        f.write(f'{i}. 产品名称: {product["product_name"]}\n')
        f.write(f'   产品ID: {product["product_id"]}\n')
        f.write(f'   价格范围: {product["price_range"]}\n')
        f.write(f'   支付金额: {product["pay_amount"]}\n')
        f.write(f'   增长率: {product["pay_amount_growth_rate"]}\n')
        f.write(f'   曝光人数: {product["impressions_people_num"]}\n')
        f.write(f'   产品图片URL: {product["product_pic"]}\n\n')

print('\n报告已保存至: growth_sorted_top5.txt')
print('图片URL也已包含在报告中。')