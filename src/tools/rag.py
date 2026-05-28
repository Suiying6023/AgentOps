import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_chroma import Chroma
from langchain_core.tools import tool
from core.llm import get_embeddings

VECTOR_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "vector_db")

def get_vector_store():
    """获取 ChromaDB 本地向量库实例"""
    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
    embeddings = get_embeddings()
    return Chroma(
        collection_name="agent_knowledge_base",
        embedding_function=embeddings,
        persist_directory=VECTOR_STORE_DIR,
    )

def ingest_document(file_path: str):
    """提取本地文档并存入 ChromaDB，支持 PDF 和 TXT/MD"""
    print(f"正在解析文档：{file_path} ...")
    
    if file_path.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    else:
        loader = TextLoader(file_path, encoding="utf-8")
        
    # 对于简单测试，我们可以用 load_and_split
    docs = loader.load_and_split()
    print(f"文档切分完毕，共 {len(docs)} 个片段。正在生成 Embeddings 并存入数据库...")
    vector_store = get_vector_store()
    vector_store.add_documents(docs)
    print(f"成功将 {file_path} 存入向量库！")

@tool
def search_knowledge_base(query: str) -> str:
    """当用户询问关于公司政策、特定技术文档或专业知识库内容时，调用此工具检索本地资料库。
    如果你无法通过常识回答，或者需要引用权威资料，请使用此工具。
    
    Args:
        query: 用户的检索关键词
    """
    vector_store = get_vector_store()
    
    # 检查集合是否存在数据
    if vector_store._collection.count() == 0:
        return "本地知识库目前为空，未挂载任何文档。"
        
    results = vector_store.similarity_search(query, k=3)
    if not results:
        return "本地知识库中未找到相关信息。"
    
    context = "\n\n".join([f"--- 片段 {i+1} ---\n{doc.page_content}" for i, doc in enumerate(results)])
    return f"从知识库中检索到以下信息，请综合这些信息回答用户：\n{context}"
