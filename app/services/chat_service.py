#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from typing import List, Dict, Any
from langchain.agents import AgentType, initialize_agent
# from langchain.utilities import SerpAPIWrapper
from langchain_community.utilities import SerpAPIWrapper
from langchain.tools import Tool

from app.config import settings

class ChatService:
    def __init__(self):
        """
        初始化 Chat 服务，创建 ChatOpenAI 模型实例和 Prompt 模板
        """
        # 初始化 OpenAI 模型实例
        self.model = ChatOpenAI(
            model_name=settings.MODEL_NAME,
            temperature=0.7,  # 控制输出的随机性
            streaming=True,   # 启用流式输出
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        search = SerpAPIWrapper(api_key=settings.SERP_API_KEY)
        self.tool = [
            Tool(
                name="Search",
                func=search.run,
                description="当你需要搜索实时信息时使用这个工具"
            )
        ]
        # 初始化 Agent
        self.agent = initialize_agent(
            tools=self.tool,
            llm=self.model,
            agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
            verbose=True
        )

        # 构造 Prompt 模板：固定的系统提示 + 历史记录占位 + 当前输入
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个有帮助的AI助手，请用简洁、专业的中文回答问题。"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])

        # 组合 prompt、模型与输出解析器，形成 chain
        # self.chain = self.prompt | self.model | StrOutputParser()

    def format_message_history(self, messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        将数据库中的消息记录转换为 LangChain 格式
        
        Args:
            messages: 列表，每个消息包含 "content" 和 "is_user" 字段
            
        Returns:
            格式化后的消息列表，每个消息包含 "role" 和 "content" 字段
        """
        formatted = []
        for msg in messages:
            role = "human" if msg.get("is_user") else "assistant"
            formatted.append({"role": role, "content": msg.get("content", "")})
        return formatted

    async def generate_response(self, user_input: str, message_history: List[Dict[str, Any]]) -> str:
        """
        根据用户输入和历史消息生成AI回复
        
        Args:
            user_input: 用户当前的输入消息
            message_history: 数据库获取的历史消息列表
            
        Returns:
            生成的AI回复文本
            
        Raises:
            Exception: 当生成回复过程中发生错误时
        """
        try:
            # 格式化历史消息
            formatted_history = self.format_message_history(message_history)
            
            # 调用 chain 生成回复
            response = await self.agent.arun(
                input=
                {
                    "input": user_input,
                    "chat_history": formatted_history
                }
            )
            
            return response
            
        except Exception as e:
            raise Exception(f"生成回复失败：{str(e)}")

# 全局服务实例，方便其他模块直接导入使用
chat_service = ChatService()
