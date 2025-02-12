"""
API 层入口：实现与前端的交互接口，集成 Supabase 和 Chat 服务
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from typing import List, Dict

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class ChatRequest(BaseModel):
    user_id: str
    message: str

# 模拟数据 - 在实际集成时会被真实服务替代
MOCK_MESSAGES = {
    "conv_123": [
        {"content": "你好", "is_user": True},
        {"content": "你好！我是AI助手，有什么可以帮你的吗？", "is_user": False}
    ]
}

async def mock_get_conversation_messages(conversation_id: str, user_id: str) -> List[Dict]:
    """
    模拟获取对话历史
    """
    if conversation_id not in MOCK_MESSAGES:
        raise HTTPException(status_code=404, detail="对话不存在")
    return MOCK_MESSAGES[conversation_id]

async def mock_generate_response(message: str, history: List[Dict]) -> str:
    """
    模拟生成AI回复
    """
    return f"这是对'{message}'的模拟回复。"

async def mock_save_message(conversation_id: str, content: str, is_user: bool):
    """
    模拟保存消息
    """
    if conversation_id in MOCK_MESSAGES:
        MOCK_MESSAGES[conversation_id].append({"content": content, "is_user": is_user})
    else:
        MOCK_MESSAGES[conversation_id] = [{"content": content, "is_user": is_user}]

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
        history = await mock_get_conversation_messages(conversation_id, request.user_id)

        # 2. 生成AI回复
        logger.info(f"正在为用户{request.user_id}生成回复")
        ai_response = await mock_generate_response(request.message, history)

        # 3. 异步保存消息
        logger.info("异步保存消息")
        background_tasks.add_task(
            mock_save_message,
            conversation_id=conversation_id,
            content=request.message,
            is_user=True
        )
        background_tasks.add_task(
            mock_save_message,
            conversation_id=conversation_id,
            content=ai_response,
            is_user=False
        )

        # 4. 返回响应
        return {"response": ai_response}

    except HTTPException as e:
        # 重新抛出HTTP异常
        raise e
    except Exception as e:
        # 记录未预期的错误
        logger.error(f"处理请求时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

# 健康检查端点
@app.get("/api/chat/{conversation_id}/history")
async def get_chat_history(conversation_id: str):
    """
    获取对话历史API端点
    """
    try:
        if conversation_id not in MOCK_MESSAGES:
            raise HTTPException(status_code=404, detail="对话不存在")
        return MOCK_MESSAGES[conversation_id]
    except Exception as e:
        logger.error(f"获取对话历史时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@app.get("/health")
async def health_check():
    """
    健康检查API，用于监控服务状态
    """
    return {"status": "healthy"}


@app.get("/")
async def root():
    """
    根路径，用于测试
    """
    return {"message": "Hello World!"}