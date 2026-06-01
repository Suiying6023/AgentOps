# AgentOps Core

AgentOps Core 是一个基于 LangGraph 和 FastAPI 构建的企业级智能体（AI Agent）基础服务框架。项目通过 Supervisor 主管路由与 ReAct 下级专员架构，深度整合了双轨制知识库与 FastMCP 微服务工具链，旨在提供生产级、可扩展的后端 Agent 基础设施。

## 核心特性 (Key Features)

- **多层级智能体编排 (Multi-Agent)**：引入 Supervisor 中枢，实现大管家与下级研究专员协同。在运行时支持根据任务复杂度，对子节点进行动态多模型算力降级分发 (Model Tiering)。
- **微服务工具链 (FastMCP)**：通过 `langchain-mcp-adapters` 将原生工具剥离为独立的 Model Context Protocol 微服务节点，实现了能力与中枢的物理隔离。
- **知识双驱引擎 (Dual-Knowledge Engine)**：
  - **Agentic RAG (自愈检索)**：基于 PostgreSQL (pgvector)，集成提问重写 (Query Rewriting)、Qwen3 极速重排 (Reranker) 以及大模型自驱重搜纠错。
  - **LLM Wiki 编译器**：基于 2026 最新范式，支持将冗长文档一键通读并编译为去中心化、双向链接的结构化 Markdown 百科知识树。
- **动态网关与配置中枢**：摒弃 `.env` 静态硬编码，底层利用 PostgreSQL 实现上游大模型厂商 (OpenAI/DeepSeek/SiliconFlow) API Key 的热挂载与秒级切换。
- **并发与持久化架构**：通过 Redis `ThreadConcurrencyLock` 拦截高并发连击，并完全依托 PostgreSQL (`AsyncPostgresSaver`) 实现高可靠的 `thread_id` 多端会话状态持久化。
- **全栈交互面板**：包含基于 Next.js 构建的极简黑白 (Monochrome) 前端聊天界面，以及用于管理上游模型 Provider 的配置大盘 (Admin Dashboard)。

## 快速启动 (Getting Started)

### 1. 服务端准备 (Backend)

后端采用 `uv` 进行依赖管理：

```bash
# 安装依赖
uv sync

# 启动 FastAPI 服务端引擎 (网关、Agent 核心与知识编译器)
uv run python src/run_service.py
```
*(默认运行于 http://localhost:8080)*

### 2. 客户端准备 (Frontend)

```bash
cd frontend
npm install
npm run dev
```
*(客户端交互界面：http://localhost:3000 | 动态配置网关大盘：http://localhost:3000/admin)*

## 未来演进路线 (Roadmap & TODO)

- [ ] **视觉理解拓展 (Vision MLLM)**：引入 GPT-4o / Qwen-VL 等多模态视觉模型，赋予 Agent 分析图像与复杂数据图表的能力。
- [ ] **高性能任务队列 (Task Queue)**：接入 Celery 等异步队列，彻底解耦海量长文档的 RAG 向量化切片与 LLM Wiki 编译耗时任务，保障主服务丝滑吞吐。
- [ ] **MinerU 深度集成**：结合 OpenDataLab 视觉解析大模型，将知识库的输入能力从纯文本拓展至复杂的双栏学术论文、数理公式及扫描版 PDF。

## 许可证

MIT License
