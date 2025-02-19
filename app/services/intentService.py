from enum import Enum
from transformers import pipeline
import logging

logger = logging.getLogger(__name__)

class IntentType(Enum):
    CHAT = "chat"           # 闲聊
    QUERY = "query"         # 信息查询
    TASK = "task"          # 具体任务
    DOCUMENT = "document"   # 文档相关查询

class IntentService:
    def __init__(self):
        self.classifier = pipeline(
            "zero-shot-classification",
            model="joeddav/xlm-roberta-large-xnli",  # 支持中文的跨语言模型
        )
        self.candidate_labels = [
            "闲聊对话",
            "信息查询",
            "任务执行",
            "文档检索"
        ]

    async def classify_intent(self, text: str) -> str:
        try:
            # 使用零样本分类
            result = self.classifier(
                text,
                candidate_labels=self.candidate_labels,
                hypothesis_template="这是关于{}的内容。"
            )
            
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
        
intent_service = IntentService()