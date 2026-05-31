import streamlit as st
import psycopg
import socket
from psycopg.rows import dict_row
from datetime import datetime
from urllib.parse import urlparse, quote

# ── 页面配置 ──────────────────────────────────────────
st.set_page_config(
    page_title="我的成长日志",
    page_icon="🌱",
    layout="wide",
)

CATEGORIES_LIST = ["读书笔记", "技术感悟", "复盘", "生活随想"]
CATEGORIES_ALL  = ["全部"] + CATEGORIES_LIST
START_DATE = datetime(2026, 5, 31).date()


# ── 数据库连接 ────────────────────────────────────────
def make_conn_str() -> str:
    """
    解析 DATABASE_URL，强制将域名解析为 IPv4 地址，
    避免 Streamlit Cloud 不支持 IPv6 的问题。
    """
    raw = st.secrets["DATABASE_URL"]
    parsed = urlparse(raw)

    username = quote(parsed.username or "", safe="")
    password = quote(parsed.password or "", safe="")
    host     = parsed.hostname
    dbname   = (parsed.path or "/postgres").lstrip("/") or "postgres"

    # 强制解析为 IPv4
    try:
        ipv4 = socket.getaddrinfo(host, None, socket.AF_INET)[0][4][0]
    except socket.gaierror:
        ipv4 = host  # 解析失败则用原始 host

    # 使用直连端口 5432（IPv4 下直连比 PgBouncer 更稳定）
    return f"postgresql://{username}:{password}@{ipv4}:5432/{dbname}?sslmode=require"


def get_conn():
    return psycopg.connect(make_conn_str(), row_factory=dict_row)


