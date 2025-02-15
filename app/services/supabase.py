"""
Supabase 服务模块：封装 Supabase 客户端及数据库操作
包括获取对话历史消息和保存新消息的功能
"""
from datetime import datetime
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
                
                if conversations and len(conversations) > 0:
                    if conversations[0].get('user_id') != user_id:
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
            error_data = getattr(e, 'error', {})
            error_code = error_data.get('code', 'unknown')
            error_message = error_data.get('message', str(e))
            error_details = error_data.get('details', None)
            
            logger.error(
                f"获取对话消息失败:\n"
                f"错误码: {error_code}\n"
                f"错误信息: {error_message}\n" 
                f"详细信息: {error_details}\n"
                f"表: conversations\n"
                f"操作: select"
            )
            raise Exception(f"获取对话消息失败: 错误码={error_code}, 信息={error_message}")

    async def update_file_status(self, file_id: str, status: str, error_message: str = None):
        """更新文件处理状态"""
        update_data = {
            "processing_status": status,
            "updated_at": datetime.now().isoformat(),
        }
        
        if error_message:
            update_data["error_message"] = error_message
            
        try:
            result = self.client.table('files') \
                .update(update_data) \
                .eq('id', file_id) \
                .execute()
            logger.info(f"文件状态已更新: file_id={file_id}, status={status}")
            return result.data
        except Exception as e:
            logger.error(f"更新文件状态失败: {str(e)}")
            raise e

    async def store_document_chunk(self, file_id: str, user_id: str, content: str, embedding: list):
        """存储文档块及其向量"""
        try:
            logger.info(f"开始存储文档块: file_id={file_id}, user_id={user_id}")
            
            # 先验证文件所有权
            file_data = self.client.table('files') \
                .select('user_id') \
                .eq('id', file_id) \
                .single() \
                .execute()
            
            if not file_data.data:
                logger.error(f"文件不存在: file_id={file_id}")
                raise ValueError(f"File not found: {file_id}")
            
            file_owner_id = file_data.data['user_id']
            logger.info(f"文件所有者验证: owner_id={file_owner_id}, current_user_id={user_id}")
                
            # 确保文件属于正确的用户
            if file_owner_id != user_id:
                logger.error(f"文件所有权验证失败: owner_id={file_owner_id}, user_id={user_id}")
                raise ValueError(f"User {user_id} does not own file {file_id}")
                
            # 存储文档块
            result = self.client.table('document_chunks') \
                .insert({
                    "file_id": file_id,
                    "user_id": user_id,
                    "content": content,
                    "embedding": embedding
                }) \
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"存储文档块失败: {str(e)}")
            raise

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
        insert_payload = {
            "conversation_id": conversation_id,
            "content": content,
            "is_user": is_user,
            "created_at": "now()"  # 使用服务器时间
        }
        
        result = self.client.table('messages') \
            .insert(insert_payload) \
            .execute() \
            .data

        return result[0] if result else None

# 全局实例化，后续模块可直接导入使用
supabase_service = SupabaseService()
