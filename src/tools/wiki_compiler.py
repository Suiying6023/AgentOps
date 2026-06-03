import os
import sys
import asyncio
import aiofiles
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

# 独立于向量库的纯文本存储区
WIKI_DIR = "data/wiki_base"
_wiki_lock = asyncio.Lock()

class WikiPage(BaseModel):
    title: str = Field(description="页面的核心概念或实体名称，例如 'AgentOps架构' 或 '张三的履历'")
    content: str = Field(description="高度提炼和结构化的 Markdown 正文。如果提及其他概念，请使用双链语法 [[概念名]]。")
    tags: list[str] = Field(description="与此页面相关的标签列表")

class WikiExtraction(BaseModel):
    pages: list[WikiPage] = Field(description="从原文中提取出的独立且高价值的维基百科页面列表")

async def compile_document_to_wiki(file_path: str):
    """将文档编译为结构化 Markdown 页面集合"""
    from core.llm import get_model
    os.makedirs(WIKI_DIR, exist_ok=True)
    
    print(f"[Wiki] 读取文件: {file_path}", file=sys.stderr)
    
    if file_path.endswith(".pdf"):
        # PDF loader 暂保留同步调用，因为 langchain_community.document_loaders 缺乏原生异步
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        text = "\n".join([doc.page_content for doc in docs])
    else:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            text = await f.read()
            
    # 配置模型结构化输出
    from core.llm import get_fallback_model_id
    model_name = await get_fallback_model_id()
    llm = get_model(model_name)
    try:
        structured_llm = llm.with_structured_output(WikiExtraction)
    except NotImplementedError:
        print("[Wiki] 当前模型不支持结构化输出，编译失败。", file=sys.stderr)
        return
        
    prompt = f"""提取用户上传文稿中的核心概念和实体，为每个实体输出一份结构化 Markdown 格式的 Wiki 页面。
请遵循以下要求：
1. 仅输出 JSON 数据结构。
2. 每个页面内容为独立 Markdown 格式。
3. 若提及其他相关概念，使用 [[链接名]] 语法标注。

原始未整理资料：
{text[:20000]}
"""
    
    try:
        from tools.rag import get_vector_store
        from langchain_core.documents import Document
        vector_store = get_vector_store()
        
        extraction = await structured_llm.ainvoke([HumanMessage(content=prompt)])
        wiki_docs = []
        
        for page in extraction.pages:
            # 文件名过滤非法字符
            safe_title = "".join([c for c in page.title if c.isalnum() or c in (" ", "-", "_")]).rstrip()
            page_path = os.path.join(WIKI_DIR, f"{safe_title}.md")
            
            # YAML Frontmatter 元数据头部
            frontmatter = f"---\ntitle: {page.title}\nupdated_at: {datetime.now().isoformat()}\ntags: [{', '.join(page.tags)}]\n---\n\n"
            
            async with _wiki_lock:
                if os.path.exists(page_path):
                    # 追加写入已存在的页面
                    async with aiofiles.open(page_path, "a", encoding="utf-8") as f:
                        await f.write("\n\n## 🔄 系统追加入库信息\n")
                        await f.write(page.content)
                else:
                    async with aiofiles.open(page_path, "w", encoding="utf-8") as f:
                        await f.write(frontmatter + page.content)
                    
            print(f"[Wiki] 写入页面: {page_path}", file=sys.stderr)
            
            # 【重要】把 Wiki 页面的元信息和核心摘要制作成向量索引，打入底层 PGVector
            wiki_docs.append(Document(
                page_content=f"[Wiki核心词条] {page.title}\n关键摘要: {page.content[:800]}",
                metadata={"source_wiki": page_path, "wiki_title": page.title, "type": "wiki"}
            ))
            
        # 写入向量库
        if wiki_docs:
            await vector_store.aadd_documents(wiki_docs)
            print(f"[Wiki] 成功建立 {len(wiki_docs)} 个实体的语义寻址向量索引", file=sys.stderr)
            
        print("[Wiki] 编译完成", file=sys.stderr)
    except Exception as e:
        print(f"[Wiki] 编译异常: {e}", file=sys.stderr)

@tool
async def search_llm_wiki(query: str) -> str:
    """搜索 Wiki 页面内容。
    
    Args:
        query: 搜索关键词
    """
    try:
        from tools.rag import get_vector_store
        vector_store = get_vector_store()
        
        print(f"[Wiki Search] 正在使用 PGVector 语义寻址 Wiki 词条: {query}", file=sys.stderr)
        
        # 通过语义搜索向量库，扩大召回面
        results = await vector_store.asimilarity_search(query, k=10)
        
        wiki_hits = []
        seen_paths = set()
        
        for doc in results:
            # 精确拦截我们打过 'wiki' 标签的索引卡片
            if doc.metadata.get("type") == "wiki":
                path = doc.metadata.get("source_wiki")
                if path and path not in seen_paths and os.path.exists(path):
                    seen_paths.add(path)
                    # 反向定位到物理文件，读取100%全貌的完整 Markdown 词条！
                    async with aiofiles.open(path, "r", encoding="utf-8") as f:
                        content = await f.read()
                        wiki_hits.append(f"【Wiki 完整结构化词条：{doc.metadata.get('wiki_title', '未知')}】\n{content}")
                        
        if not wiki_hits:
            return f"Wiki 库中未找到与 '{query}' 高度相关的结构化词条。"
            
        # 返回前两个最相关的完整词条（保证无切割上下文，且不爆 token）
        return "\n\n====================\n\n".join(wiki_hits[:2])
    except Exception as e:
        return f"Wiki语义检索失败: {e}"
