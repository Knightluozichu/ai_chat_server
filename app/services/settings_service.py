from typing import Optional
from app.config import settings
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class SettingsUpdateModel(BaseModel):
    model_provider: Optional[str] = Field(None, alias="modelProvider")
    system_prompt: Optional[str] = Field(None, alias="systemPrompt")
    use_web_search: Optional[bool] = Field(None, alias="useWebSearch")
    use_intent_detection: Optional[bool] = Field(None, alias="useIntentDetection")

    class Config:
        allow_population_by_field_name = True

class SettingsService:
    def __init__(self):
        self.settings = settings
        
    async def update_settings(self, update_data: SettingsUpdateModel) -> dict:
        """
        更新应用设置
        """
        # 打印 postman 发送的请求体
        logger.info(f"收到的更新数据: {update_data.dict()}")
        try:
            if update_data.model_provider is not None:
                if update_data.model_provider not in ["deepseek", "openai"]:
                    raise ValueError("模型提供商必须是 deepseek 或 openai")
                self.settings.MODEL_PROVIDER = update_data.model_provider
                
            if update_data.system_prompt is not None:
                self.settings.SYSTEM_PROMPT = update_data.system_prompt
                
            if update_data.use_web_search is not None:
                self.settings.USE_WEB_SEARCH = update_data.use_web_search
                
            if update_data.use_intent_detection is not None:
                self.settings.USE_INTENT_DETECTION = update_data.use_intent_detection
            # 打印更新后的设置
            # logger.info(f"更新后的设置: {self.settings.dict()}")
            return {
                "model_provider": self.settings.MODEL_PROVIDER,
                "system_prompt": self.settings.SYSTEM_PROMPT,
                "use_web_search": self.settings.USE_WEB_SEARCH,
                "use_intent_detection": self.settings.USE_INTENT_DETECTION
            }
            
        except Exception as e:
            logger.error(f"更新设置失败: {str(e)}")
            raise

    async def get_settings(self) -> dict:
        """
        获取当前设置
        """
        return {
            "model_provider": self.settings.MODEL_PROVIDER,
            "system_prompt": self.settings.SYSTEM_PROMPT,
            "use_web_search": self.settings.USE_WEB_SEARCH,
            "use_intent_detection": self.settings.USE_INTENT_DETECTION
        }

# 全局settings service实例
settings_service = SettingsService()
