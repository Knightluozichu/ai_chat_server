from enum import Enum
from typing import Any, Dict
from attr import dataclass
from transformers import pipeline
import logging
import requests
import aiohttp

logger = logging.getLogger(__name__)

class IntentType(Enum):
    CHAT = "chat"           # 闲聊
    QUERY = "query"         # 信息查询
    TASK = "task"          # 具体任务
    DOCUMENT = "document"   # 文档相关查询
    
@dataclass
class HFConfig:
    API_URL: str = "https://api-inference.huggingface.co/models/joeddav/xlm-roberta-large-xnli"
    TOKEN: str = "YOUR_HF_TOKEN"  # 请替换为实际的 Token

class IntentService:
    def __init__(self, config: HFConfig = HFConfig()):
        self.config = config
        self.headers = {"Authorization": f"Bearer {self.config.TOKEN}"}
        self.candidate_labels = [
            "闲聊对话",
            "信息查询",
            "任务执行",
            "文档检索"
        ]

    async def _query_hf(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.API_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=10
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"调用 Hugging Face API 失败: {str(e)}")
            raise
        
    async def classify_intent(self, text: str) -> IntentType: 
        try:
            payload = {
                "inputs": text,
                "parameters": {
                    "candidate_labels": self.candidate_labels,
                    "hypothesis_template": "这是关于{}的内容。"
                }
            }
            
            result = await self._query_hf(payload)
            
            # 获取最高概率的标签
            label = result['labels'][0]
            
            # 映射到意图类型
            intent_mapping = {
                "闲聊对话": IntentType.CHAT,
                "信息查询": IntentType.QUERY,
                "任务执行": IntentType.TASK,
                "文档检索": IntentType.DOCUMENT
            }
            
            return intent_mapping.get(label, IntentType.CHAT)
    
        except Exception as e:
            logger.error(f"意图识别失败: {str(e)}")
            return IntentType.CHAT  # 默认返回闲聊类型

# 建议在环境变量中设置 Token
import os

config = HFConfig(
    TOKEN=os.getenv("HF_API_TOKEN")
)
intent_service = IntentService(config)