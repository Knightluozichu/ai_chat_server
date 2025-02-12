名字：daniel_2

负责：Chat 服务模块

开发环境:macOS, python 3.10, vscode, codna,git,虚拟环境名为 ai_chat_server

实现思路：下面提供针对“Chat 服务模块”的详细技术实现思路，供 daniel_2 开发人员参考。该模块的主要目标是：
	•	利用 LangChain 框架调用 OpenAI 模型生成 AI 回复
	•	将历史聊天记录和用户输入结合构造 Prompt 模板
	•	异步调用模型生成回复，并对回复进行解析后返回给 API 层

下面分步骤介绍设计思路、主要函数、代码示例、异常处理和测试建议。

一、技术选型与整体架构
	1.	使用 LangChain 框架
	•	使用 langchain-openai 提供的 ChatOpenAI 类调用 OpenAI 模型（如 gpt-3.5-turbo 或其他配置模型）。
	•	利用 LangChain 内置的 PromptTemplate（如 ChatPromptTemplate）构造对话提示，支持将系统提示、历史消息占位符和当前用户输入组合成最终 prompt。
	•	采用 StrOutputParser 等解析器对模型返回结果进行解析，确保返回格式为字符串或符合业务要求的结构。
	2.	异步处理
	•	由于模型调用可能耗时较长，所有模型调用接口应实现异步（使用 async/await），以便 API 层能异步调用并支持流式输出。
	3.	模块职责
	•	初始化 ChatOpenAI 模型实例（使用配置中的 OPENAI_API_KEY、MODEL_NAME 等参数）。
	•	构建固定的 Prompt 模板，模板包含：
	•	系统角色提示：例如“你是一个有帮助的 AI 助手，请用简洁、专业的中文回答问题。”
	•	历史消息占位符，用于动态插入对话历史。
	•	用户当前输入，作为人类角色消息。
	•	提供辅助函数：
	•	format_message_history(messages)：将数据库中获取的消息列表转换为 LangChain 可识别的消息格式。
	•	generate_response(user_input, message_history)：根据用户输入和历史消息调用 AI 模型生成回复，并返回解析后的结果。

二、详细实现步骤

2.1 模型实例与 Prompt 模板的构建
	•	初始化 ChatOpenAI 模型实例
从配置模块中获取 OPENAI_API_KEY 与 MODEL_NAME，并传入 ChatOpenAI 构造函数。同时设置温度、流式输出参数等：

# backend/app/services/chat_service.py
from langchain_openai import ChatOpenAI
from app.config import settings

class ChatService:
    def __init__(self):
        # 初始化 OpenAI 模型实例
        self.model = ChatOpenAI(
            model_name=settings.MODEL_NAME,
            temperature=0.7,
            streaming=True,  # 如果需要流式输出
            openai_api_key=settings.OPENAI_API_KEY
        )


	•	构建 Prompt 模板
使用 LangChain 的 ChatPromptTemplate（或类似 API）构造模板。模板的设计大致如下：
	•	第一条消息（system）：固定系统提示
	•	第二条消息（placeholder）：代表历史聊天记录
	•	第三条消息（human）：格式化的当前用户输入
例如：

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

class ChatService:
    def __init__(self):
        self.model = ChatOpenAI(
            model_name=settings.MODEL_NAME,
            temperature=0.7,
            streaming=True,
            openai_api_key=settings.OPENAI_API_KEY
        )
        # 构造 Prompt 模板：固定的系统提示 + 历史记录占位 + 当前输入
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个有帮助的AI助手，请用简洁、专业的中文回答问题。"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
        # 组合 prompt、模型与输出解析器，形成 chain
        self.chain = self.prompt | self.model | StrOutputParser()



2.2 格式化历史消息
	•	函数：format_message_history(messages)
将从数据库中获取的消息（例如字典列表，每个字典包含 content、is_user 字段）转换为 LangChain 要求的格式。
	•	如果 is_user 为 True，则角色设为 “human”，否则设为 “assistant”。
示例代码：

class ChatService:
    # ... __init__ 已定义

    def format_message_history(self, messages: list) -> list:
        """
        将数据库中的消息转换为 LangChain 格式
        :param messages: 列表，每个消息包含 "content" 和 "is_user"
        :return: 格式化后的消息列表，格式为 [{"role": "human/assistant", "content": ...}, ...]
        """
        formatted = []
        for msg in messages:
            role = "human" if msg.get("is_user") else "assistant"
            formatted.append({"role": role, "content": msg.get("content", "")})
        return formatted



