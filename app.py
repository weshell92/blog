import streamlit as st
import yaml
from pathlib import Path
from datetime import datetime

# ── 页面配置 ──────────────────────────────────────────
st.set_page_config(
    page_title="我的成长日志",
    page_icon="🌱",
    layout="wide",
)

POSTS_DIR = Path("posts")
CATEGORIES = ["全部", "读书笔记", "技术感悟", "复盘", "生活随想"]
START_DATE = datetime(2026, 5, 31).date()


# ── 工具函数 ──────────────────────────────────────────
def parse_post(filepath: Path) -> dict:
    """解析 Markdown 文章的 YAML 头信息和正文"""
    content = filepath.read_text(encoding="utf-8")
    if content.startswith("---"):
        parts = content.split("---", 2)
        meta = yaml.safe_load(parts[1])
        body = parts[2].strip()
    else:
        meta = {"title": filepath.stem, "date": datetime.today().date()}
        body = content
    meta["body"] = body
    meta["filepath"] = filepath
    meta.setdefault("tags", [])
    meta.setdefault("summary", "")
    meta.setdefault("category", filepath.parent.name)
    return meta


@st.cache_data(ttl=60)
def load_all_posts() -> list:
    """加载所有文章，按日期倒序排列"""
    posts = []
    if not POSTS_DIR.exists():
        return posts
    for md_file in POSTS_DIR.rglob("*.md"):
        try:
            posts.append(parse_post(md_file))
        except Exception:
            pass
    return sorted(posts, key=lambda x: str(x.get("date", "")), reverse=True)


# ── 侧边栏 ────────────────────────────────────────────
with st.sidebar:
    st.title("🌱 我的成长日志")
    st.markdown("*每天记录，复利生长*")
    st.divider()

    selected_category = st.radio("📂 分类", CATEGORIES)
    st.divider()

    search_query = st.text_input("🔍 搜索文章", placeholder="输入关键词...")
    st.divider()

    # 统计信息
    all_posts = load_all_posts()
    days_kept = (datetime.today().date() - START_DATE).days + 1
    st.metric("📝 累计文章", len(all_posts))
    st.metric("📅 坚持天数", max(days_kept, 1))


# ── 主内容区 ──────────────────────────────────────────
# 过滤逻辑
filtered = all_posts
if selected_category != "全部":
    filtered = [p for p in filtered if p.get("category") == selected_category]
if search_query:
    q = search_query.lower()
    filtered = [
        p for p in filtered
        if q in p.get("title", "").lower() or q in p.get("body", "").lower()
    ]

# 初始化 session state
if "selected_post" not in st.session_state:
    st.session_state.selected_post = None


if st.session_state.selected_post is None:
    # ── 文章列表页 ──
    title_map = {
        "全部": "🏠 所有文章",
        "读书笔记": "📖 读书笔记",
        "技术感悟": "💡 技术感悟",
        "复盘": "🔁 复盘",
        "生活随想": "🌿 生活随想",
    }
    st.title(title_map.get(selected_category, selected_category))
    st.caption(f"共 {len(filtered)} 篇")
    st.divider()

    if not filtered:
        st.info("暂无文章，快去写第一篇吧！✍️")
    else:
        for post in filtered:
            with st.container(border=True):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"### {post['title']}")
                    if post.get("summary"):
                        st.caption(post["summary"])
                    if post.get("tags"):
                        tags_str = " ".join([f"`{t}`" for t in post["tags"]])
                        st.markdown(tags_str)
                with col2:
                    st.caption(str(post.get("date", ""))[:10])
                    st.caption(f"📂 {post.get('category', '')}")
                    if st.button("阅读 →", key=str(post["filepath"])):
                        st.session_state.selected_post = post
                        st.rerun()
else:
    # ── 文章详情页 ──
    post = st.session_state.selected_post
    if st.button("← 返回列表"):
        st.session_state.selected_post = None
        st.rerun()

    st.title(post["title"])
    col1, col2, col3 = st.columns(3)
    col1.caption(f"📅 {str(post.get('date', ''))[:10]}")
    col2.caption(f"📂 {post.get('category', '')}")
    col3.caption(f"🏷 {' / '.join(post.get('tags', []))}")
    st.divider()
    st.markdown(post["body"])
