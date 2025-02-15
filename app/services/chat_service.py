
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import List, Dict, Any, Optional
from langchain.agents import AgentType, initialize_agent
from langchain_community.utilities import SerpAPIWrapper
from langchain.tools import Tool

from app.config import settings
from app.services.supabase import supabase_service

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        """
        初始化 Chat 服务，创建 ChatOpenAI 模型实例和 Prompt 模板。
        Prompt 中要求回答时结合最新的搜索信息，确保回复包含最新的数据和时间节点。
        """
        try:
            # 初始化 OpenAI 模型实例
            self.model = ChatOpenAI(
                model_name=settings.MODEL_NAME,
                temperature=0.7,
                streaming=True,
                openai_api_key=settings.OPENAI_API_KEY
            )
            
            # 初始化向量嵌入模型
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=settings.OPENAI_API_KEY
            )

            # 初始化搜索工具
            search = SerpAPIWrapper(serpapi_api_key=settings.SERPAPI_API_KEY)
            self.tool = [
                Tool(
                    name="Search",
                    func=search.run,
                    description="当你需要搜索实时信息时使用这个工具"
                )
            ]

            # 构造 Prompt 模板
            self.prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "你是一个有帮助的AI助手，请用简洁、专业的中文回答问题。"
                    "搜索时，请找到排名前3的网页，提取其中的正文内容，去除重复或相似的部分，并进行总结和摘要。"
                    "在回答时，请务必结合最新的搜索信息，如果搜索结果中包含具体的数值，请直接引用。"
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}")
            ])

            # 初始化 Agent
            self.agent = initialize_agent(
                tools=self.tool,
                llm=self.model,
                agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                verbose=True,
                agent_kwargs={"prompt": self.prompt}
            )
            
            logger.info("ChatService 初始化成功")
        except Exception as e:
            logger.error(f"ChatService 初始化失败: {str(e)}")
            raise

    def format_message_history(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        将数据库中的消息记录转换为 LangChain 格式。

        Args:
            messages: 列表，每个消息包含 "content" 和 "is_user" 字段。

        Returns:
            格式化后的消息列表，每个消息包含 "role" 和 "content" 字段。
        """
        try:
            formatted = []
            for msg in messages:
                role = "human" if msg.get("is_user") else "assistant"
                content = msg.get("content", "").strip()
                if content:  # 确保内容不为空
                    formatted.append({"role": role, "content": content})
            return formatted
        except Exception as e:
            logger.error(f"格式化消息历史失败: {str(e)}")
            return []

    async def _get_relevant_docs(
        self, query: str, user_id: str
    ) -> List[Dict]:
        """
        获取相关文档片段
        
        Args:
            query: 查询文本
            user_id: 用户ID
            
        Returns:
            相关文档列表
        """
        try:
            # 生成查询文本的向量嵌入
            query_embedding = await self.embeddings.aembed_query(query)
            
            # 调用 Supabase 存储过程查询相关文档
            result = await supabase_service.client.rpc(
                'match_documents',
                {
                    'query_embedding': query_embedding,
                    'match_count': 3,
                    'user_id_input': user_id
                }
            ).execute()
            
            if result.data:
                return result.data
            return []
        except Exception as e:
            logger.error(f"获取相关文档失败: {str(e)}")
            return []

    async def generate_response(
        self, 
        user_input: str, 
        message_history: List[Dict[str, Any]], 
        user_id: Optional[str] = None
    ) -> str:
        """
        根据用户输入和历史消息生成 AI 回复，支持RAG检索增强。

        Args:
            user_input: 用户当前的输入消息。
            message_history: 数据库获取的历史消息列表。
            user_id: 可选的用户ID，用于获取相关文档。

        Returns:
            str: 生成的 AI 回复文本。

        Raises:
            Exception: 当生成回复过程中发生错误时。
        """
        try:
            # 获取相关文档片段
            relevant_docs = []
            if user_id:
                relevant_docs = await self._get_relevant_docs(user_input, user_id)
            
            # 构造system提示,加入文档内容
            system_prompt = "你是一个有帮助的AI助手,请用简洁、专业的中文回答问题。"
            if relevant_docs:
                docs_content = "\n\n".join([
                    f"文档片段 {i+1}:\n{doc['content']}" 
                    for i, doc in enumerate(relevant_docs)
                ])
                system_prompt += f"\n\n参考以下相关文档内容回答:\n{docs_content}"
            
            # 格式化历史消息
            formatted_history = self.format_message_history(message_history)

            # 调用 agent 生成回复
            response = await self.agent.ainvoke({
                "input": user_input,
                "chat_history": formatted_history
            })

            # 解析响应
            if isinstance(response, dict):
                result = response
            else:
                result = json.loads(response)

            # 提取最终答案
            if "action_input" in result:
                return result["action_input"]
            elif "output" in result:
                return result["output"]
            else:
                return str(result)

        except Exception as e:
            error_msg = f"生成回复失败: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

# 全局服务实例
chat_service = ChatService()
