from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
import logging
import os

# 优化日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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
    if os.environ.get("ENVIRONMENT", "").lower() == "production" and os.environ.get(name) is not None:
        source = "系统环境变量"
    else:
        source = ".env 配置"
    display_value = mask_secret(value) if "KEY" in name or "API" in name else value
    logger.info(f"从{source}获取 {name}: {display_value}")

class Settings(BaseSettings):
    # 基础配置
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # API配置组
    OPENAI_API_KEY: str = Field(..., description="OpenAI API密钥")
    DEEPSEEK_API_KEY: str = Field(..., description="DeepSeek API密钥")
    SERPAPI_API_KEY: str = Field("13123123", description="SERP API密钥")

    # 数据库配置组
    SUPABASE_URL: str = Field(..., description="Supabase URL")
    SUPABASE_SERVICE_KEY: str = Field(..., description="Supabase服务密钥")
    SUPABASE_JWT_SECRET: str = Field(..., description="Supabase JWT密钥")
    DATABASE_URL: str = Field("postgresql://user:pass@localhost:5432/db", description="数据库URL")

    # 模型配置组
    MODEL_NAME: str = Field("gpt-4o-mini", description="模型名称")
    MODEL_PROVIDER: str = Field("deepseek", description="模型提供商")
    SYSTEM_PROMPT: str = Field("", description="系统提示词")
    USE_WEB_SEARCH: bool = Field(False, description="是否启用网络搜索")
    USE_INTENT_DETECTION: bool = Field(True, description="是否启用意图识别")

    # 采购领域配置组
    CHAT_INTENT_ENABLED: bool = Field(True, description="是否启用闲聊意图功能")

    @property
    def base_path(self) -> Path:
        """返回基础路径"""
        return Path(__file__).parent

    @property
    def resources_path(self) -> Path:
        """返回资源文件路径"""
        return self.base_path / "resources"

    # 使用属性方法设置路径
    PROCUREMENT_DOMAIN_DICT_PATH: str = Field(
        default_factory=lambda: str(Path(__file__).parent / "resources/procurement_dicts/domain_terms.json"),
        description="采购领域词典路径"
    )
    INTENT_MODEL_PATH: str = Field(
        default_factory=lambda: str(Path(__file__).parent / "models/bert-wwm-procurement"),
        description="意图识别模型路径"
    )

    PROCUREMENT_RISK_MODE: str = Field("LOCAL", description="风险评估模式")
    LOCAL_RISK_RULES_PATH: str = Field(
        default_factory=lambda: str(Path(__file__).parent / "resources/procurement_dicts/risk_rules.json"),
        description="本地风险规则路径"
    )
    POLICY_MONITOR_ENDPOINT: str = Field(
        "http://policy-monitor.procurement.internal",
        description="政策监控服务端点"
    )
    RISK_KNOWLEDGE_GRAPH_URL: str = Field(
        "http://kg.procurement-risk.com/graphql",
        description="风险知识图谱API地址"
    )
    # OCR 相关配置
    OCR_SERVICE_ENDPOINT: str = Field(
        "",  # 如果未配置则默认为空字符串
        description="OCR服务端点"
    )
    OCR_API_KEY: str = Field(
        "",  # 如果未配置则默认为空字符串
        description="OCR服务API密钥"
    )
    
    # 监控服务配置
    POLICY_MONITOR_API_KEY: str = Field(
        "",  # 如果未配置则默认为空字符串
        description="政策监控服务API密钥"
    )

    @property
    def required_configs(self) -> dict:
        """返回所有必需的配置项"""
        return {
            "SUPABASE_URL": self.SUPABASE_URL,
            "SUPABASE_SERVICE_KEY": self.SUPABASE_SERVICE_KEY,
            "OPENAI_API_KEY": self.OPENAI_API_KEY,
            "DEEPSEEK_API_KEY": self.DEEPSEEK_API_KEY,
            "MODEL_NAME": self.MODEL_NAME,
            "MODEL_PROVIDER": self.MODEL_PROVIDER,
            "SERPAPI_API_KEY": self.SERPAPI_API_KEY,
            "SUPABASE_JWT_SECRET": self.SUPABASE_JWT_SECRET
        }

    def validate_required_configs(self):
        """验证所有必需的配置项"""
        missing = [k for k, v in self.required_configs.items() if not v]
        if missing:
            raise ValueError(f"必需的配置项未设置: {', '.join(missing)}")

    def validate_model_provider(self) -> None:
        """验证模型提供商配置"""
        valid_providers = {"deepseek", "openai"}
        if self.MODEL_PROVIDER not in valid_providers:
            raise ValueError(f"MODEL_PROVIDER must be one of {valid_providers}")

    def validate_api_keys(self) -> None:
        """验证 API 密钥配置"""
        if self.MODEL_PROVIDER == "deepseek" and not self.DEEPSEEK_API_KEY:
            raise ValueError("DeepSeek API key is required when using DeepSeek provider")
        if self.MODEL_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required when using OpenAI provider")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        validate_assignment = True
        extra = "ignore"

# 创建全局配置实例并执行验证
try:
    settings = Settings()
    settings.validate_required_configs()
    settings.validate_model_provider()
    settings.validate_api_keys()

    # 记录配置加载
    for name, value in settings.required_configs.items():
        log_config_item(name, str(value))

    logger.info("所有配置项已成功加载和验证")
except Exception as e:
    logger.error(f"配置验证失败: {str(e)}")
    raise

# 统一记录所有配置项的来源和信息
log_config_item("SUPABASE_URL", settings.SUPABASE_URL)
log_config_item("SUPABASE_SERVICE_KEY", settings.SUPABASE_SERVICE_KEY)
log_config_item("OPENAI_API_KEY", settings.OPENAI_API_KEY)
log_config_item("MODEL_NAME", settings.MODEL_NAME)
log_config_item("MODEL_PROVIDER", settings.MODEL_PROVIDER)
log_config_item("SERPAPI_API_KEY", settings.SERPAPI_API_KEY)
log_config_item("SUPABASE_JWT_SECRET", settings.SUPABASE_JWT_SECRET)
# log_config_item("OCR_API_KEY", settings.OCR_API_KEY)  # 暂时注释掉OCR相关配置

logger.info("所有必需的配置项已加载完成")
