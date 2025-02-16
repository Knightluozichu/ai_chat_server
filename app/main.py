"""
API 层入口：实现与前端的交互接口，集成 Supabase 和 Chat 服务
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from json.decoder import JSONDecodeError
import logging

# 导入服务模块
from app.services.supabase import supabase_service
from app.services.chat_service import chat_service
from app.services.document_service import document_service

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_message = str(exc)
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
    else:
        status_code = 500
        logger.error(f"未预期的错误: {error_message}", exc_info=True)
    
    return JSONResponse(
        status_code=status_code,
        content={"error": error_message}
    )

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.post("/api/chat/{conversation_id}")
async def chat_endpoint(
    conversation_id: str,
    request: ChatRequest,
    background_tasks: BackgroundTasks
):
    """
    聊天API端点
    """
    try:
        # 1. 获取对话历史
        logger.info(f"获取对话{conversation_id}的历史消息")
        history = supabase_service.get_conversation_messages(conversation_id, request.user_id)

        # 2. 生成AI回复
        logger.info(f"正在为用户{request.user_id}生成回复")
        ai_response = await chat_service.generate_response(request.message, history, request.user_id)

        # 3. 返回响应
        return {"response": ai_response}

    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@app.get("/api/chat/{conversation_id}/history")
async def get_chat_history(conversation_id: str):
    """
    获取对话历史API端点
    """
    try:
        # 获取对话历史
        history = supabase_service.get_conversation_messages(conversation_id, None)
        return history
    except Exception as e:
        logger.error(f"获取对话历史时发生错误: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"获取对话历史失败: {str(e)}")

@app.get("/health")
async def health_check():
    """
    健康检查API，用于监控服务状态
    """
    return {"status": "healthy"}

@app.post("/api/documents/process")
async def process_document(
    request: Request,
    background_tasks: BackgroundTasks
):
    """处理上传的文档"""
    try:
        # 记录请求体日志
        body = await request.json()
        logger.info(f"收到文档处理请求: {body}")

        file_id = body.get("file_id")
        file_url = body.get("url")
        user_id = body.get("user_id")

        if not user_id:
            logger.error("缺少user_id参数")
            raise HTTPException(status_code=400, detail="Missing user_id parameter")

        if not file_id or not file_url:
            logger.error(f"缺少必要参数: file_id={file_id}, file_url={file_url}")
            raise HTTPException(status_code=400, detail="缺少必要参数 file_id 或 url")

        logger.info(f"开始处理文档: file_id={file_id}, url={file_url}")

        background_tasks.add_task(
            document_service.process_file,
            file_id=file_id,
            file_url=file_url,
            user_id=user_id
        )

        logger.info(f"文档处理任务已添加到后台: file_id={file_id}")
        return {"status": "processing", "file_id": file_id}

    except JSONDecodeError as e:
        logger.error(f"JSON解析错误: {str(e)}")
        raise HTTPException(status_code=400, detail="无效的JSON格式")
    except Exception as e:
        logger.error(f"处理文档请求时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents/{file_id}/status")
async def get_file_status(file_id: str):
    """获取文件处理状态"""
    try:
        result = supabase_service.client.table('files') \
            .select('processing_status,error_message,progress,processed_at') \
            .eq('id', file_id) \
            .single() \
            .execute()
            
        if not result.data:
            raise HTTPException(status_code=404, detail="文件不存在")
            
        return {
            "status": result.data['processing_status'],
            "error": result.data.get('error_message'),
            "progress": result.data.get('progress', 0),
            "processed_at": result.data.get('processed_at')
        }
    except Exception as e:
        logger.error(f"获取文件状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """
    根路径 - 快速健康检查
    """
    return {"status": "ok"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)