import os
import asyncio
from dotenv import load_dotenv
import pytest
from app.services.intentService import DeepSeekConfig, IntentService, IntentType

# 加载环境变量
load_dotenv()

# @pytest.fixture
# def intent_service():
#     config = HFConfig(
#         TOKEN=os.getenv("HF_API_TOKEN")
#     )
#     return IntentService(config)

# 测试意图分类
@pytest.fixture
def intent_service():
    config = DeepSeekConfig(
        API_KEY=os.getenv("DeepSeek_API_KEY")
    )
    return IntentService(config)

@pytest.mark.asyncio
async def test_intent_classification(intent_service):
    # 测试文本
    test_cases = [
        {
            "text": "你好,能帮我查询一下今天的天气吗?",
            "expected_intent": IntentType.QUERY
        },
        {
            "text": "你觉得人工智能会取代人类工作吗?",
            "expected_intent": IntentType.CHAT
        },
        {
            "text": "请帮我翻译这段英文文档",
            "expected_intent": IntentType.TASK
        }
    ]
    
    for case in test_cases:
        result = await intent_service.classify_intent(case["text"])
        print(f"Input: {case['text']}")
        print(f"Expected: {case['expected_intent']}")
        print(f"Got: {result}\n")
        assert isinstance(result, IntentType)

if __name__ == "__main__":
    # 直接运行测试
    async def main():
        config = DeepSeekConfig(API_KEY=os.getenv("DeepSeek_API_KEY"))
        service = IntentService(config)
        
        # 测试单个查询
        text = "在阿里巴巴最新的螺丝，最便宜的是哪家店"
        result = await service.classify_intent(text)
        print(f"Input: {text}")
        print(f"Intent: {result}")

    asyncio.run(main())