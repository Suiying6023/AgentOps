# AgentOps 平台：整体架构与运行机制总览

本项目是一个基于 Docker 容器化的 AgentOps 服务平台，构建了一个具备多智能体协同、外部工具调用 (FastMCP)、动态模型调度与安全审查的“混合云原生”大模型基座。

## 系统特性 (Key Features)

- **多智能体编排 (Multi-Agent & Subagent Tiering)**：单主节点（Main Agent）统筹请求，面临复杂需求时动态创建带有独立上下文的子智能体。支持根据任务复杂度（简单/中等/复杂）自动路由至（Low/Medium/High）三个层级的模型，实现算力成本的最佳分配。
- **多模式安全审查 (Security Review Modes)**：
  - **串行 (Sequential)**：拦截器安全完成后触发主模型流，规避单并发限制。
  - **并行 (Parallel)**：双通道并发，截获恶意 Prompt 即刻熔断主模型流式输出。
  - **关闭 (Off)**：直接调用主模型。
- **统一数据持久化 (Unified PostgreSQL Persistence)**：借助 PostgreSQL 实现全链路存储，包括会话管理（`messages`, `threads` 表）、大模型动态配置（API 密钥与路由规则）、LangGraph 状态快照（`AsyncPostgresSaver`）。
- **可靠的基础设施**：借助 `asyncio.Lock` 与后端状态同步解决 `thread_id` 并发竞争问题；前端引入本地缓存与 SSR Hydration 修复会话丢失。
- **混合知识库 (Knowledge Base)**：基于 pgvector 存储向量，融合传统的切块 RAG 和基于大模型编译提炼的结构化 Wiki 检索引擎。

---

## 全局代码框架图

当前系统架构不仅整合了前端交互，还在后端实现了清晰的分层，以下节点均与真实的源码文件强对应。

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

---

## 核心流转时序图

该时序图详细描述了一次用户发起对话后，经过安全审查和子智能体调度的完整生命周期。

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

---

## 编码规范提示

- **模型动态解析**：模型 ID 使用 `{provider}/{model_name}` 结构（例如 `openai/gpt-4o`）。在 `src/core/llm.py` 内动态切分，不再依赖固化的 Enum。
- **子智能体开发**：在 `graph_agent.py` 中，如果需要开发新的专门子智能体，必须通过 `invoke_subagent` 统一入口，按 `complexity` 申请算力，不要直接硬编码模型名。
- **并发与持久化**：所有的存储操作均需通过 `src/core/memory.py` 的 PostgreSQL 连接池完成。禁止使用本地 JSON 或 SQLite 保存核心业务数据。
- **工具开发**：新增加的系统工具应统一放置于 `src/tools/` 下，完善异常捕获后返回给大模型。
