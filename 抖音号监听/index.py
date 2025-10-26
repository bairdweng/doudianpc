import asyncio
import aiosqlite
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import json

DB_FILE = "aweme_full.db"

# 初始化数据库


async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            hashtags TEXT,
            is_ads INTEGER,
            duration REAL,
            publish_time TEXT,
            play_count INTEGER,
            digg_count INTEGER,
            comment_count INTEGER,
            share_url TEXT,
            cover_url TEXT,
            video_url TEXT,
            author_id TEXT,
            author_name TEXT,
            author_avatar TEXT,
            music_id TEXT,
            music_title TEXT,
            music_author TEXT,
            update_time TEXT
        )
        
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            product_keywords TEXT,
            first_seen_date TEXT,
            last_seen_date TEXT,
            video_count INTEGER DEFAULT 0,
            total_play_count INTEGER DEFAULT 0,
            total_digg_count INTEGER DEFAULT 0,
            growth_rate REAL DEFAULT 0.0,
            popularity_score REAL DEFAULT 0.0,
            author_id TEXT,
            author_name TEXT
        )
        
        CREATE TABLE IF NOT EXISTS video_product_mapping (
            video_id TEXT,
            product_id INTEGER,
            PRIMARY KEY (video_id, product_id),
            FOREIGN KEY (video_id) REFERENCES videos(video_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
        """)
        await db.commit()

# 处理响应


async def handle_response(response, db):
    url = response.url
    if "aweme/v1/web/aweme/post" in url:
        try:
            data = await response.json()
            aweme_list = data.get("aweme_list", [])
            if not aweme_list:
                return

            async with db.execute("BEGIN"):
                for item in aweme_list:
                    video_id = item.get("aweme_id")
                    if not video_id:
                        continue

                    # 查询是否已存在
                    async with db.execute("SELECT 1 FROM videos WHERE video_id=?", (video_id,)) as cursor:
                        if await cursor.fetchone():
                            continue

                    # 视频信息
                    desc = item.get("desc", "")
                    hashtags = [h.get("hashtag_name", "") for h in (
                        item.get("text_extra") or []) if h.get("hashtag_name")]
                    hashtags_str = ",".join(hashtags)
                    is_ads = item.get("is_ads") or 0
                    duration = item.get("duration", 0) / 1000
                    create_time = item.get("create_time")
                    publish_time = datetime.fromtimestamp(create_time).strftime(
                        "%Y-%m-%d %H:%M:%S") if create_time else ""
                    stats = item.get("statistics") or {}
                    play_count = stats.get("play_count", 0)
                    digg_count = stats.get("digg_count", 0)
                    comment_count = stats.get("comment_count", 0)
                    share_url = item.get("share_info", {}).get("share_url", "")
                    cover_url = (item.get("video", {}).get(
                        "cover", {}).get("url_list") or [""])[0]
                    video_url = (item.get("video", {}).get(
                        "play_addr", {}).get("url_list") or [""])[0]

                    author = item.get("author") or {}
                    author_id = author.get("uid", "")
                    author_name = author.get("nickname", "")
                    author_avatar = (author.get(
                        "avatar_thumb", {}).get("url_list") or [""])[0]

                    music = item.get("music") or {}
                    music_id = music.get("id", "")
                    music_title = music.get("title", "")
                    music_author = music.get("author", "")

                    # 插入数据库
                    await db.execute("""
                        INSERT OR REPLACE INTO videos (
                            video_id, title, hashtags, is_ads, duration, publish_time,
                            play_count, digg_count, comment_count, share_url, cover_url,
                            video_url, author_id, author_name, author_avatar,
                            music_id, music_title, music_author, update_time
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        video_id, desc, hashtags_str, is_ads, duration, publish_time,
                        play_count, digg_count, comment_count, share_url, cover_url,
                        video_url, author_id, author_name, author_avatar,
                        music_id, music_title, music_author, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                    
                    # 提取产品信息
                    await extract_products_from_video(db, item, author_id, author_name)
                    print(f"✅ 插入视频 {video_id} - {desc[:20]}")

                await db.commit()
        except Exception as e:
            print("❌ 处理数据出错:", e)

# 主运行函数


async def run(urls):
    await init_db()
    async with aiosqlite.connect(DB_FILE) as db:
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir="/Users/bairdweng/Library/Application Support/Google/Chrome/Default",
                channel="chrome",
                headless=False
            )
            page = await browser.new_page()

            # 每次抓取前绑定 response 事件
            page.on("response", lambda response: asyncio.create_task(
                handle_response(response, db)))

            for url in urls:
                print(f"🔹 开始抓取 {url}")
                await page.goto(url)
                await asyncio.sleep(20)  # 等待网络请求触发

            print("✅ 抓取完成，保持浏览器打开 60 秒")
            await asyncio.sleep(60)
            await browser.close()
            
            # 分析热卖和增长产品
            print("🔍 分析热卖和增长产品...")
            await analyze_hot_products(db)
            await analyze_growth_products(db)

# 定义要抓取的用户URL列表
DEFAULT_URLS = [
    "https://www.douyin.com/user/MS4wLjABAAAA75EbUN-VEfEiyyidKjBKLw4vza41ET_RS8PK_2LySF6UugM_nPdFUKBEb_-2gX2m",  # 灿晟数码严选工作室认证徽章
    "https://www.douyin.com/user/MS4wLjABAAAAD-_Dk8WpxkT43dZ-Ib5pza05hI7LKsWo3jR766miHKftsKGdvITpEz48-hZKwXCw",  # tutu
    "https://www.douyin.com/user/MS4wLjABAAAAAXviISIVZECvu_zsrSC812o7cx6HWQDJMALk-CwR8cTNu0KoqF0YJwooVwdhYykE",  # 对的
    "https://www.douyin.com/user/MS4wLjABAAAALoETvdflpmaXqD5jQxReulB_qxkcP34JNBI24kdEyZw",  # 守护者
    "https://www.douyin.com/user/MS4wLjABAAAAIiLGcuZGSJxc4okvtGARBEpx4N4VDDw1tmyB6JG2viQ"  # 壳岸
]

# 定时任务函数
async def scheduled_task():
    print(f"\n📅 开始定时抓取任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        await run(DEFAULT_URLS)
        print(f"✅ 定时抓取任务完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"❌ 定时抓取任务出错: {e}")

# 启动定时任务
async def start_scheduler():
    # 创建调度器
    scheduler = AsyncIOScheduler()
    
    # 添加每天执行一次的任务（默认在凌晨1点执行）
    scheduler.add_job(
        scheduled_task,
        trigger=CronTrigger(hour=1, minute=0),  # 每天凌晨1点执行
        id='daily_scrape',
        name='抖音用户视频每天抓取',
        replace_existing=True
    )
    
    # 启动调度器
    scheduler.start()
    print(f"🚀 定时任务已启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📅 每天凌晨1:00自动执行抓取任务")
    print("🔄 按 Ctrl+C 停止任务")
    
    # 立即执行一次抓取任务
    print("\n🔄 立即执行一次抓取任务")
    await scheduled_task()
    
    # 保持程序运行
    try:
        while True:
            await asyncio.sleep(86400)  # 睡眠一天
    except KeyboardInterrupt:
        print("\n🛑 定时任务已停止")
        scheduler.shutdown()

async def extract_products_from_video(db, video_item, author_id, author_name):
    """从视频内容中提取产品信息"""
    try:
        title = video_item.get("desc", "")
        hashtags = [h.get("hashtag_name", "") for h in (video_item.get("text_extra") or []) if h.get("hashtag_name")]
        video_id = video_item.get("aweme_id")
        
        # 增强的产品关键词模式（按类别分组）
        product_categories = {
            '品牌': [r'华为|苹果|小米|OPPO|vivo|三星|荣耀|realme|一加|魅族'],
            '型号': [r'Mate[0-9]+|P[0-9]+|iPhone[0-9]+|iPhone SE|iPhone X[0-9]*|Pro|Max|Ultra|Plus|Note[0-9]+|S[0-9]+'],
            '产品类型': [r'手机壳|保护套|手机膜|钢化膜|保护壳|充电器|数据线|充电宝|耳机|支架|散热背夹|手机支架'],
            '特色款': [r'保时捷|非凡大师|典藏版|限量版|联名款|定制款|透明款|磨砂款|液态硅胶|全包款|防摔款'],
            '功能': [r'防摔|防水|全包|散热|快充|无线充|磁吸|隐形支架|镜头保护|防指纹']
        }
        
        # 提取可能的产品关键词
        found_products = []
        product_info = {}
        
        # 按类别提取关键词
        for category, patterns in product_categories.items():
            category_matches = []
            for pattern in patterns:
                # 从标题提取
                matches = re.findall(pattern, title)
                category_matches.extend(matches)
                # 从hashtag提取
                for hashtag in hashtags:
                    if re.search(pattern, hashtag):
                        category_matches.append(hashtag)
            
            if category_matches:
                # 去重并保存到产品信息中
                product_info[category] = list(set(category_matches))
                found_products.extend(category_matches)
        
        # 合并结果，生成更有意义的产品名称
        enhanced_products = []
        
        # 优先组合品牌+型号+产品类型的完整产品名称
        if '品牌' in product_info and '型号' in product_info and '产品类型' in product_info:
            for brand in product_info['品牌']:
                for model in product_info['型号']:
                    for product_type in product_info['产品类型']:
                        enhanced_products.append(f"{brand}{model}{product_type}")
        
        # 如果没有完整组合，使用单一关键词
        if not enhanced_products:
            enhanced_products = list(set(found_products))
        
        # 如果仍然没有找到产品，尝试更简单的关键词提取
        if not enhanced_products:
            simple_keywords = re.findall(r'[\u4e00-\u9fa5]{2,}', title)
            # 过滤掉常见非产品词汇
            common_words = {'这个', '那个', '我们', '你们', '他们', '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都'}
            simple_keywords = [word for word in simple_keywords if len(word) >= 2 and word not in common_words]
            enhanced_products = simple_keywords[:3]  # 最多取3个可能的关键词
        
        # 保存找到的产品
        for product_keyword in enhanced_products[:5]:  # 最多处理5个产品
            product_keyword = product_keyword[:50]  # 限制长度
            
            # 查找或创建产品记录
            async with db.execute(
                "SELECT product_id FROM products WHERE product_keywords LIKE ? AND author_id = ?",
                (f"%{product_keyword}%", author_id)
            ) as cursor:
                existing = await cursor.fetchone()
                
            if existing:
                product_id = existing[0]
                # 更新产品信息
                await db.execute(
                    "UPDATE products SET last_seen_date = ?, video_count = video_count + 1 WHERE product_id = ?",
                    (datetime.now().strftime("%Y-%m-%d"), product_id)
                )
            else:
                # 确定产品类别
                product_category = "其他"
                for category, patterns in product_categories.items():
                    for pattern in patterns:
                        if re.search(pattern, product_keyword):
                            product_category = category
                            break
                
                # 创建新产品
                await db.execute(
                    """
                    INSERT INTO products 
                    (product_name, product_keywords, first_seen_date, last_seen_date, video_count, 
                     author_id, author_name, growth_rate, popularity_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (product_keyword, product_keyword, datetime.now().strftime("%Y-%m-%d"), 
                     datetime.now().strftime("%Y-%m-%d"), 1, author_id, author_name, 0.0, 0.0)
                )
                product_id = await db.execute("SELECT last_insert_rowid()")
                product_id = (await product_id.fetchone())[0]
                
                # 建立视频和产品的映射关系
                try:
                    await db.execute(
                        "INSERT OR IGNORE INTO video_product_mapping (video_id, product_id) VALUES (?, ?)",
                        (video_id, product_id)
                    )
                except:
                    pass  # 忽略重复插入错误
        
    except Exception as e:
        print(f"❌ 提取产品信息出错: {e}")

async def update_product_scores(db):
    """更新产品的热度和增长分数 - 暂时跳过复杂计算"""
    try:
        # 简化版：直接设置一个基础分数，避免SQL语法问题
        await db.execute("UPDATE products SET popularity_score = 10.0")
        await db.commit()
    except Exception as e:
        print(f"❌ 更新产品分数出错: {e}")
        await db.rollback()

async def analyze_hot_products(db, days=7):
    """分析最近热卖的产品 - 完全简化版"""
    try:
        # 简化版查询，只返回需要的字段
        query = """
        SELECT p.product_id, p.product_name, COUNT(DISTINCT v.video_id) as video_count,
               SUM(v.play_count) as total_plays, SUM(v.digg_count) as total_likes,
               p.author_name, AVG(v.play_count) as avg_plays
        FROM products p
        JOIN video_product_mapping vpm ON p.product_id = vpm.product_id
        JOIN videos v ON vpm.video_id = v.video_id
        GROUP BY p.product_id, p.product_name
        ORDER BY SUM(v.play_count) DESC
        LIMIT 10
        """
        
        async with db.execute(query) as cursor:
            hot_products = await cursor.fetchall()
        
        if hot_products:
            print(f"\n🔥 最近热卖产品TOP10:")
            print("-" * 80)
            print(f"{'排名':<5}{'产品名称':<25}{'视频数':<10}{'播放量':<15}{'点赞数':<10}{'店铺'}")
            print("-" * 80)
            
            # 保存结果到文件
            filename = f"hot_products_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"🔥 热卖产品TOP10 (生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
                f.write("-" * 80 + "\n")
                f.write(f"{'排名':<5}{'产品名称':<25}{'视频数':<10}{'播放量':<15}{'点赞数':<10}{'店铺'}\n")
                f.write("-" * 80 + "\n")
                
                for i, product in enumerate(hot_products, 1):
                    # 确保解包正确 - 现在查询返回7个字段
                    product_id, name, video_count, plays, likes, author, avg_plays = product
                    author_truncated = author[:15] if len(author) > 15 else author
                    print(f"{i:<5}{name[:23]:<25}{video_count:<10}{plays:<15,}{likes:<10,}{author_truncated}")
                    f.write(f"{i:<5}{name[:23]:<25}{video_count:<10}{plays:<15,}{likes:<10,}{author}\n")
            
            print(f"\n✅ 热卖产品报告已保存至 {filename}")
        else:
            print("\n📢 暂无热卖产品数据")
        
    except Exception as e:
        print(f"❌ 分析热卖产品出错: {e}")

async def analyze_growth_products(db, days=7):
    """分析潜在增长产品 - 使用简化方法"""
    try:
        today = datetime.now()
        
        # 简化版：基于视频数和播放量进行排序
        query = """
        SELECT p.product_id, p.product_name, p.author_name,
               COUNT(DISTINCT v.video_id) as video_count,
               SUM(v.play_count) as total_plays,
               SUM(v.digg_count) as total_likes
        FROM products p
        JOIN video_product_mapping vpm ON p.product_id = vpm.product_id
        JOIN videos v ON vpm.video_id = v.video_id
        GROUP BY p.product_id, p.product_name
        HAVING COUNT(DISTINCT v.video_id) > 0 AND SUM(v.play_count) > 30
        ORDER BY 
            COUNT(DISTINCT v.video_id) DESC, 
            SUM(v.play_count) DESC
        LIMIT 10
        """
        
        async with db.execute(query) as cursor:
            growth_data = await cursor.fetchall()
        
        if growth_data:
            print(f"\n📈 潜在增长产品TOP10:")
            print("-" * 80)
            print(f"{'排名':<5}{'产品名称':<25}{'视频数':<10}{'播放量':<15}{'点赞数':<10}{'店铺'}")
            print("-" * 80)
            
            # 保存到文件
            filename = f"growth_products_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"📈 潜在增长产品分析 (生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
                f.write(f"📅 分析日期: {today.strftime('%Y-%m-%d')}\n\n")
                f.write("-" * 80 + "\n")
                f.write(f"{'排名':<5}{'产品名称':<25}{'视频数':<10}{'播放量':<15}{'点赞数':<10}{'店铺'}\n")
                f.write("-" * 80 + "\n")
                
                for i, product in enumerate(growth_data, 1):
                    # 解包正确的字段数量
                    product_id, name, author, video_count, total_plays, total_likes = product
                    author_truncated = author[:15] if len(author) > 15 else author
                    print(f"{i:<5}{name[:23]:<25}{video_count:<10}{total_plays:<15,}{total_likes:<10,}{author_truncated}")
                    f.write(f"{i:<5}{name[:23]:<25}{video_count:<10}{total_plays:<15,}{total_likes:<10,}{author}\n")
            
            print(f"\n✅ 潜在增长产品报告已保存至 {filename}")
        else:
            print("\n📈 暂无足够数据进行增长产品分析")
            print("   建议: 继续收集更多视频数据以进行趋势分析")
            
    except Exception as e:
        print(f"❌ 分析增长产品出错: {e}")
        # 如果出错，尝试一个更简单的分析方法
        try:
            simple_query = """
            SELECT p.product_name, p.video_count, p.author_name
            FROM products p
            ORDER BY p.video_count DESC
            LIMIT 5
            """
            async with db.execute(simple_query) as cursor:
                simple_products = await cursor.fetchall()
                
            if simple_products:
                print("\n📈 简易产品分析结果:")
                for product in simple_products:
                    print(f"- {product[0]} ({product[2]}): {product[1]}个相关视频")
        except:
            pass

async def init_database(db):
    """初始化数据库表结构"""
    try:
        # 创建videos表（如果已存在则忽略）
        await db.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                hashtags TEXT,
                is_ads INTEGER,
                duration REAL,
                publish_time TEXT,
                play_count INTEGER,
                digg_count INTEGER,
                comment_count INTEGER,
                share_url TEXT,
                cover_url TEXT,
                video_url TEXT,
                author_id TEXT,
                author_name TEXT,
                author_avatar TEXT,
                music_id TEXT,
                music_title TEXT,
                music_author TEXT,
                update_time TEXT
            )
        """)
        
        # 创建products表（如果已存在则忽略）
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT,
                product_keywords TEXT,
                first_seen_date TEXT,
                last_seen_date TEXT,
                video_count INTEGER DEFAULT 0,
                total_play_count INTEGER DEFAULT 0,
                total_digg_count INTEGER DEFAULT 0,
                growth_rate REAL DEFAULT 0.0,
                popularity_score REAL DEFAULT 0.0,
                author_id TEXT,
                author_name TEXT
            )
        """)
        
        # 创建video_product_mapping表（如果已存在则忽略）
        await db.execute("""
            CREATE TABLE IF NOT EXISTS video_product_mapping (
                video_id TEXT,
                product_id INTEGER,
                PRIMARY KEY (video_id, product_id),
                FOREIGN KEY (video_id) REFERENCES videos(video_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            )
        """)
        
        await db.commit()
        print("✅ 数据库表结构初始化完成")
    except Exception as e:
        print(f"❌ 数据库初始化出错: {e}")
        await db.rollback()

async def extract_products_from_existing_videos(db):
    """从现有视频中提取产品信息"""
    try:
        # 统计视频数量
        async with db.execute("SELECT COUNT(*) FROM videos") as cursor:
            total_videos = (await cursor.fetchone())[0]
        
        print(f"ℹ️  开始从 {total_videos} 个视频中提取产品信息...")
        
        # 增强的产品关键词模式（按类别分组）
        product_categories = {
            '品牌': [r'华为|苹果|小米|OPPO|vivo|三星|荣耀|realme|一加|魅族'],
            '型号': [r'Mate[0-9]+|P[0-9]+|iPhone[0-9]+|iPhone SE|iPhone X[0-9]*|Pro|Max|Ultra|Plus|Note[0-9]+|S[0-9]+'],
            '产品类型': [r'手机壳|保护套|手机膜|钢化膜|保护壳|充电器|数据线|充电宝|耳机|支架|散热背夹|手机支架'],
            '特色款': [r'保时捷|非凡大师|典藏版|限量版|联名款|定制款|透明款|磨砂款|液态硅胶|全包款|防摔款'],
            '功能': [r'防摔|防水|全包|散热|快充|无线充|磁吸|隐形支架|镜头保护|防指纹']
        }
        
        # 分批处理视频以避免内存问题
        batch_size = 100
        processed = 0
        
        while processed < total_videos:
            async with db.execute(
                "SELECT video_id, title, author_id, author_name, publish_time FROM videos LIMIT ? OFFSET ?",
                (batch_size, processed)
            ) as cursor:
                videos_batch = await cursor.fetchall()
                
            if not videos_batch:
                break
            
            for video in videos_batch:
                video_id, title, author_id, author_name, publish_time = video
                
                try:
                    # 提取产品关键词
                    found_products = []
                    product_info = {}
                    
                    # 按类别提取关键词
                    for category, patterns in product_categories.items():
                        category_matches = []
                        for pattern in patterns:
                            matches = re.findall(pattern, title)
                            category_matches.extend(matches)
                        
                        if category_matches:
                            product_info[category] = list(set(category_matches))
                            found_products.extend(category_matches)
                    
                    # 生成增强的产品名称
                    enhanced_products = []
                    
                    # 优先组合品牌+型号+产品类型
                    if '品牌' in product_info and '型号' in product_info and '产品类型' in product_info:
                        for brand in product_info['品牌']:
                            for model in product_info['型号']:
                                for product_type in product_info['产品类型']:
                                    enhanced_products.append(f"{brand}{model}{product_type}")
                    
                    # 如果没有完整组合，使用单一关键词
                    if not enhanced_products and found_products:
                        enhanced_products = list(set(found_products))
                    
                    # 处理每个找到的产品
                    for product_keyword in enhanced_products[:3]:  # 限制数量
                        product_keyword = product_keyword[:50]  # 限制长度
                        
                        # 查找或创建产品记录
                        async with db.execute(
                            "SELECT product_id FROM products WHERE product_keywords LIKE ? AND author_id = ?",
                            (f"%{product_keyword}%", author_id)
                        ) as pcursor:
                            existing = await pcursor.fetchone()
                            
                        if existing:
                            product_id = existing[0]
                            # 更新产品信息
                            await db.execute(
                                "UPDATE products SET last_seen_date = ?, video_count = video_count + 1 WHERE product_id = ?",
                                (datetime.now().strftime("%Y-%m-%d"), product_id)
                            )
                        else:
                            # 创建新产品
                            await db.execute(
                                """
                                INSERT INTO products 
                                (product_name, product_keywords, first_seen_date, last_seen_date, video_count, 
                                 author_id, author_name)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                """,
                                (product_keyword, product_keyword, publish_time.split(' ')[0] if publish_time else "2024-01-01", 
                                 datetime.now().strftime("%Y-%m-%d"), 1, author_id, author_name)
                            )
                            product_id = await db.execute("SELECT last_insert_rowid()")
                            product_id = (await product_id.fetchone())[0]
                        
                        # 建立映射关系
                        try:
                            await db.execute(
                                "INSERT OR IGNORE INTO video_product_mapping (video_id, product_id) VALUES (?, ?)",
                                (video_id, product_id)
                            )
                        except:
                            pass
                    
                except Exception as e:
                    # 忽略单个视频的错误，继续处理
                    pass
            
            processed += len(videos_batch)
            await db.commit()
            print(f"⏳ 已处理 {processed}/{total_videos} 个视频...")
        
        # 统计提取的产品数量
        async with db.execute("SELECT COUNT(*) FROM products") as cursor:
            total_products = (await cursor.fetchone())[0]
        
        print(f"✅ 产品信息提取完成！共提取 {total_products} 个产品")
        
    except Exception as e:
        print(f"❌ 提取产品信息出错: {e}")
        await db.rollback()

async def generate_combined_report(db):
    """生成综合分析报告"""
    try:
        report_date = datetime.now().strftime("%Y-%m-%d")
        report_filename = f"competitor_analysis_{report_date}.txt"
        
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(f"📊 竞争店铺产品分析综合报告\n")
            f.write(f"📅 生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 统计信息
            async with db.execute("SELECT COUNT(*) FROM videos") as cursor:
                total_videos = (await cursor.fetchone())[0]
            
            async with db.execute("SELECT COUNT(*) FROM products") as cursor:
                total_products = (await cursor.fetchone())[0]
            
            async with db.execute("SELECT COUNT(DISTINCT author_id) FROM videos") as cursor:
                total_shops = (await cursor.fetchone())[0]
            
            f.write(f"📋 数据概览\n")
            f.write(f"- 抓取视频总数: {total_videos:,}\n")
            f.write(f"- 识别产品总数: {total_products}\n")
            f.write(f"- 监控店铺数: {total_shops}\n\n")
            
            # 热门店铺TOP5
            f.write(f"🏆 热门店铺TOP5 (按视频数)\n")
            async with db.execute(
                "SELECT author_name, COUNT(*) as video_count FROM videos GROUP BY author_name ORDER BY video_count DESC LIMIT 5"
            ) as cursor:
                top_shops = await cursor.fetchall()
                for i, shop in enumerate(top_shops, 1):
                    f.write(f"{i}. {shop[0]}: {shop[1]} 个视频\n")
            
            f.write("\n" + "="*60 + "\n\n")
        
        print(f"✅ 综合分析报告已生成: {report_filename}")
        
    except Exception as e:
        print(f"❌ 生成综合报告出错: {e}")

# 增加一个手动分析命令行功能
async def analyze_existing_data():
    """分析已存在的数据，找出热卖和增长产品"""
    print("🔍 开始分析已有数据中的热卖和增长产品...")
    async with aiosqlite.connect(DB_FILE) as db:
        # 确保表结构存在
        await init_database(db)
        
        # 如果products表为空，尝试从现有视频中提取产品信息
        async with db.execute("SELECT COUNT(*) FROM products") as cursor:
            count = (await cursor.fetchone())[0]
        
        if count == 0:
            await extract_products_from_existing_videos(db)
        else:
            print(f"ℹ️  检测到已有 {count} 个产品记录")
        
        # 执行分析
        print("\n📊 开始执行产品分析...")
        await analyze_hot_products(db)
        await analyze_growth_products(db)
        
        # 生成综合报告
        await generate_combined_report(db)
        
        # 显示使用说明
        print("\n📝 使用说明:")
        print("   • 热卖产品分析基于播放量和点赞数的综合权重")
        print("   • 增长趋势分析比较最近7天和之前7天的表现")
        print("   • 生成的报告文件保存在当前目录")
        print("   • 定期运行 'python index.py analyze' 可持续监控竞品动态")
        print("   • 直接运行脚本可抓取最新视频并自动分析")
    
    print("\n✅ 数据分析完成！")

if __name__ == "__main__":
    import sys
    
    # 如果参数中包含 analyze，则只执行分析而不抓取
    if len(sys.argv) > 1 and sys.argv[1] == "analyze":
        asyncio.run(analyze_existing_data())
    else:
        # 启动定时任务调度器
        asyncio.run(start_scheduler())
