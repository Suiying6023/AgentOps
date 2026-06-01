# AgentOps Core

AgentOps Core 是一个基于 LangGraph 和 FastAPI 构建的智能体（AI Agent）基础服务框架。项目通过 ReAct 架构整合了大模型与本地工具链，并实现了多轮会话持久化与流式响应，旨在提供可扩展的后端 Agent 基础设施。

## 核心特性 (Key Features)

- **智能体编排**：使用 LangGraph 构建 ReAct 循环机制，支持灵活的工具调用与错误回退流转。
- **Agentic RAG (自愈检索)**：基于 PostgreSQL (pgvector) 构建企业级知识库，集成了提问重写 (Query Rewriting)、Qwen3 极速重排 (Reranker) 以及大模型自驱重搜纠错机制。
- **模型热切换架构**：实现了私有化 Embedding 模型与在线商业 API 的一键无缝切换，基于动态 `collection_name` 隔离多维向量空间。
- **会话持久化隔离**：基于 PostgreSQL (`AsyncPostgresSaver`) 实现 `thread_id` 上下文隔离机制，支持多用户独立并发会话。
- **SSE 流式响应**：利用 Server-Sent Events (SSE) 协议向客户端实时传输模型推演过程与系统日志。
- **可观测性与自动化评测**：深度接入 Langfuse 实现调用链路追踪，并自建了兼容中文语境的 LLM-as-a-Judge 自动化评测体系。
- **全栈交互面板**：包含基于 Next.js 与 Tailwind CSS 构建的前端交互界面，支持多线程侧边栏管理。

## 快速启动 (Getting Started)

### 1. 服务端准备 (Backend)

后端采用 `uv` 进行依赖管理：

```bash
# 复制环境变量配置模板并补充必需的 API_KEY
cp .env.example .env

# 启动 FastAPI 服务端引擎
uv run python src/run_service.py
```
*(默认运行于 http://localhost:8080)*

### 2. 客户端准备 (Frontend)

```bash
cd frontend
npm install
npm run dev
```
*(默认运行于 http://localhost:3000)*

## 未来演进路线 (Roadmap & TODO)

- [x] **并发分布式锁**：接入原生 Redis，引入 `ThreadConcurrencyLock`，完美拦截同会话的高并发连击，解决状态冲突与竞争问题。
- [x] **存储全面演进**：将 LangGraph Checkpointer 底层也从 SQLite 替换为 PostgreSQL，完成 100% 数据库一统。
- [x] **工具协议化**：接入了 `FastMCP` 与 `langchain-mcp-adapters`，将系统级工具剥离为独立的 Model Context Protocol 微服务节点。
- [x] **多智能体协作**：引入 Supervisor 路由中枢，实现多角色 Agent (打分专家、检索专家、闲聊专员) 的协同工作流。
- [ ] **动态网关与运营面板**：搭建前端 Admin 控制台，支持上游模型厂商 (OpenAI/DeepSeek) API Key 的动态管理与网关连通性看板。

## 许可证

MIT License
