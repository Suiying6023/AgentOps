# AgentOps Core

AgentOps Core 是一个基于 LangGraph 和 FastAPI 构建的智能体（AI Agent）基础服务框架。项目通过主从动态派生与 ReAct 架构，整合了知识库与 FastMCP 工具链，提供后端 Agent 基础设施。

## 核心特性 (Key Features)

- **多智能体编排 (Multi-Agent)**：单主节点（Main Agent）统筹请求，所有工具直连；当面临复杂推理或并发需求时，动态创建带有独立上下文的子智能体（Sub-Agent）后台执行任务。
- **动态子智能体分级 (Subagent Tiering)**：支持根据任务复杂度（简单、中等、复杂）自动路由至配置的不同层级模型（Low / Medium / High），实现算力成本的最佳分配。
- **多模式安全审查 (Security Review Modes)**：
  - **串行执行 (Sequential)**：拦截器安全完成后触发主模型流，规避单并发 API 限制。
  - **并行执行 (Parallel)**：双通道并发，一旦截获恶意 Prompt Injection 即刻熔断主模型流式输出。
  - **关闭 (Off)**：直接调用主模型，不经过安全拦截。
- **统一数据持久化 (Unified PostgreSQL Persistence)**：
  - **会话管理**：所有基于 `thread_id` 的聊天历史 (Messages) 及会话线程元数据完全存储于 PostgreSQL，并支持前台重命名与物理删除。
  - **快照追踪**：通过 `AsyncPostgresSaver` 实现 LangGraph 节点检查点状态持久化。
  - **动态配置**：大模型 API、路由规则及前台呈现的开关等全局环境变量均存储于 PostgreSQL，并实现热重载更新。
- **工具链协议化 (FastMCP)**：通过 `langchain-mcp-adapters` 将内部工具解耦为独立的 Model Context Protocol 节点。
- **混合知识库 (Knowledge Base)**：
  - **RAG 检索**：基于 PostgreSQL (pgvector)，集成提问重写、Reranker 重排与多轮检索机制。
  - **LLM Wiki 编译**：文档编译为结构化 Markdown 后，其元数据与摘要同步注入 PGVector 进行语义检索，召回整段原始上下文。
- **前端页面**：包含基于 Next.js 构建的流式聊天界面与后台动态管理系统。

## 快速启动 (Getting Started)

### 1. 服务端准备 (Backend)

后端采用 `uv` 进行依赖管理，需确保环境中已配置 PostgreSQL (含 pgvector 扩展) 及 Redis 实例：

```bash
# 安装依赖
uv sync

# 启动 FastAPI 服务
uv run uvicorn main:app --app-dir src --host 0.0.0.0 --port 8080 --reload
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
