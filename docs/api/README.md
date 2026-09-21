# api/ — API 参考

对外接口参考文档：CLI 命令契约、MCP 工具面、serve HTTP API、findings.json 格式。

生成策略：
- `findings.json` / EvidenceBundle 的 JSON Schema 由 pydantic 模型**自动导出**到仓库根 `schemas/`，
  本目录只放人写的导读（如 `contract.md`）；
- serve API 由 FastAPI 自文档（/docs）承担，本目录放稳定子集的手写参考；
- CLI 参考从 `--help` 快照生成，M1 后补。

命名：按面分文件（`cli.md`、`mcp.md`、`server.md`、`contract.md`），不锁其余。
