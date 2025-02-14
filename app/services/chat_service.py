#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import List, Dict, Any
from langchain.agents import AgentType, initialize_agent
from langchain_community.utilities import SerpAPIWrapper
from langchain.tools import Tool

from app.config import settings


class ChatService:
    def __init__(self):
        """
        初始化 Chat 服务，创建 ChatOpenAI 模型实例和 Prompt 模板。
        Prompt 中要求回答时结合最新的搜索信息，确保回复包含最新的数据和时间节点。
        """
        # 初始化 OpenAI 模型实例
        self.model = ChatOpenAI(
            model_name=settings.MODEL_NAME,
            temperature=0.7,      # 控制输出的随机性
            streaming=True,       # 启用流式输出
            openai_api_key=settings.OPENAI_API_KEY
        )

        # 初始化搜索工具，传递 SERPAPI_API_KEY
        search = SerpAPIWrapper(serpapi_api_key=settings.SERPAPI_API_KEY)
        self.tool = [
            Tool(
                name="Search",
                func=search.run,
                description="当你需要搜索实时信息时使用这个工具"
            )
        ]

        # 构造 Prompt 模板：固定的系统提示 + 历史记录占位 + 当前输入
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一个有帮助的AI助手，请用简洁、专业的中文回答问题。"
                "搜索时，请找到排名前3的网页，提取其中的正文内容，去除重复或相似的部分，并进行总结和摘要。"
                "在回答时，请务必结合最新的搜索信息，如果搜索结果中包含具体的数值，请直接引用，不要简单地回答,‘请查看相关网站’,确保回复包含最新的数据和时间节点。"
              
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])

        # 初始化 Agent，并传入自定义 prompt，确保内部链能够识别 chat_history 参数
        self.agent = initialize_agent(
            tools=self.tool,
            llm=self.model,
            agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
            verbose=True,
            agent_kwargs={"prompt": self.prompt}
        )

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
        formatted = []
        for msg in messages:
            role = "human" if msg.get("is_user") else "assistant"
            formatted.append({"role": role, "content": msg.get("content", "")})
        return formatted

    async def generate_response(
        self, user_input: str, message_history: List[Dict[str, Any]]
    ) -> str:
        """
        根据用户输入和历史消息生成 AI 回复。

        Args:
            user_input: 用户当前的输入消息。
            message_history: 数据库获取的历史消息列表。

        Returns:
            生成的 AI 回复文本，仅提取返回 JSON 中的最终答案字段。

        Raises:
            Exception: 当生成回复过程中发生错误时。
        """
        try:
            # 格式化历史消息
            formatted_history = self.format_message_history(message_history)

            # 调用 agent 生成回复（使用 ainvoke 异步方法，传入输入和历史记录）
            response = await self.agent.ainvoke(
                input={"input": user_input, "chat_history": formatted_history}
            )

            # 如果返回已经是字典，则直接处理；否则尝试解析 JSON
            if isinstance(response, dict):
                result = response
            else:
                result = json.loads(response)

            # 提取最终答案：优先使用 "action_input" 字段，如果没有则使用 "output" 字段
            if "action_input" in result:
                return result["action_input"]
            elif "output" in result:
                return result["output"]
            else:
                return str(result)

        except Exception as e:
            raise Exception(f"生成回复失败：{str(e)}")


# 全局服务实例，方便其他模块直接导入使用
chat_service = ChatService()