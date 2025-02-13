"""
Supabase 服务模块：封装 Supabase 客户端及数据库操作
包括获取对话历史消息和保存新消息的功能
"""
from supabase import create_client, Client
from app.config import settings
import logging

# 配置日志
logger = logging.getLogger(__name__)

class SupabaseService:
    def __init__(self):
        # 初始化 Supabase 客户端，传入配置项
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )

    def get_conversation_messages(self, conversation_id: str, user_id: str = None):
        """
        获取指定对话的所有历史消息，并验证用户访问权限。

        Args:
            conversation_id (str): 对话ID
            user_id (str, optional): 用户ID，用于权限验证。如果为None，则跳过权限验证

        Returns:
            list: 消息列表，每条消息包含 content, is_user, created_at 字段

        Raises:
            Exception: 当查询失败或用户无权访问时抛出异常
        """
        try:
            # 如果提供了user_id，先验证用户权限
            if user_id:
                # 验证用户权限：查询 conversations 表中该对话的所有者 user_id
                conversation_result = self.client.table('conversations') \
                    .select('user_id') \
                    .eq('id', conversation_id) \
                    .execute()

                conversations = conversation_result.data
                
                if not conversations or len(conversations) == 0:
                    # 如果对话不存在，创建新对话
                    new_conversation = {
                        'id': conversation_id,
                        'user_id': user_id
                    }
                    self.client.table('conversations') \
                        .insert(new_conversation) \
                        .execute()
                elif conversations[0].get('user_id') != user_id:
                    raise Exception("无权访问此对话")

            # 查询 messages 表，选取需要的字段，按创建时间排序
            messages = self.client.table('messages') \
                .select('content,is_user,created_at') \
                .eq('conversation_id', conversation_id) \
                .order('created_at') \
                .execute() \
                .data

            return messages

        except Exception as e:
            logger.error(f"获取对话消息失败: {str(e)}")
            raise Exception(f"获取对话消息失败: {str(e)}")

    def save_message(self, conversation_id: str, content: str, is_user: bool):
        """
        保存一条消息记录到 messages 表中

        Args:
            conversation_id (str): 对话ID
            content (str): 消息内容
            is_user (bool): 是否为用户消息（False 表示 AI 回复）

        Returns:
            dict: 插入的消息记录

        Raises:
            Exception: 当保存消息失败时抛出异常
        """
        try:
            insert_payload = {
                "conversation_id": conversation_id,
                "content": content,
                "is_user": is_user
            }
            
            result = self.client.table('messages') \
                .insert(insert_payload) \
                .execute() \
                .data

            return result[0] if result else None

        except Exception as e:
            logger.error(f"保存消息失败: {str(e)}")
            raise Exception(f"保存消息失败: {str(e)}")

# 全局实例化，后续模块可直接导入使用
supabase_service = SupabaseService()