2.3 生成 AI 回复
	•	函数：generate_response(user_input, message_history)
异步函数，根据当前用户输入和历史消息生成回复，步骤如下：
	1.	调用 format_message_history 将历史消息转换格式。
	2.	构造调用 chain 的输入字典，包含键 "input" 对应当前消息，"chat_history" 对应格式化后的历史记录。
	3.	异步调用 chain 的 ainvoke 方法生成回复。
	4.	返回生成的回复（如必要可增加后处理逻辑）。
示例代码：

class ChatService:
    # ... __init__ 与 format_message_history 已定义

    async def generate_response(self, user_input: str, message_history: list) -> str:
        """
        根据当前用户输入和历史聊天记录生成 AI 回复
        :param user_input: 用户当前的提问或消息
        :param message_history: 数据库获取的历史消息列表
        :return: AI 生成的回复文本
        """
        formatted_history = self.format_message_history(message_history)
        try:
            response = await self.chain.ainvoke({
                "input": user_input,
                "chat_history": formatted_history
            })
        except Exception as e:
            # 异常处理，可以记录日志后重新抛出或返回默认回复
            raise Exception(f"生成回复失败：{str(e)}")
        return response



2.4 异常处理与日志记录
	•	在生成回复过程中，需捕获可能由网络、模型调用或解析器产生的异常，记录日志并反馈错误信息。
	•	可以引入 Python 内置 logging 模块或第三方日志库，记录每次请求的输入、格式化后的历史和模型返回结果，便于调试和后续优化。

2.5 单元测试建议
	•	为 format_message_history 函数编写测试用例，提供不同格式的消息输入，验证转换后的角色和值是否符合预期。
	•	对 generate_response 编写异步单元测试，利用 Mock 模块模拟 self.chain.ainvoke 方法返回预期结果，验证在正常和异常情况下的行为。

例如：

import pytest
import asyncio
from app.services.chat_service import ChatService

@pytest.fixture
def sample_messages():
    return [
        {"content": "你好", "is_user": True},
        {"content": "你好，有什么可以帮你？", "is_user": False}
    ]

@pytest.mark.asyncio
async def test_generate_response(monkeypatch, sample_messages):
    service = ChatService()

    # 模拟 chain.ainvoke 方法返回固定字符串
    async def mock_ainvoke(inputs):
        assert inputs["input"] == "请问天气如何？"
        # 检查 chat_history 格式正确
        assert isinstance(inputs["chat_history"], list)
        return "天气晴朗，适合出行。"

    monkeypatch.setattr(service.chain, "ainvoke", mock_ainvoke)
    response = await service.generate_response("请问天气如何？", sample_messages)
    assert response == "天气晴朗，适合出行。"

三、未来扩展方向
	•	Prompt 模板动态调整：根据实际使用反馈，不断优化系统提示和对话模板，甚至支持用户自定义 prompt 选项。
	•	流式回复支持：如果前端需要实时流式输出 AI 回复，可考虑使用 LangChain 提供的流式 API 并处理流式数据。
	•	多模型支持：未来可扩展支持调用不同 LLM 模型，通过配置切换使用其他 API 接口（如 GPT-4、Claude 等）。

总结

对于 daniel_2 来说，Chat 服务模块的主要实现思路包括：
	1.	利用 LangChain 初始化 ChatOpenAI 模型和 Prompt 模板，确保 prompt 设计符合业务要求。
	2.	实现将数据库中的历史消息格式化为 LangChain 所需格式的函数。
	3.	编写异步生成回复函数，传入当前用户输入和格式化后的历史记录，通过调用 chain.ainvoke 得到回复，并进行异常处理。
	4.	配置详细单元测试，确保每个函数在各种场景下均能稳定运行。

以上思路和代码示例为 Chat 服务模块提供了清晰的实现路径，有助于后续与 API 层整合并支持整体聊天对话流程。



当前开发进度 (2025/2/12)：

✅ 完成状态：

Chat 服务核心功能开发

实现 ChatService 类（app/services/chat_service.py）
完成 OpenAI 模型初始化配置
实现 Prompt 模板构建
完成历史消息格式化功能
实现异步回复生成功能
测试用例开发

完成 Chat 服务单元测试（app/tests/test_chat_service.py）
实现多个测试场景：
消息格式化测试
异步回复生成测试
异常处理测试
依赖配置

添加必要的依赖包到 requirements.txt
配置 langchain-openai
配置 langchain-core