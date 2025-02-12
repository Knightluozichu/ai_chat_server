from setuptools import setup, find_packages

setup(
    name="ai_chat_server",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.5.2",
        "supabase>=2.0.3",
        "langchain-openai>=0.0.2",
        "langchain-core>=0.1.7",
        "pytest>=8.3.4"
    ],
)
