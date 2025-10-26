import asyncio
import json
import re
import os
import sqlite3
from datetime import datetime
from playwright.async_api import async_playwright
from playwright.async_api import Request, Response

# 获取脚本所在目录的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 产品分析和报告生成类
class ProductAnalyzer:
    def __init__(self):
        self.products_data = []
        self.request_captured = False
        self.current_shop_id = None
        self.current_shop_name = None
        self.db_conn = None
        self.initialize_database()
        # 新增：存储店铺列表
        self.shop_list = []
        # 新增：标记是否已获取店铺列表
        self.got_shop_list = False
        # 新增：存储已处理的店铺ID，避免重复处理
        self.processed_shop_ids = set()
        # 新增：标记是否正在自动采集模式
        self.auto_collection_mode = False
        # 新增：存储当前页面引用，用于发送请求
        self.current_page = None
        # 新增：存储原始请求模板
        self.products_request_template = None
    
    def initialize_database(self):
        """初始化SQLite数据库"""
        try:
            # 使用脚本目录路径连接到SQLite数据库
            db_path = os.path.join(SCRIPT_DIR, 'product_data.db')
            self.db_conn = sqlite3.connect(db_path)
            cursor = self.db_conn.cursor()
            
            # 创建店铺表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS shops (
                shop_id TEXT PRIMARY KEY,
                shop_name TEXT,
                last_updated TIMESTAMP
            )
            ''')
            
            # 创建产品表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                product_name TEXT,
                product_pic TEXT,
                price_range TEXT,
                pay_amount TEXT,
                pay_amount_growth_rate TEXT,
                impressions_people_num TEXT,
                shop_id TEXT,
                captured_at TIMESTAMP,
                qr_code TEXT,
                FOREIGN KEY (shop_id) REFERENCES shops (shop_id)
            )
            ''')
            
            # 创建索引以提高查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_shop_id ON products(shop_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_captured_at ON products(captured_at)')
            
            self.db_conn.commit()
            print("✅ 数据库初始化成功")
        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")
    
    async def handle_request(self, request):
        """处理请求，提取关键信息"""
        url = request.url
        
        # 只保留关键URL捕获信息
        if "get_sub_peer_shop_list" in url:
            print(f"📨 捕获到店铺列表请求: {url}")
            # 强制设置请求捕获标志
            self.request_captured = True
            try:
                # 尝试获取请求体数据
                if request.post_data:
                    try:
                        post_data = json.loads(request.post_data)
                        # 保存请求模板，用于后续自动发送请求
                        self.products_request_template = {
                            'url': url,
                            'method': request.method,
                            'headers': dict(request.headers),
                            'post_data': post_data
                        }
                    except Exception as e:
                        pass
            except Exception as e:
                pass
        
        # 处理产品信息请求 - 使用更灵活的匹配
        elif "business_chance_center" in url and "peer_shop_top_sale_goods_info" in url:
            print(f"📨 捕获到产品信息请求: {url}")
            # 设置请求捕获标志
            self.request_captured = True
            try:
                # 保存请求模板，用于后续自动发送请求
                if request.post_data:
                    try:
                        post_data = json.loads(request.post_data)
                        # 保存请求模板
                        self.products_request_template = {
                            'url': url,
                            'method': request.method,
                            'headers': dict(request.headers),
                            'post_data': post_data
                        }
                        
                        # 检查是否包含店铺相关信息
                        if isinstance(post_data, dict):
                            # 保存当前处理的店铺信息
                            if 'shop_id' in post_data:
                                self.current_shop_id = post_data['shop_id']
                            if 'shop_name' in post_data:
                                self.current_shop_name = post_data['shop_name']
                    except:
                        pass
            except Exception as e:
                pass
    
    async def handle_response(self, response):
        """处理响应，提取店铺和产品数据"""
        url = response.url
        request = response.request
        
        # 处理店铺列表请求 - 使用更宽松的匹配规则
        if "get_sub_peer_shop_list" in url or ("peer_shop" in url and "list" in url):
            # 强制设置请求捕获标志
            self.request_captured = True
            try:
                # 检查响应状态码
                if response.status == 200:
                    # 解析JSON响应
                    try:
                        data = await response.json()
                        
                        # 保存完整的响应数据到临时文件（带时间戳）
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        shop_list_file = os.path.join(SCRIPT_DIR, f'shop_list_{timestamp}.json')
                        with open(shop_list_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        
                        # 尝试多种可能的数据结构路径
                        # 路径1: data.peer_shop_list
                        if isinstance(data, dict):
                            # 检查直接在data中的情况
                            if 'peer_shop_list' in data:
                                shop_list = data['peer_shop_list']
                                # 保存店铺列表到实例变量，用于后续自动采集
                                self.shop_list = shop_list
                                self.got_shop_list = True
                                print(f"✅ 成功获取店铺列表，包含 {len(shop_list)} 个店铺")
                                # 保存店铺信息到数据库
                                self.save_shop_list_to_database(shop_list)
                            # 路径2: data.data.peer_shop_list
                            elif 'data' in data and isinstance(data['data'], dict) and 'peer_shop_list' in data['data']:
                                shop_list = data['data']['peer_shop_list']
                                # 保存店铺列表到实例变量，用于后续自动采集
                                self.shop_list = shop_list
                                self.got_shop_list = True
                                print(f"✅ 成功获取店铺列表，包含 {len(shop_list)} 个店铺")
                                # 保存店铺信息到数据库
                                self.save_shop_list_to_database(shop_list)
                            # 路径3: 检查其他可能的键名
                            elif 'data' in data and isinstance(data['data'], dict) and 'list' in data['data']:
                                shop_list = data['data']['list']
                                if isinstance(shop_list, list) and len(shop_list) > 0 and isinstance(shop_list[0], dict):
                                    # 保存店铺列表到实例变量，用于后续自动采集
                                    self.shop_list = shop_list
                                    self.got_shop_list = True
                                    print(f"✅ 成功获取店铺列表，包含 {len(shop_list)} 个店铺")
                                    # 保存店铺信息到数据库
                                    self.save_shop_list_to_database(shop_list)
                    except Exception as json_err:
                        print(f"❌ 解析店铺列表JSON失败: {json_err}")
                        # 保存原始响应文本用于调试
                        try:
                            text = await response.text()
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            debug_file = os.path.join(SCRIPT_DIR, f'shop_list_raw_{timestamp}.txt')
                            with open(debug_file, 'w', encoding='utf-8') as f:
                                f.write(text[:2000])  # 只保存前2000字符
                            print(f"💾 原始店铺列表响应已保存到 {debug_file} 用于分析")
                        except:
                            pass
            except Exception as e:
                print(f"❌ 处理店铺列表响应失败: {e}")
        
        # 处理产品信息请求响应 - 使用更灵活的匹配
        elif "business_chance_center" in url and "peer_shop_top_sale_goods_info" in url:
            print(f"📨 捕获到产品信息响应: {url}")
            try:
                # 解析JSON响应
                try:
                    data = await response.json()
                    print(f"📋 产品响应数据结构: {list(data.keys())}")
                    
                    # 保存响应数据到products_data
                    product_data_found = False
                    if isinstance(data, dict) and 'data' in data:
                        print(f"🔍 发现data字段，内部结构: {list(data['data'].keys()) if isinstance(data['data'], dict) else type(data['data'])}")
                        # 尝试不同的数据结构路径
                        if isinstance(data['data'], dict):
                            # 路径1: data.data.list
                            if 'list' in data['data']:
                                self.products_data = data['data']['list']
                                self.request_captured = True
                                product_data_found = True
                                print(f"✅ 从data.data.list解析到 {len(self.products_data)} 个产品数据")
                            # 路径2: data.data.data
                            elif 'data' in data['data']:
                                self.products_data = data['data']['data']
                                self.request_captured = True
                                product_data_found = True
                                print(f"✅ 从data.data.data解析到 {len(self.products_data)} 个产品数据")
                            # 检查其他可能的键名
                            elif 'peer_shop_top_sale_goods_info_list' in data['data']:
                                self.products_data = data['data']['peer_shop_top_sale_goods_info_list']
                                self.request_captured = True
                                product_data_found = True
                                print(f"✅ 从data.data.peer_shop_top_sale_goods_info_list解析到 {len(self.products_data)} 个产品数据")
                            elif 'product_list' in data['data']:
                                self.products_data = data['data']['product_list']
                                self.request_captured = True
                                product_data_found = True
                                print(f"✅ 从data.data.product_list解析到 {len(self.products_data)} 个产品数据")
                        # 如果data.data直接是列表
                        elif isinstance(data['data'], list):
                            self.products_data = data['data']
                            self.request_captured = True
                            product_data_found = True
                            print(f"✅ 从data.data列表解析到 {len(self.products_data)} 个产品数据")
                    # 路径3: 直接在data中有list
                    elif isinstance(data, dict) and 'list' in data:
                        self.products_data = data['list']
                        self.request_captured = True
                        product_data_found = True
                        print(f"✅ 从data.list解析到 {len(self.products_data)} 个产品数据")
                    # 路径4: 直接在data中有peer_shop_top_sale_goods_info_list
                    elif isinstance(data, dict) and 'peer_shop_top_sale_goods_info_list' in data:
                        self.products_data = data['peer_shop_top_sale_goods_info_list']
                        self.request_captured = True
                        product_data_found = True
                        print(f"✅ 从data.peer_shop_top_sale_goods_info_list解析到 {len(self.products_data)} 个产品数据")
                    # 路径5: 直接在data中有product_list
                    elif isinstance(data, dict) and 'product_list' in data:
                        self.products_data = data['product_list']
                        self.request_captured = True
                        product_data_found = True
                        print(f"✅ 从data.product_list解析到 {len(self.products_data)} 个产品数据")
                except Exception as json_err:
                    print(f"❌ 解析产品JSON失败: {json_err}")
                    # 保存原始响应文本
                    try:
                        text = await response.text()
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        debug_file = os.path.join(SCRIPT_DIR, f'product_response_raw_{timestamp}.txt')
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(text[:2000])  # 只保存前2000字符
                        print(f"💾 原始响应已保存到 {debug_file} 用于分析")
                    except:
                        pass
            except Exception as e:
                print(f"❌ 处理产品响应失败: {e}")
            # 已在上方处理
        
        # 处理产品信息请求
        elif "/business_chance_center/peer_shop_top_sale_goods_info" in url:
            print(f"📨 捕获到备用路径产品信息响应: {url}")
            try:
                # 解析JSON响应
                data = await response.json()
                print(f"📋 备用路径产品响应数据结构: {list(data.keys())}")
                
                # 使用标准解析逻辑
                product_data_found = False
                if isinstance(data, dict) and 'data' in data:
                    inner_data = data['data']
                    print(f"🔍 备用路径发现data字段，内部结构: {list(inner_data.keys()) if isinstance(inner_data, dict) else type(inner_data)}")
                    
                    # 检查是否存在peer_shop_top_sale_goods_info_list
                    if 'peer_shop_top_sale_goods_info_list' in inner_data:
                        self.products_data = inner_data['peer_shop_top_sale_goods_info_list']
                        product_data_found = True
                        print(f"✅ 备用路径从data.data.peer_shop_top_sale_goods_info_list解析到 {len(self.products_data)} 个产品数据")
                    elif 'product_list' in inner_data:
                        self.products_data = inner_data['product_list']
                        product_data_found = True
                        print(f"✅ 备用路径从data.data.product_list解析到 {len(self.products_data)} 个产品数据")
                    elif 'list' in inner_data:
                        self.products_data = inner_data['list']
                        product_data_found = True
                        print(f"✅ 备用路径从data.data.list解析到 {len(self.products_data)} 个产品数据")
                    elif 'data' in inner_data:
                        self.products_data = inner_data['data']
                        product_data_found = True
                        print(f"✅ 备用路径从data.data.data解析到 {len(self.products_data)} 个产品数据")
                    else:
                        self.products_data = []
                else:
                    self.products_data = []
                
                # 如果成功解析到产品数据
                if self.products_data and product_data_found:
                    self.request_captured = True
                    print(f"✅ 备用路径成功捕获到产品数据，共 {len(self.products_data)} 条")
            except Exception as e:
                print(f"❌ 处理备用路径产品响应失败: {e}")
                # 保存原始响应文本
                try:
                    text = await response.text()
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    debug_file = os.path.join(SCRIPT_DIR, f'product_alt_response_raw_{timestamp}.txt')
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(text[:2000])  # 只保存前2000字符
                    print(f"💾 备用路径原始响应已保存到 {debug_file} 用于分析")
                except:
                    pass
    
    def get_growth_score(self, growth_rate_str):
        """根据增长率字符串计算排序分数"""
        if not growth_rate_str:
            return 0
            
        # 处理负增长率范围，如 "-10%--15%"
        if growth_rate_str.startswith('-'):
            # 提取负增长范围的两个数字
            match = re.match(r'-([\d.]+)%--([\d.]+)%', growth_rate_str)
            if match:
                # 对于负增长，取较小的负值作为排序依据（更负的增长）
                val1, val2 = float(match.group(1)), float(match.group(2))
                # 返回负数表示负增长
                return -max(val1, val2)
            return 0
        
        # 处理正增长率范围，如 "50%-100%", "100%-200%"
        match = re.match(r'([\d.]+)%-(\d+)%', growth_rate_str)
        if match:
            min_val, max_val = float(match.group(1)), float(match.group(2))
            # 对于正增长，计算中间值作为排序依据
            # 根据规则：100%-200% > 50%-100% > -10%--15%
            # 我们通过返回较高的正数值来确保正确排序
            return (min_val + max_val) / 2
        
        return 0
    
    def save_shop_list_to_database(self, shop_list):
        """将店铺列表数据保存到SQLite数据库"""
        try:
            if not self.db_conn:
                print("❌ 数据库连接未初始化")
                return
                
            cursor = self.db_conn.cursor()
            captured_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            shops_saved = 0
            for shop in shop_list:
                shop_id = shop.get('shop_id', '')
                shop_name = shop.get('shop_name', '未知店铺')
                
                # 使用INSERT OR REPLACE更新店铺信息
                cursor.execute(
                    "INSERT OR REPLACE INTO shops (shop_id, shop_name, last_updated) VALUES (?, ?, ?)",
                    (shop_id, shop_name, captured_at)
                )
                shops_saved += 1
            
            self.db_conn.commit()
            print(f"✅ 成功保存 {shops_saved} 个店铺信息到数据库")
        except Exception as e:
            print(f"❌ 保存店铺列表到数据库失败: {e}")
            if self.db_conn:
                self.db_conn.rollback()
    
    async def auto_collect_all_shops(self, page):
        """自动批量采集所有店铺的数据"""
        if not self.got_shop_list or not self.shop_list:
            print("❌ 未获取店铺列表，无法开始自动采集")
            return
            
        if not self.products_request_template:
            print("❌ 未获取产品请求模板，无法开始自动采集")
            return
            
        self.current_page = page
        self.auto_collection_mode = True
        print("🚀 开始自动批量采集所有店铺数据...")
        print(f"📊 总共需要采集 {len(self.shop_list)} 个店铺")
        
        # 过滤已处理的店铺
        shops_to_process = [shop for shop in self.shop_list if shop.get('shop_id') not in self.processed_shop_ids]
        print(f"📋 待处理店铺数量: {len(shops_to_process)}")
        
        # 为当前页面创建临时监听器，专门处理自动发送的请求响应
        original_products_data = self.products_data.copy()
        
        success_count = 0
        fail_count = 0
        
        for i, shop in enumerate(shops_to_process, 1):
            shop_id = shop.get('shop_id')
            shop_name = shop.get('shop_name', '未知店铺')
            
            if not shop_id:
                print(f"⚠️  店铺 {i} 缺少shop_id，跳过")
                fail_count += 1
                continue
                
            print(f"\n🔄 正在采集店铺 {i}/{len(shops_to_process)}: {shop_name} (ID: {shop_id})")
            
            try:
                # 重置产品数据
                self.products_data = []
                self.request_captured = False
                
                # 准备请求数据
                request_data = self.products_request_template['post_data'].copy()
                request_data['shop_id'] = shop_id
                
                # 保存当前店铺信息
                self.current_shop_id = shop_id
                self.current_shop_name = shop_name
                
                print(f"📤 发送产品信息请求...")
                print(f"📋 请求参数: shop_id={shop_id}")
                
                # 发送请求
                response = await page.request.post(
                    self.products_request_template['url'],
                    data=json.dumps(request_data, ensure_ascii=False),
                    headers=self.products_request_template['headers']
                )
                
                print(f"📥 收到响应，状态码: {response.status}")
                
                # 手动处理响应
                data = await response.json()
                
                # 解析产品数据
                if isinstance(data, dict) and 'data' in data:
                    inner_data = data['data']
                    
                    # 检查是否存在peer_shop_top_sale_goods_info_list
                    if 'peer_shop_top_sale_goods_info_list' in inner_data:
                        self.products_data = inner_data['peer_shop_top_sale_goods_info_list']
                        print(f"📊 解析到 {len(self.products_data)} 个产品数据")
                    elif 'product_list' in inner_data:
                        self.products_data = inner_data['product_list']
                        print(f"📊 解析到 {len(self.products_data)} 个产品数据")
                    elif isinstance(inner_data, list):
                        self.products_data = inner_data
                        print(f"📊 解析到 {len(self.products_data)} 个产品数据")
                    else:
                        print(f"❌ 未找到产品列表数据")
                
                # 保存数据到数据库
                if self.products_data:
                    # 调试：在保存到数据库前检查qr_code字段
                    qr_code_count = 0
                    for product in self.products_data[:3]:  # 只检查前3个产品
                        if 'qr_code' in product and product['qr_code']:
                            qr_code_count += 1
                            print(f"🔍 产品 {product.get('product_id', 'unknown')} 包含非空qr_code字段")
                        else:
                            print(f"🔍 产品 {product.get('product_id', 'unknown')} qr_code字段为空或不存在")
                    print(f"🔍 总共有 {qr_code_count}/{min(3, len(self.products_data))} 个产品包含非空qr_code字段")
                    self.save_to_database()
                    self.processed_shop_ids.add(shop_id)
                    success_count += 1
                    print(f"✅ 店铺 {shop_name} 数据采集成功")
                else:
                    print(f"❌ 店铺 {shop_name} 未采集到有效数据")
                    fail_count += 1
                
                # 避免请求过快，添加延迟
                print("⏱️  等待2秒后继续下一个店铺...")
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ 采集店铺 {shop_name} 数据时出错: {e}")
                import traceback
                traceback.print_exc()
                fail_count += 1
                # 出错后也添加延迟，避免连续失败
                await asyncio.sleep(1)
        
        # 恢复原始数据
        self.products_data = original_products_data
        
        # 打印总结
        print("\n📋 自动批量采集完成！")
        print(f"✅ 成功采集: {success_count} 个店铺")
        print(f"❌ 采集失败: {fail_count} 个店铺")
        print(f"📊 已处理店铺总数: {len(self.processed_shop_ids)}")
        
        # 如果还有未处理的店铺，可以提示用户
        remaining_shops = len(self.shop_list) - len(self.processed_shop_ids)
        if remaining_shops > 0:
            print(f"💡 提示: 还有 {remaining_shops} 个店铺未处理，可以再次运行自动采集")
        
        self.auto_collection_mode = False
        print("\n🔄 已退出自动采集模式，可以继续手动操作")
    
    def save_to_database(self):
        """将采集的数据保存到SQLite数据库"""
        try:
            if not self.db_conn:
                print("❌ 数据库连接未初始化")
                return
                
            cursor = self.db_conn.cursor()
            captured_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 保存店铺信息
            if self.current_shop_id:
                # 先从数据库中查询是否已有该店铺信息
                cursor.execute("SELECT shop_name FROM shops WHERE shop_id = ?", (self.current_shop_id,))
                existing_shop = cursor.fetchone()
                
                # 优先使用当前提供的店铺名称，如果没有则尝试从数据库获取
                shop_name_to_save = self.current_shop_name
                
                # 如果当前没有提供名称，但数据库中有，则使用数据库中的名称
                if not shop_name_to_save and existing_shop and existing_shop[0]:
                    shop_name_to_save = existing_shop[0]
                # 如果都没有，使用默认名称
                if not shop_name_to_save:
                    shop_name_to_save = "未知店铺"
                
                # 使用INSERT OR REPLACE更新店铺信息
                cursor.execute(
                    "INSERT OR REPLACE INTO shops (shop_id, shop_name, last_updated) VALUES (?, ?, ?)",
                    (self.current_shop_id, shop_name_to_save, captured_at)
                )
            
            # 保存产品信息
            products_saved = 0
            for product in self.products_data:
                product_id = product.get('product_id', '')
                product_name = product.get('product_name', '未知产品')
                product_pic = product.get('product_pic', '')
                price_range = product.get('price_range', '')
                pay_amount = product.get('pay_amount', '')
                pay_amount_growth_rate = product.get('pay_amount_growth_rate', '')
                impressions_people_num = product.get('impressions_people_num', '')
                
                # 插入产品数据
                # 检查是否有qr_code字段，如果没有则使用空字符串
                qr_code = product.get('qr_code', '')
                cursor.execute(
                    '''INSERT INTO products 
                    (product_id, product_name, product_pic, price_range, pay_amount, 
                    pay_amount_growth_rate, impressions_people_num, shop_id, captured_at, qr_code) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (product_id, product_name, product_pic, price_range, pay_amount, 
                     pay_amount_growth_rate, impressions_people_num, self.current_shop_id, captured_at, qr_code)
                )
                products_saved += 1
            
            self.db_conn.commit()
            print(f"✅ 成功保存 {products_saved} 个产品到数据库")
        except Exception as e:
            print(f"❌ 保存数据到数据库失败: {e}")
            if self.db_conn:
                self.db_conn.rollback()

# 移除了所有文件读取相关功能，只保留接口监听功能

async def run_playwright():
    """运行Playwright监听目标请求"""
    analyzer = ProductAnalyzer()
    
    print("🔄 启动数据采集工具...")
    print("📝 本工具将监听特定API请求并保存数据到数据库")
    print("💾 数据将保存到SQLite数据库(product_data.db)")
    print("📊 请使用analyze_data.py脚本进行数据分析")
    print("✅ 数据库初始化成功")
    print("🔄 启动浏览器监听请求...")
    print("🚀 启动浏览器，开始监听请求...")
    print("📝 请在浏览器中访问相关页面，系统将自动捕获目标请求")
    print("💡 捕获到请求后将自动分析并生成报告")
    print("\n🛑 按 Ctrl+C 可随时停止监听")
    print("🚀 系统配置为自动模式：获取店铺列表和产品请求后将自动开始批量采集")
    
    async with async_playwright() as p:
        # 使用launch_persistent_context启动带有用户数据目录的浏览器
        context = await p.chromium.launch_persistent_context(
            user_data_dir="/Users/bairdweng/Desktop/myproject/doudianpc/chrome_user_data",
            headless=False,
            slow_mo=100,
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--window-size=1280,800"
            ]
        )
        
        # 获取浏览器实例
        browser = context.browser
        
        # 获取第一个页面或创建新页面
        if context.pages:
            page = context.pages[0]
        else:
            page = await context.new_page()
        
        # 直接打开指定的抖店页面
        target_url = "https://fxg.jinritemai.com/ffa/bu/NewBusinessCenter?btm_ppre=a0.b0.c0.d0&btm_pre=a2427.b76571.c902327.d871297&btm_show_id=5374be68-95d7-49f5-99f1-faab744c7567"
        print(f"🚀 正在打开目标URL: {target_url}")
        await page.goto(target_url)
        
        # 绑定请求和响应事件
        print("🔗 正在绑定浏览器事件监听器...")
        
        # 增强版请求监听器
        async def on_request(request):
            # print(f"📡 捕获到请求: {request.method} {request.url}")
            await analyzer.handle_request(request)
        
        # 增强版响应监听器
        async def on_response(response):
            # print(f"📡 捕获到响应: {response.status} {response.url}")
            await analyzer.handle_response(response)
        
        # 绑定事件监听器
        page.on("request", lambda request: asyncio.create_task(on_request(request)))
        page.on("response", lambda response: asyncio.create_task(on_response(response)))
        
        # 监听页面导航完成事件
        async def on_navigation(details):
            print(f"📍 页面导航完成: {details.url}")
        
        page.on("load", on_navigation)
        print("✅ 浏览器事件监听器绑定成功")
        print("📋 已启用增强版事件监听，将显示所有请求和响应")
        
        # 提示用户访问正确的业务页面
        print("🎯 请在浏览器中访问正确的业务页面")
        print("📋 系统将监控包含'get_sub_peer_shop_list'和'business_chance_center'的请求")
        print("💡 当您在业务页面中操作时，系统将自动捕获相关请求")
        
        # 等待用户操作并持续捕获请求
        try:
            print("\n⌛ 等待捕获目标请求...")
            print("🚀 系统已配置为自动采集模式")
            print("📊 获取店铺列表和产品请求模板后将自动开始批量采集")
            print("🔄 系统将持续监听，按Ctrl+C可随时停止")
            
            # 持续监听模式，不设置超时
            # 添加计数器显示监听状态
            counter = 0
            print("\n🔄 系统已启动监听模式")
            print("🎯 等待捕获店铺列表和产品请求模板")
            
            while True:
                # 检查是否已捕获请求
                if analyzer.request_captured:
                    # 如果捕获到数据，保存到数据库
                    if analyzer.products_data:
                        print("\n✅ 成功捕获产品数据")
                        print(f"📊 捕获到 {len(analyzer.products_data)} 个产品数据")
                        print("💾 开始保存数据到数据库...")
                        
                        # 保存数据到数据库
                        analyzer.save_to_database()
                        
                        # 重置请求捕获标志，准备捕获下一个店铺的数据
                        analyzer.request_captured = False
                        print("\n🔄 已重置捕获状态，准备捕获下一个店铺的数据")
                        print("🚀 自动采集模式：系统正在自动处理下一个店铺")
                        # 确保始终启用自动模式
                        analyzer.auto_collection_mode = True
                        # 只有在获取到店铺列表和产品请求模板后才开始自动采集
                        if analyzer.got_shop_list and analyzer.products_request_template:
                            print("📋 已获取所需数据，即将开始自动批量采集")
                            await analyzer.auto_collect_all_shops(page)
                        else:
                            print("⏳ 等待获取店铺列表和产品请求模板...")
                    else:
                        analyzer.request_captured = False
                
                # 每30秒打印一次监听状态
                counter += 1
                # 每5秒检查一次状态
                if counter % 5 == 0:
                    # 检查是否已获取店铺列表和产品请求模板，自动开启采集
                    if analyzer.got_shop_list and analyzer.products_request_template and not analyzer.auto_collection_mode:
                        print("🚀 自动采集条件已满足！")
                        print("🔄 系统将自动开始批量采集所有店铺数据")
                        analyzer.auto_collection_mode = True
                        await analyzer.auto_collect_all_shops(page)
                elif counter % 30 == 0:
                    # 30秒状态检查，提示用户系统仍在运行
                    print("🔄 系统持续运行中，等待捕获店铺列表和产品数据")
                    # 如果已经有一些数据但没有完整的店铺列表，也给用户提示
                    if analyzer.products_data and not analyzer.got_shop_list:
                        print("💡 提示：已捕获产品数据，但需要获取店铺列表才能开始自动批量采集")
                
                # 短暂休眠，避免CPU占用过高
                await asyncio.sleep(1)
        
        except KeyboardInterrupt:
            print("\n\n🛑 监听已停止")
        finally:
            # 关闭数据库连接
            if analyzer.db_conn:
                analyzer.db_conn.close()
                print("✅ 数据库连接已关闭")
                
            print("\n📋 使用说明:")
            print("1. 本工具监听特定API请求获取产品数据")
            print("2. 采集的数据自动保存到SQLite数据库(product_data.db)")
            print("3. 请使用analyze_data.py脚本进行数据分析")
            print("4. 浏览器保持打开状态，您可以继续查看其他店铺数据")
            
            print("\n✅ 数据采集工具已停止运行，浏览器将保持打开状态")

def main():
    """主函数，启动浏览器监听"""
    try:
        asyncio.run(run_playwright())
    except KeyboardInterrupt:
        print("\n🛑 用户中断操作")
        print("💡 提示: 您可以输入以下命令:")
        print("   - 'url' 手动输入URL")
        print("   - 'auto' 开始自动批量采集所有店铺数据")
        print("   - 'exit' 退出程序")
        
        while True:
            try:
                cmd = input("\n请输入命令: ")
                if cmd.lower() == 'url':
                    # 这里可以添加手动输入URL的处理逻辑
                    print("🔄 切换到手动URL输入模式")
                    # 重新启动监听
                    asyncio.run(run_playwright())
                elif cmd.lower() == 'auto':
                    print("🚀 准备开始自动批量采集所有店铺数据...")
                    print("📝 注意: 请确保已经获取过店铺列表和产品请求模板")
                    print("🔄 重新启动浏览器以执行自动采集")
                    # 重新启动监听，这次会自动执行采集
                    asyncio.run(run_playwright())
                elif cmd.lower() == 'exit':
                    print("👋 感谢使用，再见！")
                    break
                else:
                    print("❌ 未知命令，请重新输入")
            except KeyboardInterrupt:
                print("\n🛑 用户中断操作")
                break
    except Exception as e:
        print(f"❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()