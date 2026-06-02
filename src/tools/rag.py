import os
import sys
from langchain_community.document_loaders import PyPDFLoader
from langchain_postgres import PGVector
from langchain_core.tools import tool
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from core.llm import get_embeddings
from core.settings import settings

def get_vector_store():
    """获取 PGVector 关系与向量数据库实例"""
    embeddings = get_embeddings()
    
    # 切换不同的 Embedding 模型时使用隔离的 Collection
    collection_name = "agent_knowledge_base_local" if settings.USE_LOCAL_EMBEDDING else "agent_knowledge_base_online"
    
    return PGVector(
        embeddings=embeddings,
        connection=settings.postgres_uri,
        collection_name=collection_name,
        create_extension=True,
    )

def ingest_document(file_path: str):
    """提取本地文档并存入 PGVector"""
    print(f"正在解析文档：{file_path} ...", file=sys.stderr)
    
    if file_path.endswith(".pdf"):
        # PDF 字符切分
        loader = PyPDFLoader(file_path)
        raw_docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = text_splitter.split_documents(raw_docs)
    else:
        # Markdown 标题结构化切分
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
        # 针对每个标题块内部，如果过长则进一步切分，同时继承标题元数据
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = text_splitter.split_documents(header_split_docs)
        
    # [核心优化] 将元数据中的 source (文件名) 强行嵌入到正文开头，增强检索时对文件名的匹配概率
    file_name = os.path.basename(file_path)
    for doc in docs:
        doc.page_content = f"[来源文档: {file_name}]\n" + doc.page_content
        
    print(f"切分完毕，共 {len(docs)} 个片段。正在存入向量库...", file=sys.stderr)
    vector_store = get_vector_store()
    vector_store.add_documents(docs)
    print(f"成功将 {file_path} 存入 PostgreSQL 向量数据库！", file=sys.stderr)

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
    # Query Rewriting (提问重写)
    # ==========================================
    llm = get_model()
    
    rewrite_prompt = f"""你当前作为一个专业的信息检索助手，正在为一个底层 RAG 向量知识库重写搜索关键词。
用户在提问时，经常会携带很多发号施令的口语，或者直接提及“系统”、“知识库”、“RAG”、“向量库”、“查一下”等执行层面的背景指令。

示例：
- 用户提问：“帮我查查向量库里有没有张三的信息” -> 应该重写为：“张三”
- 用户提问：“看看RAG系统里李四的出差报销政策” -> 应该重写为：“李四 出差报销政策”

请基于上述背景，理解用户的真实查询意图，忽略用户的任何行动指令和工具称呼，纯粹地抽取出用于全文检索的**核心实体名词**和**关键动作**。
若指代不明请根据常识补全。请直接输出重写后的核心搜索词（多个词用空格分隔），不要附带任何解释。

用户的原始问题：{query}"""

    try:
        # 使用 HumanMessage 传递 prompt
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=rewrite_prompt)])
        rewritten_query = response.content.strip()
        
        # 如果重写为空则使用原句
        if not rewritten_query:
            rewritten_query = query
            
        print(f"\n[RAG] 原始提问: '{query}'", file=sys.stderr)
        print(f"[RAG] 重写提问: '{rewritten_query}'\n", file=sys.stderr)
    except Exception as e:
        print(f"[RAG] 重写失败，使用原句: {e}", file=sys.stderr)
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
    # Document Reranking (文档重排)
    # ==========================================
    graded_results = []
    
    try:
        import requests
        from core.settings import settings
        
        api_key = settings.GEMAI_API_KEY.get_secret_value() if settings.GEMAI_API_KEY else ""
        url = settings.GEMAI_BASE_URL.replace("/v1", "") + "/v1/rerank"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 批处理 Reranker 评估
        documents = [doc.page_content for doc in results]
        payload = {
            "model": settings.GEMAI_RERANKER_MODEL,
            "query": rewritten_query,
            "documents": documents
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            rerank_data = response.json().get("results", [])
            print(f"\n[RAG] Reranker 出分:", file=sys.stderr)
            
            for item in rerank_data:
                idx = item["index"]
                score = item["relevance_score"]
                print(f"  - 原片段 {idx+1} 相关度得分: {score:.4f}", file=sys.stderr)
                
                # 设定阈值过滤相关片段
                if score >= 0.35:
                    graded_results.append(results[idx])
        else:
            print(f"[RAG] Reranker 服务异常: {response.text}", file=sys.stderr)
            graded_results = results  # 降级：保留全部片段
            
    except Exception as e:
        print(f"[RAG] Reranker 异常，保留全部片段: {e}", file=sys.stderr)
        graded_results = results

    if not graded_results:
        print("[RAG] 检索片段得分低于阈值，拦截返回空结果。", file=sys.stderr)
        return "检索到的片段相关性过低，请提供更多上下文。"
    
    context_list = []
    # 返回过滤后的片段
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
