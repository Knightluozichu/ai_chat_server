"""
配置模块的单元测试
"""
import os
import tempfile
import pytest
from app.config import Settings

def test_settings_load(monkeypatch):
    """
    测试配置加载功能
    """
    # 创建临时 .env 文件，写入模拟环境变量
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write("SUPABASE_URL=https://example.supabase.co\n")
        tmp.write("SUPABASE_SERVICE_KEY=service_key_value\n")
        tmp.write("OPENAI_API_KEY=openai_key_value\n")
        tmp.flush()

        # 设置环境变量指向临时文件
        monkeypatch.setenv("ENV_FILE", tmp.name)

        # 实例化 Settings（使用临时 .env 文件）
        settings = Settings(_env_file=tmp.name)
        
        # 验证配置项是否正确加载
        assert settings.SUPABASE_URL == "https://example.supabase.co"
        assert settings.SUPABASE_SERVICE_KEY == "service_key_value"
        assert settings.OPENAI_API_KEY == "openai_key_value"
        assert settings.MODEL_NAME == "gpt-3.5-turbo"  # 默认值测试

def test_settings_missing_required(monkeypatch):
    """
    测试缺少必要配置项时的错误处理
    """
    # 创建缺少必要配置的临时 .env 文件
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write("OPENAI_API_KEY=test_key\n")  # 只提供一个必要配置
        tmp.flush()
        
        monkeypatch.setenv("ENV_FILE", tmp.name)
        
        # 验证缺少必要配置时会抛出异常
        with pytest.raises(Exception):
            Settings(_env_file=tmp.name)
