"""
配置模块：使用 pydantic 的 BaseSettings 进行配置管理，
可自动从 .env 文件加载环境变量，确保类型安全。
"""
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

class Settings(BaseSettings):
    # Supabase 相关配置
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str  # 使用 service_role key 保证安全性
    
    # OpenAI 相关配置
    OPENAI_API_KEY: str
    MODEL_NAME: str = "gpt-3.5-turbo"  # 默认模型，可在 .env 中覆盖

    class Config:
        # 指定 .env 文件路径，便于本地和容器环境统一配置
        env_file = ".env"
        env_file_encoding = "utf-8"

# 全局配置实例，后续其他模块可直接导入 settings 使用
settings = Settings()


# 获取部署环境中的SUPABASE_URL
SUPABASE_URL = os.environ.get('SUPABASE_URL')
if SUPABASE_URL:
    settings.SUPABASE_URL = SUPABASE_URL
    print(f"获取到的 SUPABASE_URL 是: {SUPABASE_URL}")
else:
    print("未找到 SUPABASE_URL 部署环境变量。")
    
# 获取部署环境中的SUPABASE_SERVICE_KEY
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
if SUPABASE_SERVICE_KEY:
    settings.SUPABASE_SERVICE_KEY = SUPABASE_SERVICE_KEY
    print(f"获取到的 SUPABASE_SERVICE_KEY 是: {SUPABASE_SERVICE_KEY}")
else:
    print("未找到 SUPABASE_SERVICE_KEY 部署环境变量。")
    
# 获取部署环境中的OPENAI_API_KEY
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if OPENAI_API_KEY:
    settings.OPENAI_API_KEY = OPENAI_API_KEY
    print(f"获取到的 OPENAI_API_KEY 是: {OPENAI_API_KEY}")
else:
    print("未找到 OPENAI_API_KEY 部署环境变量。")
    
# 获取部署环境中的MODEL_NAME
MODEL_NAME = os.environ.get('MODEL_NAME')
if MODEL_NAME:
    settings.MODEL_NAME = MODEL_NAME
    print(f"获取到的 MODEL_NAME 是: {MODEL_NAME}")   
else:
    print("未找到 MODEL_NAME 部署环境变量。") 


