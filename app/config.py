"""
配置模块：使用 pydantic 的 BaseSettings 进行配置管理，
可自动从 .env 文件加载环境变量，确保类型安全。
"""
from pydantic import BaseSettings

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
