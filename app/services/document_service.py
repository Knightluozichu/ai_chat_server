import logging
from typing import List
from langchain.document_loaders import TextLoader

# 配置日志
logger = logging.getLogger(__name__)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
import tempfile
import httpx
from app.config import settings
from app.services.supabase import supabase_service

class DocumentService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    async def process_file(self, file_id: str, file_url: str, user_id: str):
        """处理上传的文件"""
        logger.info(f"开始处理文件: file_id={file_id}, url={file_url}")
        temp_path = None
        
        try:
            # 验证文件URL
            if not file_url.endswith(('.txt', '.pdf', '.doc', '.docx')):
                raise ValueError("不支持的文件类型")
                
            # 更新文件状态为处理中
            logger.info(f"更新文件状态为处理中: file_id={file_id}")
            try:
                await supabase_service.update_file_status(file_id, "processing")
            except Exception as e:
                logger.error(f"更新文件状态失败: {str(e)}")
                return
            
            # 下载文件
            async with httpx.AsyncClient() as client:
                response = await client.get(file_url)
                response.raise_for_status()
            logger.info(f"文件下载成功: {file_url}")
                
            # 保存到临时文件
            try:
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    logger.info(f"开始保存临时文件: {temp_file.name}")
                    temp_file.write(response.content)
                    temp_path = temp_file.name
            except Exception as e:
                logger.error(f"保存临时文件失败: {str(e)}")
                raise e

            # 加载文档
            loader = TextLoader(temp_path)
            documents = loader.load()
            
            # 分块
            chunks = self.text_splitter.split_documents(documents)
            
            # 生成向量嵌入并存储
            for chunk in chunks:
                embedding = await self.embeddings.aembed_query(chunk.page_content)
                await supabase_service.store_document_chunk(
                    file_id=file_id,
                    user_id=user_id,
                    content=chunk.page_content,
                    embedding=embedding
                )
            
            # 更新文件状态为完成
            await supabase_service.update_file_status(file_id, "completed")
            
        except Exception as e:
            # 更新文件状态为失败
            logger.error(f"处理文件失败: {str(e)}")
            await supabase_service.update_file_status(file_id, "failed")
            raise e
        finally:
            # 清理临时文件
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.info(f"临时文件已清理: {temp_path}")
                except Exception as e:
                    logger.error(f"清理临时文件失败: {str(e)}")

document_service = DocumentService()