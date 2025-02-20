from enum import Enum
from typing import Any, Dict
from attr import dataclass
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class IntentType(Enum):
    CHAT = "chat"           # 闲聊
    QUERY = "query"         # 信息查询
    TASK = "task"          # 具体任务
    DOCUMENT = "document"   # 文档相关查询
    
@dataclass
class DeepSeekConfig:
    API_KEY: str = "YOUR_DEEPSEEK_API_KEY"
    BASE_URL: str = "https://api.deepseek.com"

class IntentService:
    def __init__(self, config: DeepSeekConfig = DeepSeekConfig()):
        self.config = config
        self.client = OpenAI(
            api_key=self.config.API_KEY,
            base_url=self.config.BASE_URL
        )
        self.system_prompt = """
你是一个意图分类助手。你需要将用户的输入分类为以下四种类型之一：
- 闲聊对话：日常交谈、问候、闲聊等
- 信息查询：询问特定信息、数据或知识
- 任务执行：请求执行具体任务或操作
- 文档检索：与文档相关的查询或操作

只需返回分类结果，不需要解释。
"""

    async def classify_intent(self, text: str) -> IntentType:
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,  # 使用较低的温度以获得更确定的结果
                max_tokens=10     # 只需要简短的回答
            )
            
            # 获取分类结果
            result = response.choices[0].message.content.strip().lower()
            
            # 映射到意图类型
            intent_mapping = {
                "闲聊对话": IntentType.CHAT,
                "信息查询": IntentType.QUERY,
                "任务执行": IntentType.TASK,
                "文档检索": IntentType.DOCUMENT
            }
            
            return intent_mapping.get(result, IntentType.CHAT)
    
        except Exception as e:
            logger.error(f"意图识别失败: {str(e)}")
            return IntentType.CHAT  # 默认返回闲聊类型

# 从环境变量中获取配置
import os

config = DeepSeekConfig(
    API_KEY=os.getenv("DeepSeek_API_KEY")
)
intent_service = IntentService(config)