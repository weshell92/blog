import streamlit as st
import yaml
import requests
import base64
from pathlib import Path
from datetime import datetime

# ── 页面配置 ──────────────────────────────────────────
st.set_page_config(
    page_title="我的成长日志",
    page_icon="🌱",
    layout="wide",
)

POSTS_DIR = Path("posts")
CATEGORIES_LIST = ["读书笔记", "技术感悟", "复盘", "生活随想"]
CATEGORIES_ALL = ["全部"] + CATEGORIES_LIST
START_DATE = datetime(2026, 5, 31).date()
GITHUB_REPO = "weshell92/blog"


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


def publish_post(title, category, tags, summary, body) -> tuple[bool, str]:
    """通过 GitHub API 将新文章提交到仓库"""
    try:
        token = st.secrets["GITHUB_TOKEN"]
    except Exception:
        return False, "请在 Streamlit Secrets 中配置 GITHUB_TOKEN"

    today = datetime.today().strftime("%Y-%m-%d")

    # 构建 YAML front matter
    front_matter = {
        "title": title,
        "date": today,
        "category": category,
        "tags": tags,
        "summary": summary,
    }
    file_content = (
        "---\n"
        + yaml.dump(front_matter, allow_unicode=True, default_flow_style=False)
        + "---\n\n"
        + body
    )

    # 生成安全文件名
    safe_title = "".join(c if c.isalnum() or c in "-_\u4e00-\u9fff" else "-" for c in title)[:40]
    filename = f"{today}-{safe_title}.md"
    path = f"posts/{category}/{filename}"

    # 调用 GitHub Contents API
    encoded = base64.b64encode(file_content.encode("utf-8")).decode()
    resp = requests.put(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "message": f"新增文章：{title}",
            "content": encoded,
            "branch": "main",
        },
        timeout=10,
    )

    if resp.status_code in (200, 201):
        return True, path
    else:
        msg = resp.json().get("message", "未知错误")
        return False, f"GitHub API 错误：{msg}"


# ── 侧边栏 ────────────────────────────────────────────
with st.sidebar:
    st.title("🌱 我的成长日志")
    st.markdown("*每天记录，复利生长*")
    st.divider()

    page = st.radio("", ["📖 阅读", "✍️ 写文章"], label_visibility="collapsed")
    st.divider()

    all_posts = load_all_posts()
    days_kept = (datetime.today().date() - START_DATE).days + 1
    st.metric("📝 累计文章", len(all_posts))
    st.metric("📅 坚持天数", max(days_kept, 1))


# ── 写文章页 ──────────────────────────────────────────
if page == "✍️ 写文章":
    st.title("✍️ 写新文章")
    st.caption("写完点击发布，文章会自动保存到仓库，博客稍后自动刷新 ✅")
    st.divider()

    with st.form("new_post_form", clear_on_submit=True):
        title = st.text_input("📌 标题 *", placeholder="今天想写什么？")

        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("📂 分类 *", CATEGORIES_LIST)
        with col2:
            tags_input = st.text_input("🏷 标签", placeholder="用逗号分隔，如：Python, 读书")

        summary = st.text_input("💬 摘要", placeholder="一句话简介（可选，会显示在列表页）")

        body = st.text_area(
            "📝 正文（支持 Markdown）",
            height=450,
            placeholder="## 开始写作...\n\n支持 **加粗**、*斜体*、`代码`、列表等 Markdown 语法。",
        )

        submitted = st.form_submit_button("🚀 发布文章", type="primary", use_container_width=True)

    if submitted:
        if not title.strip():
            st.error("❌ 标题不能为空")
        elif not body.strip():
            st.error("❌ 正文不能为空")
        else:
            tags = [t.strip() for t in tags_input.split(",") if t.strip()]
            with st.spinner("正在发布..."):
                ok, result = publish_post(title.strip(), category, tags, summary.strip(), body.strip())
            if ok:
                st.success(f"🎉 发布成功！文章已保存到 `{result}`")
                st.info("⏳ 博客将在 1~2 分钟内自动更新，请稍候刷新页面。")
                st.balloons()
            else:
                st.error(result)

    # Markdown 参考
    with st.expander("📎 Markdown 速查"):
        st.markdown("""
| 语法 | 效果 |
|------|------|
| `**文字**` | **加粗** |
| `*文字*` | *斜体* |
| `## 标题` | 二级标题 |
| `` `代码` `` | `行内代码` |
| `> 引用` | 引用块 |
| `- 列表项` | 无序列表 |
| `1. 列表项` | 有序列表 |
        """)


# ── 阅读页 ────────────────────────────────────────────
elif page == "📖 阅读":
    # 分类和搜索过滤
    col_f1, col_f2 = st.columns([2, 3])
    with col_f1:
        selected_category = st.radio("分类", CATEGORIES_ALL, horizontal=True, label_visibility="collapsed")
    with col_f2:
        search_query = st.text_input("🔍 搜索文章", placeholder="输入关键词...", label_visibility="collapsed")

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
        # ── 文章列表 ──
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
            st.info("暂无文章，去左边点「✍️ 写文章」写第一篇吧！")
        else:
            for post in filtered:
                with st.container(border=True):
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.markdown(f"### {post['title']}")
                        if post.get("summary"):
                            st.caption(post["summary"])
                        if post.get("tags"):
                            st.markdown(" ".join([f"`{t}`" for t in post["tags"]]))
                    with col2:
                        st.caption(str(post.get("date", ""))[:10])
                        st.caption(f"📂 {post.get('category', '')}")
                        if st.button("阅读 →", key=str(post["filepath"])):
                            st.session_state.selected_post = post
                            st.rerun()
    else:
        # ── 文章详情 ──
        post = st.session_state.selected_post
        if st.button("← 返回列表"):
            st.session_state.selected_post = None
            st.rerun()

        st.title(post["title"])
        c1, c2, c3 = st.columns(3)
        c1.caption(f"📅 {str(post.get('date', ''))[:10]}")
        c2.caption(f"📂 {post.get('category', '')}")
        c3.caption(f"🏷 {' / '.join(post.get('tags', []))}")
        st.divider()
        st.markdown(post["body"])
