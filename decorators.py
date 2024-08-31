import time
from functools import wraps
from loguru import logger

def async_timing_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"{func.__name__} 실행 시간: {execution_time:.2f}초")
        return result
    return wrapper