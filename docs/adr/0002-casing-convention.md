# ADR-0002: 品牌驼峰展示体与小写技术标识符

日期: 2026-09-21 | 状态: accepted

## 背景
新建项目时名称大小写形式需统一：连写 aftermatter 会被多数读者当成陌生单词扫过，
丢失 after+matter 双关；而 Python 生态的包名/import 强制小写。

## 决定
双层写法：品牌展示体 **AfterMatter**（仅 README 标题、文档标题、演讲场景）；
一切写进文件系统与网络 URL 的标识符一律小写 **aftermatter**
（仓库 slug、PyPI 包名、`import aftermatter`、CLI 命令、目录名）。CLI 另注册短别名 `aftm`。
先例：FastAPI/fastapi、LangChain/langchain。PyPI 大小写不敏感，不存在另一写法被抢注的风险。

## 影响
docs/README.md 命名约定节、AGENTS.md §一 记录此约定；新文档标题用展示体，正文可小写。
