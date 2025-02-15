
import functools
import asyncio
import logging

logger = logging.getLogger(__name__)

def async_retry(retries=3, delay=1):
    """异步重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"第{attempt + 1}次尝试失败: {str(e)}")
                    if attempt < retries - 1:
                        await asyncio.sleep(delay * (attempt + 1))
            raise last_exception
        return wrapper
    return decorator
