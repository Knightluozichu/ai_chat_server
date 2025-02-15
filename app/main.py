"""
API 层入口：实现与前端的交互接口，集成 Supabase 和 Chat 服务
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

# 导入服务模块
from app.services.supabase import supabase_service
from app.services.chat_service import chat_service

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI()

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
        ai_response = await chat_service.generate_response(request.message, history)
        
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
        history = supabase_service.get_conversation_messages(conversation_id, NoneNoneNone)
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

@app.get("/")
async def root():
    """
    根路径 - 快速健康检查
    """
    return {"status": "ok"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)