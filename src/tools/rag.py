import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_postgres import PGVector
from langchain_core.tools import tool
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from core.llm import get_embeddings
from core.settings import settings

def get_vector_store():
    """获取 PGVector 关系与向量数据库实例"""
    embeddings = get_embeddings()
    
    # 核心企业级改造：当切换不同的 Embedding 模型（维度不同）时，必须使用隔离的 Collection
    collection_name = "agent_knowledge_base_local" if settings.USE_LOCAL_EMBEDDING else "agent_knowledge_base_online"
    
    return PGVector(
        embeddings=embeddings,
        connection=settings.postgres_uri,
        collection_name=collection_name,
        create_extension=True,
    )

def ingest_document(file_path: str):
    """提取本地文档并存入 PGVector，支持 PDF 和 TXT/MD (针对 MD 进行高级语义结构化分块)"""
    print(f"正在高级解析文档：{file_path} ...")
    
    if file_path.endswith(".pdf"):
        # PDF 采用常规的重叠字符切分
        loader = PyPDFLoader(file_path)
        raw_docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = text_splitter.split_documents(raw_docs)
    else:
        # MD/TXT 采用高级 Markdown 标题结构化切分，最大化保留上下文段落关系
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        header_split_docs = markdown_splitter.split_text(text)
        
        # 针对每个标题块内部，如果过长则进一步切分，同时继承标题元数据
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = text_splitter.split_documents(header_split_docs)
        
    print(f"高级切分完毕，共 {len(docs)} 个片段。正在生成 Embeddings 并存入 PostgreSQL 向量库...")
    vector_store = get_vector_store()
    vector_store.add_documents(docs)
    print(f"成功将 {file_path} 存入 PostgreSQL 向量数据库！")

@tool
def search_knowledge_base(query: str) -> str:
    """当你被问到任何需要查阅资料、事实核查或你不确定的问题时，必须调用此工具检索本地资料库。
    如果你无法通过常识回答，或者需要引用权威资料，请使用此工具。
    
    Args:
        query: 用户的原始检索需求或口语化提问
    """
    from core.llm import get_model
    from langchain_core.messages import SystemMessage
    
    # ==========================================
    # Phase 9: Query Rewriting (提问重写) 节点
    # ==========================================
    llm = get_model()
    
    rewrite_prompt = f"""你是一个高级的信息检索专家。你的任务是将用户的原始输入重写为一个极其适合在向量数据库(Vector DB)中进行语义搜索（Semantic Search）的标准化查询语句。
请严格遵循以下规则：
1. 提取出所有核心实体、专有名词和关键动作。
2. 剥离掉无意义的口语化语气词（如“请问”、“那个”、“是怎么回事”）。
3. 如果原始问题有指代不明的情况，请根据常识补全。
4. 仅仅输出重写后的搜索词，不要有任何多余的解释、换行或标点。

用户的原始问题：{query}"""

    try:
        # 拦截并重写 Query
        # 注意：不要只传 SystemMessage，许多经过 RLHF 对齐的大模型（如 DeepSeek）如果没看到 HumanMessage 会直接返回空字符串
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=rewrite_prompt)])
        rewritten_query = response.content.strip()
        
        # 兜底：如果模型抽风返回了空，依然用原句
        if not rewritten_query:
            rewritten_query = query
            
        print(f"\n[Agentic RAG] 🔍 原始提问: '{query}'")
        print(f"[Agentic RAG] ✍️ 重写提问: '{rewritten_query}'\n")
    except Exception as e:
        print(f"[Agentic RAG] ⚠️ 重写失败，降级使用原句: {e}")
        rewritten_query = query

    # 使用重写后的查询词请求向量数据库
    vector_store = get_vector_store()
    
    try:
        results = vector_store.similarity_search(rewritten_query, k=4)
    except Exception as e:
        return f"知识库服务暂时不可用，原因: {str(e)}"
        
    if not results:
        return "本地知识库中未找到相关信息。"
        
    # ==========================================
    # Phase 9: Document Grading & Reranking (专业重排裁判)
    # ==========================================
    graded_results = []
    
    try:
        import requests
        from core.settings import settings
        
        url = settings.GEMAI_BASE_URL.replace("/v1", "") + "/v1/rerank"
        api_key = settings.GEMAI_API_KEY.get_secret_value() if settings.GEMAI_API_KEY else "sk-NoCIP2lKzL1SxctciLVOF6W0Jsp5qs1UxZ09Wvi8kPQY73rK"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 提取所有文本丢给专门的 Reranker 模型做批处理
        documents = [doc.page_content for doc in results]
        payload = {
            "model": settings.GEMAI_RERANKER_MODEL,
            "query": rewritten_query,
            "documents": documents
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            rerank_data = response.json().get("results", [])
            print(f"\n[Agentic RAG] ⚡ Reranker 专业裁判出分与重排:")
            
            for item in rerank_data:
                idx = item["index"]
                score = item["relevance_score"]
                print(f"  - 原片段 {idx+1} 相关度得分: {score:.4f}")
                
                # 设定及格线：高于 0.45 视为高度相关，保留并自动根据得分重新洗牌顺序
                # (注意：不同 Reranker 模型的分值分布不同。对于 qwen3-reranker，0.5 左右通常已经是强相关的正样本)
                if score >= 0.45:
                    graded_results.append(results[idx])
        else:
            print(f"[Agentic RAG] ⚠️ Reranker 服务挂了: {response.text}")
            graded_results = results  # 降级：保留全部片段
            
    except Exception as e:
        print(f"[Agentic RAG] ⚠️ Reranker 异常，防丢策略默认保留全部片段: {e}")
        graded_results = results

    if not graded_results:
        print("[Agentic RAG] ❌ 检索召回的片段得分均低于阈值，被专业裁判全部驳回，触发兜底拒答。")
        return "本地知识库中检索到了部分片段，但经过专业 AI 裁判打分后，发现均与您的原始问题缺乏强相关性。请尝试换个说法或提供更多上下文。"
    
    context_list = []
    # 最终喂给大模型的，只有经过裁判筛选的 graded_results
    for i, doc in enumerate(graded_results):
        # 提取切片的标题层次信息（如果有的话），拼接给模型，使其明白上下文层级
        headers = []
        for h_key in ["Header 1", "Header 2", "Header 3"]:
            if h_key in doc.metadata:
                headers.append(doc.metadata[h_key])
        header_path = " -> ".join(headers) if headers else "通用段落"
        context_list.append(f"--- 片段 {i+1} ({header_path}) ---\n{doc.page_content}")
        
    context = "\n\n".join(context_list)
    return f"从知识库中检索到以下信息，请综合这些信息回答用户：\n{context}"
