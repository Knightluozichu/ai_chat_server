"""
Supabase 服务模块的单元测试
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.supabase import SupabaseService

@pytest.fixture
def mock_supabase_client():
    """
    创建模拟的 Supabase 客户端
    """
    mock_client = MagicMock()
    with patch('app.services.supabase.create_client', return_value=mock_client):
        yield mock_client

def test_get_conversation_messages_success(mock_supabase_client):
    """
    测试成功获取对话消息的情况
    """
    # 准备测试数据
    test_messages = [
        {"content": "测试消息1", "is_user": True, "created_at": "2024-01-01"},
        {"content": "测试回复1", "is_user": False, "created_at": "2024-01-01"}
    ]
    test_conversation = {"user_id": "test_user"}
    
    # 设置模拟响应
    messages_response = MagicMock()
    messages_response.data = test_messages
    messages_response.error = None
    
    conversation_response = MagicMock()
    conversation_response.data = test_conversation
    conversation_response.error = None
    
    # 配置模拟客户端的行为
    mock_supabase_client.table().select().eq().order().execute.return_value = messages_response
    mock_supabase_client.table().select().eq().single().execute.return_value = conversation_response
    
    # 执行测试
    service = SupabaseService()
    result = service.get_conversation_messages("test_conv_id", "test_user")
    
    # 验证结果
    assert result == test_messages

def test_get_conversation_messages_unauthorized(mock_supabase_client):
    """
    测试无权访问对话的情况
    """
    # 设置模拟响应：消息存在但用户不匹配
    messages_response = MagicMock()
    messages_response.data = []
    messages_response.error = None
    
    conversation_response = MagicMock()
    conversation_response.data = {"user_id": "other_user"}  # 不同的用户
    conversation_response.error = None
    
    mock_supabase_client.table().select().eq().order().execute.return_value = messages_response
    mock_supabase_client.table().select().eq().single().execute.return_value = conversation_response
    
    # 执行测试，应该抛出异常
    service = SupabaseService()
    with pytest.raises(Exception, match="无权访问此对话"):
        service.get_conversation_messages("test_conv_id", "test_user")

def test_save_message_success(mock_supabase_client):
    """
    测试成功保存消息的情况
    """
    # 准备测试数据
    test_message = {
        "conversation_id": "test_conv_id",
        "content": "测试消息",
        "is_user": True
    }
    
    # 设置模拟响应
    insert_response = MagicMock()
    insert_response.data = test_message
    insert_response.error = None
    
    mock_supabase_client.table().insert().select().single().execute.return_value = insert_response
    
    # 执行测试
    service = SupabaseService()
    result = service.save_message(
        conversation_id="test_conv_id",
        content="测试消息",
        is_user=True
    )
    
    # 验证结果
    assert result == test_message

def test_save_message_error(mock_supabase_client):
    """
    测试保存消息失败的情况
    """
    # 设置模拟响应为错误
    insert_response = MagicMock()
    insert_response.error = {"message": "数据库错误"}
    
    mock_supabase_client.table().insert().select().single().execute.return_value = insert_response
    
    # 执行测试，应该抛出异常
    service = SupabaseService()
    with pytest.raises(Exception, match="保存消息失败"):
        service.save_message("test_conv_id", "测试消息", True)
