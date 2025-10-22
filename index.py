import asyncio
import aiosqlite
from datetime import datetime
from playwright.async_api import async_playwright

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
            music_author TEXT
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
                        INSERT INTO videos (
                            video_id, title, hashtags, is_ads, duration, publish_time,
                            play_count, digg_count, comment_count, share_url, cover_url,
                            video_url, author_id, author_name, author_avatar,
                            music_id, music_title, music_author
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        video_id, desc, hashtags_str, is_ads, duration, publish_time,
                        play_count, digg_count, comment_count, share_url, cover_url,
                        video_url, author_id, author_name, author_avatar,
                        music_id, music_title, music_author
                    ))
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

if __name__ == "__main__":
    urls = [
        "https://www.douyin.com/user/MS4wLjABAAAA75EbUN-VEfEiyyidKjBKLw4vza41ET_RS8PK_2LySF6UugM_nPdFUKBEb_-2gX2m",  # 灿晟数码严选工作室认证徽章
        "https://www.douyin.com/user/MS4wLjABAAAAD-_Dk8WpxkT43dZ-Ib5pza05hI7LKsWo3jR766miHKftsKGdvITpEz48-hZKwXCw",  # tutu
        "https://www.douyin.com/user/MS4wLjABAAAAAXviISIVZECvu_zsrSC812o7cx6HWQDJMALk-CwR8cTNu0KoqF0YJwooVwdhYykE",  # 对的
        "https://www.douyin.com/user/MS4wLjABAAAALoETvdflpmaXqD5jQxReulB_qxkcP34JNBI24kdEyZw",  # 守护者
        "https://www.douyin.com/user/MS4wLjABAAAAIiLGcuZGSJxc4okvtGARBEpx4N4VDDw1tmyB6JG2viQ"  # 壳岸
    ]
    asyncio.run(run(urls))
