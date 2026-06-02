import pytest
import os
from tools.rag import ingest_document

@pytest.mark.asyncio
async def test_pdf_ingest():
    pdf_path = r"D:\Code\Agent\健康元\AI笔试-郭旭辉-杭州师范大学.pdf"
    
    if not os.path.exists(pdf_path):
        pytest.skip(f"文件 {pdf_path} 不存在，跳过测试")
        
    print(f"\n==================== 开始测试 PDF 灌库 ====================")
    ingest_document(pdf_path)
    print(f"==================== 测试 PDF 灌库完成 ====================")
    assert True
