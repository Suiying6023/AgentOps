# AgentOps Core

AgentOps Core 是一个基于 LangGraph 和 FastAPI 构建的智能体（AI Agent）基础服务框架。项目通过 Supervisor 路由与 ReAct 架构，整合了知识库与 FastMCP 工具链，提供后端 Agent 基础设施。

## 核心特性 (Key Features)

- **多智能体编排 (Multi-Agent)**：基于 Supervisor 节点实现多角色协同。运行时支持根据任务复杂度动态切换模型 (Model Tiering)。
- **工具链协议化 (FastMCP)**：通过 `langchain-mcp-adapters` 将内部工具解耦为独立的 Model Context Protocol 节点。
- **混合知识库 (Knowledge Base)**：
  - **RAG 检索**：基于 PostgreSQL (pgvector)，集成提问重写 (Query Rewriting)、Reranker 重排与多轮检索机制。
  - **LLM Wiki 编译**：支持将文档编译为包含双向链接的 Markdown 页面集合，作为向量检索的补充。
- **动态模型网关**：基于 PostgreSQL 存储大模型厂商 (如 OpenAI/DeepSeek 等) 的 API Key，支持运行时动态更新。
- **并发与会话持久化**：使用 Redis 分布式锁控制并发请求，通过 PostgreSQL (`AsyncPostgresSaver`) 实现基于 `thread_id` 的会话状态持久化。
- **前端页面**：包含基于 Next.js 构建的聊天界面与管理页面。

## 快速启动 (Getting Started)

### 1. 服务端准备 (Backend)

后端采用 `uv` 进行依赖管理：

```bash
# 安装依赖
uv sync

# 启动 FastAPI 服务
uv run python src/run_service.py
```
*(默认运行于 http://localhost:8080)*

### 2. 客户端准备 (Frontend)

```bash
cd frontend
npm install
npm run dev
```
*(聊天界面：http://localhost:3000 | 管理页面：http://localhost:3000/admin)*

## 许可证

MIT License
