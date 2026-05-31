# 🌱 我的成长日志

> 每天记录，复利生长

基于 Python + Streamlit 搭建的个人成长博客，记录读书笔记、技术感悟、复盘与生活随想。

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 写作流程

1. 在 `posts/对应分类/` 目录下新建 `.md` 文件
2. 文件名格式：`YYYY-MM-DD-标题.md`
3. 文件头部填写 YAML front matter：

```markdown
---
title: "文章标题"
date: 2026-05-31
category: 读书笔记
tags: [标签1, 标签2]
summary: "一句话简介"
---

正文内容...
```

4. `git add . && git commit -m "新增文章" && git push`，博客自动更新 ✅

## 部署到 streamlit.app

1. 将本项目推送到 GitHub
2. 访问 [share.streamlit.io](https://share.streamlit.io)
3. New app → 选择此仓库 → Main file: `app.py` → Deploy

## 分类说明

| 分类 | 内容 |
|------|------|
| 📖 读书笔记 | 每本书的核心提炼与感悟 |
| 💡 技术感悟 | 编程实践与技术思考 |
| 🔁 复盘 | 周/月/季度回顾 |
| 🌿 生活随想 | 日常观察与碎片思考 |
