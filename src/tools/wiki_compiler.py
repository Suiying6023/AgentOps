import os
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

# 独立于向量库的纯文本存储区
WIKI_DIR = "data/wiki_base"

class WikiPage(BaseModel):
    title: str = Field(description="页面的核心概念或实体名称，例如 'AgentOps架构' 或 '张三的履历'")
    content: str = Field(description="高度提炼和结构化的 Markdown 正文。如果提及其他概念，请使用双链语法 [[概念名]]。")
    tags: list[str] = Field(description="与此页面相关的标签列表")

class WikiExtraction(BaseModel):
    pages: list[WikiPage] = Field(description="从原文中提取出的独立且高价值的维基百科页面列表")

def compile_document_to_wiki(file_path: str):
    """将非结构化文档直接编译为高价值的 Markdown 维基体系 (实验性功能)"""
    from core.llm import get_model
    os.makedirs(WIKI_DIR, exist_ok=True)
    
    print(f"[LLM Wiki] 🧠 正在执行知识编译引擎，读取: {file_path} ...")
    
    if file_path.endswith(".pdf"):
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        text = "\n".join([doc.page_content for doc in docs])
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            
    # 初始化大模型并强制输出严格的 Pydantic 结构
    llm = get_model()
    try:
        structured_llm = llm.with_structured_output(WikiExtraction)
    except NotImplementedError:
        print("[LLM Wiki] ⚠️ 当前厂商模型不支持 Function Calling 结构化输出，编译失败。请切换到 OpenAI / DeepSeek 主力模型。")
        return
        
    prompt = f"""你是一个顶级的企业级知识架构师 (Knowledge Compiler)。
你的任务是深度阅读用户上传的未整理文稿，提取出其中独立的、高价值的核心概念和实体，并为每一个实体编写一份排版精美的结构化 Wiki 页面。
请遵循纪律：
1. 不要输出任何寒暄，只输出提取后的严格数据结构。
2. 每个页面必须是独立、连贯的 Markdown 格式。
3. 发现相关知识点时，使用 [[链接名]] 的格式创建双向关联感。

原始未整理资料：
{text[:20000]}
"""
    
    try:
        extraction = structured_llm.invoke([HumanMessage(content=prompt)])
        
        for page in extraction.pages:
            # 文件名过滤非法字符
            safe_title = "".join([c for c in page.title if c.isalnum() or c in (" ", "-", "_")]).rstrip()
            page_path = os.path.join(WIKI_DIR, f"{safe_title}.md")
            
            # YAML Frontmatter 元数据头部
            frontmatter = f"---\ntitle: {page.title}\nupdated_at: {datetime.now().isoformat()}\ntags: [{', '.join(page.tags)}]\n---\n\n"
            
            if os.path.exists(page_path):
                # 进阶玩法：未来可以让大模型“融合”两次内容，这里我们先简单追加
                with open(page_path, "a", encoding="utf-8") as f:
                    f.write("\n\n## 🔄 系统追加入库信息\n")
                    f.write(page.content)
            else:
                with open(page_path, "w", encoding="utf-8") as f:
                    f.write(frontmatter + page.content)
                    
            print(f"[LLM Wiki] 📄 成功凝练页面: {page_path}")
            
        print("[LLM Wiki] ✅ 知识编译与组装完成！")
    except Exception as e:
        print(f"[LLM Wiki] ❌ 编译异常: {e}")

@tool
def search_llm_wiki(query: str) -> str:
    """【实验功能】当你被明确要求搜索“维基”、“精华知识”或你需要获取高度提炼的结构化实体信息时，必须调用此工具。
    它会遍历并读取经过后台 LLM 深度编译后的完整 Markdown 页面，而不是零碎的切片片段。
    
    Args:
        query: 核心实体或关键词
    """
    if not os.path.exists(WIKI_DIR):
        return "本地 LLM Wiki 知识库为空，暂无经过编译的词条。"
        
    results = []
    query_lower = query.lower()
    
    # MVP 版本：基于全局文件系统的全文硬匹配
    for filename in os.listdir(WIKI_DIR):
        if not filename.endswith(".md"): continue
        filepath = os.path.join(WIKI_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            # 如果标题或正文命中了，把整个“完整编译好”的页面直接喂给检索者
            if query_lower in filename.lower() or query_lower in content.lower():
                results.append(f"【维基页面：{filename}】\n{content}")
                
    if not results:
        return f"在 LLM Wiki 词条库中未找到与 '{query}' 直接相关的系统化页面。"
        
    # 为了防止上下文溢出，最多返回前 3 个完整页面的深度内容
    return "\n\n====================\n\n".join(results[:3])
