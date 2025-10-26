import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# 连接数据库
conn = sqlite3.connect("aweme_full.db")
df = pd.read_sql_query("SELECT * FROM videos ORDER BY publish_time DESC", conn)

st.title("抖音账号作品管理 — 最近作品总览")

# 转换 publish_time 为 datetime
df["publish_time_dt"] = pd.to_datetime(df["publish_time"], errors='coerce')

# 作者筛选（多选）
# 作者筛选（多选），默认不选中任何作者
all_authors = sorted(df["author_name"].dropna().unique())
author_filter = st.multiselect("选择作者", all_authors, default=[])
if author_filter:
    df = df[df["author_name"].isin(author_filter)]
# 最近天数筛选
days_option = st.selectbox(
    "选择最近天数", ["全部时间", "1天", "2天", "3天", "自定义日期范围"], index=1)

if days_option == "全部时间":
    df_filtered = df.copy()
elif days_option != "自定义日期范围":
    days_num = int(days_option.replace("天", ""))
    now = pd.Timestamp.now()
    start_time = now - pd.Timedelta(days=days_num)
    df_filtered = df[df["publish_time_dt"] >= start_time]
else:
    start_date = st.date_input("开始日期", datetime.now() - timedelta(days=3))
    end_date = st.date_input("结束日期", datetime.now())
    df_filtered = df[(df["publish_time_dt"] >= pd.to_datetime(start_date)) &
                     (df["publish_time_dt"] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))]

# 按作者分组显示
authors_grouped = df_filtered.groupby("author_name")

for author, group in authors_grouped:
    st.markdown(f"## 作者: {author} （选定时间内发布 {len(group)} 条视频）")

    for _, row in group.iterrows():
        # 使用列布局，紧凑显示
        cols = st.columns([1, 3])
        with cols[0]:
            if row["cover_url"]:
                # 点击图片查看大图
                st.markdown(f"[![封面]({row['cover_url']})]({row['cover_url']})")
        with cols[1]:
            st.markdown(f"**发布时间:** {row['publish_time']}")
            st.markdown(f"**标题:** {row['title']}")
            st.markdown(f"**标签:** {row['hashtags']}")
            st.markdown(
                f"**播放/点赞/评论:** {row['play_count']}/{row['digg_count']}/{row['comment_count']}")
            if row["share_url"]:
                st.markdown(f"[点击观看视频]({row['share_url']})")
        st.markdown("---")
