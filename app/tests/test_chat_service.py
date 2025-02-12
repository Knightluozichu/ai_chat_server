#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest
from unittest.mock import patch, AsyncMock
from app.services.chat_service import ChatService

@pytest.fixture
def sample_messages():
    """提供测试用的消息记录样本"""
    return [
        {"content": "你好", "is_user": True},
        {"content": "你好，有什么可以帮你？", "is_user": False},
        {"content": "今天天气如何？", "is_user": True}
    ]

def test_format_message_history(sample_messages):
    """测试历史消息格式化功能"""
    service = ChatService()
    formatted = service.format_message_history(sample_messages)
    
    # 验证消息数量相同
    assert len(formatted) == len(sample_messages)
    
    # 验证消息格式正确
    assert formatted[0] == {"role": "human", "content": "你好"}
    assert formatted[1] == {"role": "assistant", "content": "你好，有什么可以帮你？"}
    assert formatted[2] == {"role": "human", "content": "今天天气如何？"}

@pytest.mark.asyncio
async def test_generate_response(sample_messages):
    """测试 AI 回复生成功能"""
    service = ChatService()
    
    # Mock chain.ainvoke 方法
    test_response = "今天天气晴朗，温度适宜。"
    with patch.object(service.chain, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
        mock_ainvoke.return_value = test_response
        
        response = await service.generate_response(
            user_input="请告诉我今天的天气",
            message_history=sample_messages
        )
        
        # 验证返回的回复
        assert response == test_response
        
        # 验证 chain.ainvoke 被正确调用
        mock_ainvoke.assert_called_once()
        call_args = mock_ainvoke.call_args[0][0]
        assert "input" in call_args
        assert "chat_history" in call_args
        assert call_args["input"] == "请告诉我今天的天气"

@pytest.mark.asyncio
async def test_generate_response_error():
    """测试生成回复时的错误处理"""
    service = ChatService()
    
    # Mock chain.ainvoke 抛出异常
    with patch.object(service.chain, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
        mock_ainvoke.side_effect = Exception("API调用失败")
        
        with pytest.raises(Exception) as exc_info:
            await service.generate_response(
                user_input="测试消息",
                message_history=[]
            )
        
        assert "生成回复失败" in str(exc_info.value)
        assert "API调用失败" in str(exc_info.value)
