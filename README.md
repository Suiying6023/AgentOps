# AgentOps Core

AgentOps Core 是一个基于 LangGraph 和 FastAPI 构建的智能体（AI Agent）基础服务平台，构建了一个具备多智能体协同、外部工具调用 (FastMCP)、动态模型调度与安全审查的“混合云原生”大模型基座。

## 核心特性 (Key Features)

- **多智能体编排 (Multi-Agent & Subagent Tiering)**：单主节点（Main Agent）统筹请求，所有工具直连；面临复杂推理需求时，动态创建带有独立上下文的子智能体。支持根据任务复杂度（简单/中等/复杂）自动路由至配置的不同层级模型（Low/Medium/High），实现算力成本的最佳分配。
- **多模式安全审查 (Security Review Modes)**：
  - **串行执行 (Sequential)**：拦截器安全完成后触发主模型流，规避单并发 API 限制。
  - **并行执行 (Parallel)**：双通道并发，一旦截获恶意 Prompt Injection 即刻熔断主模型流式输出。
  - **关闭 (Off)**：直接调用主模型，不经过安全拦截。
- **统一数据持久化 (Unified PostgreSQL Persistence)**：借助 PostgreSQL 实现全链路存储。
  - **会话管理**：所有基于 `thread_id` 的聊天历史及线程元数据完全存储于 PostgreSQL，支持前端重命名与删除。
  - **动态配置**：大模型 API、路由规则及前台呈现开关等环境变量均存储于 PostgreSQL 并实现热重载。
  - **快照追踪**：通过 `AsyncPostgresSaver` 实现 LangGraph 节点检查点状态持久化。
- **可靠的基础设施**：借助 `asyncio.Lock` 与后端状态同步解决 `thread_id` 并发竞争问题；前端引入本地缓存与 SSR Hydration 修复页面刷新导致的会话丢失。
- **工具链协议化 (FastMCP)**：通过 `langchain-mcp-adapters` 将内部工具解耦为独立的 Model Context Protocol 微服务节点。
- **混合知识库 (Knowledge Base)**：基于 pgvector 存储向量，融合传统的切块 RAG 和基于大模型编译提炼的结构化 Wiki 检索引擎。

## 全局代码框架图


```mermaid
graph TD
    subgraph Frontend ["前端架构层 (frontend/src/)"]
        AppPage["页面组装<br>(app/page.tsx)"]
        Components["UI 组件群<br>(components/)"]
        Hooks["状态缓存与防丢失<br>(hooks/useChat.ts)"]
        API_Lib["网络请求封装<br>(lib/api.ts)"]
    end
    
    subgraph API_Gateway ["网关服务层 (src/main.py)"]
        Router["会话路由 (/stream, /invoke)"]
        ModelAPI["模型探测接口 (/models)"]
        Guardrails["安全审查 (并行/串行/关闭)<br>(core/guardrails.py)"]
        MemoryStore["PG 会话持久化<br>(core/memory.py)"]
    end

    subgraph Config_Factory ["动态配置与工厂 (src/core/)"]
        ProviderDB["统一配置管理<br>(config_manager.py)"]
        LLMFactory["动态模型工厂<br>(llm.py)"]
    end

    subgraph LangGraph_Engine ["图编排引擎层 (src/agents/)"]
        AgentGraph["核心主节点图<br>(graph_agent.py)"]
        SubAgents["子智能体分级路由<br>(Low/Medium/High)"]
        CallModel["模型执行节点"]
        ToolsNode["工具调度节点"]
    end
    
    subgraph Data_Tools ["数据与工具实现层 (src/tools/ & PostgreSQL)"]
        VectorDB["PostgreSQL + pgvector<br>(rag.py, wiki_compiler.py)"]
        NativeTools["原生工具集<br>(weather.py 等)"]
        MCP["FastMCP 微服务协议集成"]
    end
    
    subgraph Checkpointer ["状态持久化层"]
        PgSaver["AsyncPostgresSaver"]
    end

    AppPage --> Components
    Components --> Hooks
    Hooks --> API_Lib
    API_Lib -->|HTTP/SSE 请求| Router
    API_Lib -->|拉取可用模型| ModelAPI
    
    ModelAPI -->|读取表配置| ProviderDB
    
    Router -->|并发锁与审查模式调度| Guardrails
    Router -->|1.加载历史| MemoryStore
    Router -->|2.触发推理| AgentGraph
    
    AgentGraph --> CallModel
    AgentGraph --> SubAgents
    SubAgents -->|派生子任务| CallModel
    CallModel -->|动态实例化| LLMFactory
    LLMFactory -->|读取密钥| ProviderDB
    
    AgentGraph --> ToolsNode
    ToolsNode -->|调用向量库| VectorDB
    ToolsNode -->|调用网络API| NativeTools
    ToolsNode -->|RPC调用| MCP
    ToolsNode -->|结果注入| CallModel
    
    AgentGraph -.->|流转快照存盘| PgSaver
    AgentGraph -.->|yield Token| Router
```

## 核心流转时序图

描述一次用户发起对话后，经过安全审查和子智能体调度的完整生命周期。

```mermaid
sequenceDiagram
    autonumber
    actor Client as 前端 (Next.js)
    participant API as 接口路由 (chat.py)
    participant Guard as 安全审查 (guardrails.py)
    participant Memory as PG记忆库 (memory.py)
    participant Agent as GraphAgent (agents/)
    participant Factory as 模型工厂 (llm.py)
    participant LG as LangGraph 引擎
    participant Tools as 工具集 (tools/)

    Client->>API: GET /models (获取支持的模型)
    API-->>Client: 返回 Provider/Model 列表
    
    Client->>API: POST /stream (携带用户消息)
    API->>Memory: 获取历史记录并上锁
    
    par 安全审查与推理（并行模式下）
        API->>Guard: 提交内容进行安全审计
        Guard-->>API: 若发现恶意 Prompt 则熔断输出
    and 主业务流
        API->>Agent: 传入历史记录与 model_id
        Agent->>LG: 开始流转
        
        Note over LG: 若遇复杂任务
        LG->>LG: 根据任务复杂度路由 (Low/Medium/High)
        LG->>Factory: 实例化降级或升级的子模型
        
        LG->>Factory: 请求 BaseChatModel
        Factory-->>LG: 返回初始化实例
        LG->>LG: 调用模型并捕获 Token 流
        LG-->>API: yield Chunk
        API-->>Client: 推送 SSE
        
        Note over LG: 若需调用工具
        LG->>Tools: 执行业务逻辑 (查 RAG / FastMCP)
        Tools-->>LG: 返回结果继续循环
    end
    
    Note over LG: 到达 END 节点
    LG-->>Agent: 返回完整 State
    
    API->>Memory: 持久化 Human & AI 消息到 PG
    API-->>Client: 推送 [DONE] 结束流
```

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
