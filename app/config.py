"""
配置模块：使用 pydantic 的 BaseSettings 进行配置管理，
可自动从 .env 文件加载环境变量，确保类型安全。
同时支持从系统环境变量覆盖配置，适应不同部署环境。
"""
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Supabase 相关配置
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str  # 使用 service_role key 保证安全性
    
    # OpenAI 相关配置
    OPENAI_API_KEY: str
    MODEL_NAME: str = "gpt-3.5-turbo"  # 默认模型，可在环境变量中覆盖
    
    SERPAPI_API_KEY: str

    class Config:
        # 指定 .env 文件路径，便于本地和容器环境统一配置
        env_file = ".env"
        env_file_encoding = "utf-8"

# 全局配置实例，后续其他模块可直接导入 settings 使用
settings = Settings()

def mask_secret(value: str) -> str:
    """
    对敏感信息进行脱敏处理：仅显示前4位和后4位字符，中间用*替代
    """
    if not value or len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"

# 获取并尝试使用系统环境变量（生产环境优先）
SUPABASE_URL = os.environ.get('SUPABASE_URL')
if SUPABASE_URL:
    settings.SUPABASE_URL = SUPABASE_URL
    logger.info(f"从系统环境变量获取 SUPABASE_URL: {SUPABASE_URL}")
else:
    logger.info(f"使用 .env 配置的 SUPABASE_URL: {settings.SUPABASE_URL}")
    
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
if SUPABASE_SERVICE_KEY:
    settings.SUPABASE_SERVICE_KEY = SUPABASE_SERVICE_KEY
    logger.info(f"从系统环境变量获取 SUPABASE_SERVICE_KEY: {mask_secret(SUPABASE_SERVICE_KEY)}")
else:
    logger.info(f"使用 .env 配置的 SUPABASE_SERVICE_KEY: {mask_secret(settings.SUPABASE_SERVICE_KEY)}")
    
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if OPENAI_API_KEY:
    settings.OPENAI_API_KEY = OPENAI_API_KEY
    logger.info(f"从系统环境变量获取 OPENAI_API_KEY: {mask_secret(OPENAI_API_KEY)}")
else:
    logger.info(f"使用 .env 配置的 OPENAI_API_KEY: {mask_secret(settings.OPENAI_API_KEY)}")
    
MODEL_NAME = os.environ.get('MODEL_NAME')
if MODEL_NAME:
    settings.MODEL_NAME = MODEL_NAME
    logger.info(f"从系统环境变量获取 MODEL_NAME: {MODEL_NAME}")   
else:
    logger.info(f"使用 .env 配置的 MODEL_NAME: {settings.MODEL_NAME}")

SERPAPI_API_KEY = os.environ.get('SERPAPI_API_KEY')
if SERPAPI_API_KEY:
    settings.SERPAPI_API_KEY = SERPAPI_API_KEY
    logger.info(f"从系统环境变量获取 SERPAPI_API_KEY: {mask_secret(SERPAPI_API_KEY)}")
else:
    logger.info(f"使用.env 配置的 SERPAPI_API_KEY: {mask_secret(settings.SERPAPI_API_KEY)}")

# 验证所有必需的配置是否已设置
required_configs = {
    "SUPABASE_URL": settings.SUPABASE_URL,
    "SUPABASE_SERVICE_KEY": settings.SUPABASE_SERVICE_KEY,
    "OPENAI_API_KEY": settings.OPENAI_API_KEY,
    "MODEL_NAME": settings.MODEL_NAME,
    "SERPAPI_API_KEY": settings.SERPAPI_API_KEY
}

for config_name, config_value in required_configs.items():
    if not config_value:
        raise ValueError(f"必需的配置项 {config_name} 未设置")
    
logger.info("所有必需的配置项已加载完成")
