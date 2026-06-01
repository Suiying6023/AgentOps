# AgentOps Core

AgentOps Core 是一个基于 LangGraph 和 FastAPI 构建的智能体（AI Agent）基础服务框架。项目通过主从动态派生与 ReAct 架构，整合了知识库与 FastMCP 工具链，提供后端 Agent 基础设施。

## 核心特性 (Key Features)

- **多智能体编排 (Multi-Agent)**：单主节点（Main Agent）统筹请求，所有工具直连；当面临复杂推理或并发需求时，动态创建带有独立上下文的子智能体（Sub-Agent）后台执行任务。
- **工具链协议化 (FastMCP)**：通过 `langchain-mcp-adapters` 将内部工具解耦为独立的 Model Context Protocol 节点。
- **混合知识库 (Knowledge Base)**：
  - **RAG 检索**：基于 PostgreSQL (pgvector)，集成提问重写 (Query Rewriting)、Reranker 重排与多轮检索机制。
  - **LLM Wiki 编译**：采用 Ingestion-time 向量化方案。文档编译为结构化 Markdown 后，将其元数据与摘要同步注入 PGVector 进行语义检索，召回整段原始上下文。
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
