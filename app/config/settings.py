from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 原有配置项
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/db"
    DEBUG: bool = False
    
    # 新增采购领域配置
    PROCUREMENT_DOMAIN_DICT_PATH: Path = Path(__file__).parent.parent / "resources/procurement_dicts/domain_terms.json"
    INTENT_MODEL_PATH: Path = Path(__file__).parent.parent / "models/bert-wwm-procurement"
    PROCUREMENT_RISK_MODE: str = "LOCAL"
    LOCAL_RISK_RULES_PATH: Path = Path(__file__).parent.parent / "resources/procurement_dicts/risk_rules.json"
    POLICY_MONITOR_ENDPOINT: str = "http://policy-monitor.procurement.internal"
    CHAT_INTENT_ENABLED: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
