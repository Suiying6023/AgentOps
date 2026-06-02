import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks

from core.auth import verify_bearer

router = APIRouter(prefix="/knowledge", dependencies=[Depends(verify_bearer)])

@router.post("/upload")
async def upload_knowledge(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """RAG 向量库上传解析"""
    upload_dir = "data/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    def process_rag_doc(path: str, filename: str):
        try:
            from tools.rag import ingest_document
            ingest_document(path)
            print(f"[后台任务] 文件 {filename} 解析并灌库成功！")
        except Exception as e:
            print(f"[后台任务] 文件 {filename} 灌库失败: {e}")
        finally:
            if os.path.exists(path): os.remove(path)

    # 提交到后台线程池处理，绝不阻塞主线程
    background_tasks.add_task(process_rag_doc, file_path, file.filename)
    return {"status": "success", "message": f"文件 {file.filename} 已进入后台队列，系统正在安静为您灌库，您可继续聊天！"}

@router.post("/upload_wiki")
async def upload_wiki(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Wiki 知识编译上传"""
    upload_dir = "data/uploads_wiki"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    def process_wiki_doc(path: str, filename: str):
        try:
            from tools.wiki_compiler import compile_document_to_wiki
            compile_document_to_wiki(path)
            print(f"[后台任务] 文件 {filename} Wiki 编译成功！")
        except Exception as e:
            print(f"[后台任务] 文件 {filename} Wiki 编译失败: {e}")
        finally:
            if os.path.exists(path): os.remove(path)

    background_tasks.add_task(process_wiki_doc, file_path, file.filename)
    return {"status": "success", "message": f"文件 {file.filename} 已进入后台 Wiki 编译队列，大模型正在通读，您可继续聊天！"}
