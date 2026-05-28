# AgentOps Core

AgentOps Core 是一个基于 LangGraph 和 FastAPI 构建的智能体（AI Agent）基础服务框架。项目通过 ReAct 架构整合了大模型与本地工具链，并实现了多轮会话持久化与流式响应，旨在提供可扩展的后端 Agent 基础设施。

## 核心特性 (Key Features)

- **智能体编排**：使用 LangGraph 构建 ReAct 循环机制，支持灵活的工具调用与错误回退流转。
- **会话持久化隔离**：基于 SQLite 实现基于 `thread_id` 的上下文隔离机制，支持多用户独立并发会话。
- **SSE 流式响应**：利用 Server-Sent Events (SSE) 协议向客户端实时传输模型推演过程与系统日志。
- **可观测性与安全**：接入 Langfuse 实现调用链路追踪与 Token 监控；内置 Prompt Injection 异步拦截器。
- **工具链扩展**：内置可配置的工具链接口，默认实现天气查询与基于 ChromaDB 的知识库检索 (RAG) 模块。
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

- [ ] 存储演进：剥离 SQLite，接入 PostgreSQL 集群支撑分布式状态与记忆存储。
- [ ] 并发控制：引入 Redis 处理分布式锁，优化高并发场景下的 SSE 流式稳定性。
- [ ] 深度 RAG：引入 Query Rewriting (提问重写) 与 Self-Correction (检索自纠错) 机制提升准确度。
- [ ] 多智能体协作：引入 Supervisor 路由中枢，实现多角色 Agent 协同工作流。

## 许可证

MIT License
