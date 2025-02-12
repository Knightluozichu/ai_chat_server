"""
API层的单元测试
"""
from fastapi.testclient import TestClient
import pytest
from httpx import AsyncClient
import uvicorn
import asyncio
import threading
import time
from app.main import app

client = TestClient(app)

def run_server():
    """在后台线程中运行服务器"""
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

def test_health_check():
    """
    测试健康检查端点
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_chat_endpoint_with_existing_conversation():
    """
    测试聊天API - 已存在的对话
    """
    test_data = {
        "user_id": "test_user",
        "message": "你好"
    }
    response = client.post("/api/chat/conv_123", json=test_data)
    assert response.status_code == 200
    assert "response" in response.json()
    assert isinstance(response.json()["response"], str)

def test_chat_endpoint_with_new_conversation():
    """
    测试聊天API - 新对话
    """
    test_data = {
        "user_id": "test_user",
        "message": "新对话"
    }
    response = client.post("/api/chat/new_conv", json=test_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "对话不存在"

def test_chat_endpoint_with_invalid_request():
    """
    测试聊天API - 无效请求
    """
    # 缺少必需字段
    test_data = {
        "message": "你好"
        # 缺少 user_id
    }
    response = client.post("/api/chat/conv_123", json=test_data)
    assert response.status_code == 422  # FastAPI的验证错误状态码

def test_chat_endpoint_with_empty_message():
    """
    测试聊天API - 空消息
    """
    test_data = {
        "user_id": "test_user",
        "message": ""
    }
    response = client.post("/api/chat/conv_123", json=test_data)
    assert response.status_code == 200
    assert "response" in response.json()

@pytest.mark.asyncio
async def test_chat_with_background_tasks():
    """
    使用异步客户端测试完整的聊天流程，包括后台任务
    """    
    # 启动服务器
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # 等待服务器启动
    time.sleep(1)
    
    try:
        async with AsyncClient(base_url="http://127.0.0.1:8000") as ac:
            # 发送测试请求
            test_data = {
                "user_id": "test_user",
                "message": "测试消息"
            }
            response = await ac.post("/api/chat/conv_123", json=test_data)
            
            # 验证响应
            assert response.status_code == 200
            assert "response" in response.json()
            
            # 验证消息是否被保存（允许一些延迟，因为是后台任务）
            await asyncio.sleep(0.1)  # 等待后台任务完成
            
            # 通过API验证消息保存状态
            history_response = await ac.get("/api/chat/conv_123/history")
            assert history_response.status_code == 200
            messages = history_response.json()
            assert any(msg["content"] == "测试消息" and msg["is_user"] for msg in messages)
    finally:
        # 测试完成后停止服务器
        # 注意：在实际生产环境中应该优雅地关闭服务器
        pass  # 由于是daemon线程，主线程结束后会自动终止