def run(sql, params=None, fetch=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            conn.commit()
            if fetch == "one":
                return cur.fetchone()
            if fetch == "all":
                return cur.fetchall()
            return cur.rowcount


def init_db():
    run("""
        CREATE TABLE IF NOT EXISTS posts (
            id          SERIAL PRIMARY KEY,
            title       TEXT      NOT NULL,
            category    TEXT      NOT NULL,
            tags        TEXT      DEFAULT '',
            summary     TEXT      DEFAULT '',
            body        TEXT      NOT NULL,
            created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)


# ── CRUD ──────────────────────────────────────────────
def insert_post(title, category, tags, summary, body) -> int:
    now = datetime.now()
    row = run(
        "INSERT INTO posts (title, category, tags, summary, body, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (title, category, tags, summary, body, now, now),
        fetch="one",
    )
    return row["id"]


def update_post(post_id, title, category, tags, summary, body):
    run(
        "UPDATE posts SET title=%s, category=%s, tags=%s, "
        "summary=%s, body=%s, updated_at=%s WHERE id=%s",
        (title, category, tags, summary, body, datetime.now(), post_id),
    )


def get_all_posts(category=None, keyword=None) -> list:
    sql = "SELECT * FROM posts WHERE 1=1"
    params = []
    if category and category != "全部":
        sql += " AND category = %s"
        params.append(category)
    if keyword:
        sql += " AND (title ILIKE %s OR body ILIKE %s)"
        params += [f"%{keyword}%", f"%{keyword}%"]
    sql += " ORDER BY created_at DESC"
    return run(sql, params, fetch="all") or []


def get_post(post_id) -> dict | None:
    return run("SELECT * FROM posts WHERE id=%s", (post_id,), fetch="one")


def count_posts() -> int:
    row = run("SELECT COUNT(*) AS cnt FROM posts", fetch="one")
    return row["cnt"] if row else 0


# ── 初始化 ────────────────────────────────────────────
try:
    init_db()
except Exception as e:
    st.error(f"数据库连接失败：{type(e).__name__}: {e}")
    st.info("💡 请检查 Streamlit Secrets 中的 DATABASE_URL 是否正确。")
    st.stop()

for key, default in [
    ("page", "read"),
    ("view_post_id", None),
    ("edit_post_id", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def go(page, **kwargs):
    st.session_state.page = page
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()


# ── 侧边栏 ────────────────────────────────────────────
with st.sidebar:
    st.title("🌱 我的成长日志")
    st.markdown("*每天记录，复利生长*")
    st.divider()

    if st.button("📖 所有文章", use_container_width=True,
                 type="primary" if st.session_state.page == "read" else "secondary"):
        go("read", view_post_id=None)

    if st.button("✍️ 写文章", use_container_width=True,
                 type="primary" if st.session_state.page == "write" else "secondary"):
        go("write")

    st.divider()
    days_kept = (datetime.today().date() - START_DATE).days + 1
    st.metric("📝 累计文章", count_posts())
    st.metric("📅 坚持天数", max(days_kept, 1))


# ══ 📖 阅读页 ══
if st.session_state.page == "read":

    if st.session_state.view_post_id:
        post = get_post(st.session_state.view_post_id)
        if not post:
            st.error("文章不存在")
            go("read", view_post_id=None)

        col_back, col_edit, _ = st.columns([2, 2, 6])
        with col_back:
            if st.button("← 返回列表"):
                go("read", view_post_id=None)
        with col_edit:
            if st.button("✏️ 编辑文章", type="primary"):
                go("edit", edit_post_id=post["id"])

        st.title(post["title"])
        c1, c2, c3, c4 = st.columns(4)
        c1.caption(f"📅 {str(post['created_at'])[:10]}")
        c2.caption(f"📂 {post['category']}")
        c3.caption(f"🏷 {post['tags']}" if post["tags"] else "")
        updated = str(post['updated_at'])[:10]
        created = str(post['created_at'])[:10]
        c4.caption(f"🔄 更新于 {updated}" if updated != created else "")
        st.divider()
        st.markdown(post["body"])

    else:
        col_f1, col_f2 = st.columns([2, 3])
        with col_f1:
            selected_category = st.radio(
                "分类", CATEGORIES_ALL, horizontal=True, label_visibility="collapsed"
            )
        with col_f2:
            search_query = st.text_input(
                "搜索", placeholder="🔍 输入关键词...", label_visibility="collapsed"
            )

        title_map = {
            "全部": "🏠 所有文章", "读书笔记": "📖 读书笔记",
            "技术感悟": "💡 技术感悟", "复盘": "🔁 复盘", "生活随想": "🌿 生活随想",
        }
        posts = get_all_posts(
            category=selected_category if selected_category != "全部" else None,
            keyword=search_query.strip() if search_query.strip() else None,
        )

        st.title(title_map.get(selected_category, selected_category))
        st.caption(f"共 {len(posts)} 篇")
        st.divider()

        if not posts:
            st.info("暂无文章，点击左侧「✍️ 写文章」开始记录吧！")
        else:
            for post in posts:
                with st.container(border=True):
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.markdown(f"### {post['title']}")
                        if post.get("summary"):
                            st.caption(post["summary"])
                        if post.get("tags"):
                            st.markdown(" ".join([f"`{t}`" for t in post["tags"].split(",") if t.strip()]))
                    with col2:
                        st.caption(str(post["created_at"])[:10])
                        st.caption(f"📂 {post['category']}")
                        if st.button("阅读 →", key=f"read_{post['id']}"):
                            go("read", view_post_id=post["id"])


# ══ ✍️ 写文章页 ══
elif st.session_state.page == "write":
    st.title("✍️ 写新文章")
    st.caption("填写完成后点击发布，文章立即保存到 Supabase ✅")
    st.divider()

    with st.form("write_form", clear_on_submit=True):
        title = st.text_input("📌 标题 *", placeholder="今天想写什么？")
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("📂 分类 *", CATEGORIES_LIST)
        with col2:
            tags_input = st.text_input("🏷 标签", placeholder="用逗号分隔，如：Python, 读书")
        summary = st.text_input("💬 摘要", placeholder="一句话简介（显示在列表页）")
        body = st.text_area("📝 正文（支持 Markdown）", height=450,
                            placeholder="## 开始写作...\n\n支持 **加粗**、*斜体*、`代码`、列表等语法。")
        submitted = st.form_submit_button("🚀 发布文章", type="primary", use_container_width=True)

    if submitted:
        if not title.strip():
            st.error("❌ 标题不能为空")
        elif not body.strip():
            st.error("❌ 正文不能为空")
        else:
            new_id = insert_post(title.strip(), category, tags_input.strip(), summary.strip(), body.strip())
            st.success("🎉 发布成功！")
            st.balloons()
            go("read", view_post_id=new_id)

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
        """)


# ══ ✏️ 编辑文章页 ══
elif st.session_state.page == "edit":
    post = get_post(st.session_state.edit_post_id)
    if not post:
        st.error("文章不存在")
        go("read", view_post_id=None)

    if st.button("← 取消，返回文章"):
        go("read", view_post_id=post["id"])

    st.title("✏️ 编辑文章")
    st.caption(f"创建于 {str(post['created_at'])[:10]}")
    st.divider()

    with st.form("edit_form"):
        title = st.text_input("📌 标题 *", value=post["title"])
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox(
                "📂 分类 *", CATEGORIES_LIST,
                index=CATEGORIES_LIST.index(post["category"]) if post["category"] in CATEGORIES_LIST else 0,
            )
        with col2:
            tags_input = st.text_input("🏷 标签", value=post["tags"])
        summary = st.text_input("💬 摘要", value=post["summary"])
        body = st.text_area("📝 正文（支持 Markdown）", value=post["body"], height=450)
        submitted = st.form_submit_button("💾 保存修改", type="primary", use_container_width=True)

    if submitted:
        if not title.strip():
            st.error("❌ 标题不能为空")
        elif not body.strip():
            st.error("❌ 正文不能为空")
        else:
            update_post(post["id"], title.strip(), category, tags_input.strip(), summary.strip(), body.strip())
            st.success("✅ 修改已保存！")
            go("read", view_post_id=post["id"])
