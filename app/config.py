from pydantic import Field
from pydantic_settings import BaseSettings
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # 环境标识，"development" 表示本地开发环境，"production" 表示部署环境
    ENVIRONMENT: str = "development"

    # Supabase 相关配置
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str  # 使用 service_role key 保证安全性
    SUPABASE_JWT_SECRET: str 

    # OpenAI 相关配置
    OPENAI_API_KEY: str
    MODEL_NAME: str = "gpt-3.5-turbo"  # 默认模型，可在环境变量中覆盖

    # SERPAPI 相关配置
    SERPAPI_API_KEY: str
    SERPAPI_API_KEY = "13123123"
    
    # 采购领域配置
    CHAT_INTENT_ENABLED: bool = Field(True, description="是否启用闲聊意图功能")
    PROCUREMENT_DOMAIN_DICT_PATH: str = Field("app/resources/procurement_dicts/domain_terms.json", description="采购领域词典路径")
    POLICY_MONITOR_ENDPOINT: str = Field("https://api.policy-monitor.com/v1", description="政策监控服务端点")
    RISK_KNOWLEDGE_GRAPH_URL: str = Field("http://kg.procurement-risk.com/graphql", description="风险知识图谱API地址")
    OCR_SERVICE_ENDPOINT: str = Field("https://ocr.procurement.com/v1", description="OCR服务端点")
    OCR_API_KEY: str = Field(description="OCR服务API密钥")
  
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 全局配置实例，pydantic 会自动优先使用系统环境变量，未设置时则从 .env 中加载
settings = Settings()

def mask_secret(value: str) -> str:
    """
    对敏感信息进行脱敏处理：仅显示前4位和后4位字符，中间用...替代
    """
    if not value or len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"

def log_config_item(name: str, value: str):
    """
    根据 ENVIRONMENT 和 os.environ 判断配置来源，并打印日志：
    - 若处于生产环境且系统环境变量中存在，则认为使用的是系统环境变量
    - 否则视为使用 .env 配置
    对于包含 KEY/API 的敏感信息，进行脱敏显示
    """
    # 如果设置为生产环境且系统环境变量中存在对应项，则认为来源为系统环境变量
    if settings.ENVIRONMENT.lower() == "production" and os.environ.get(name) is not None:
        source = "系统环境变量"
    else:
        source = ".env 配置"
    display_value = mask_secret(value) if "KEY" in name or "API" in name else value
    logger.info(f"从{source}获取 {name}: {display_value}")

# 统一记录所有配置项的来源和信息
log_config_item("SUPABASE_URL", settings.SUPABASE_URL)
log_config_item("SUPABASE_SERVICE_KEY", settings.SUPABASE_SERVICE_KEY)
log_config_item("OPENAI_API_KEY", settings.OPENAI_API_KEY)
log_config_item("MODEL_NAME", settings.MODEL_NAME)
log_config_item("SERPAPI_API_KEY", settings.SERPAPI_API_KEY)
log_config_item("SUPABASE_JWT_SECRET", settings.SUPABASE_JWT_SECRET)

# 验证所有必需的配置是否已设置
required_configs = {
    "SUPABASE_URL": settings.SUPABASE_URL,
    "SUPABASE_SERVICE_KEY": settings.SUPABASE_SERVICE_KEY,
    "OPENAI_API_KEY": settings.OPENAI_API_KEY,
    "MODEL_NAME": settings.MODEL_NAME,
    "SERPAPI_API_KEY": settings.SERPAPI_API_KEY,
    "SUPABASE_JWT_SECRET": settings.SUPABASE_JWT_SECRET
}

for config_name, config_value in required_configs.items():
    if not config_value:
        raise ValueError(f"必需的配置项 {config_name} 未设置")
    
logger.info("所有必需的配置项已加载完成")
