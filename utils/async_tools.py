"""
Async Tools Wrapper for F1 Agent
Provides async execution wrapper for synchronous tools
"""
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any

logger = logging.getLogger("AsyncTools")


class AsyncToolWrapper:
    """Wrapper to run synchronous tools in async context"""
    
    def __init__(self, max_workers: int = 5):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.info(f"Async tool wrapper initialized with {max_workers} workers")
    
    async def run_sync_tool(self, func: Callable, *args, **kwargs) -> Any:
        """Run a synchronous function in a thread pool"""
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: func(*args, **kwargs)
            )
            return result
        except Exception as e:
            logger.error(f"Error running sync tool {func.__name__}: {e}")
            raise
    
    def shutdown(self):
        """Shutdown the thread pool executor"""
        self.executor.shutdown(wait=True)
        logger.info("Async tool wrapper shut down")


# Singleton instance
_wrapper_instance = None


def get_async_wrapper() -> AsyncToolWrapper:
    """Get singleton async wrapper instance"""
    global _wrapper_instance
    if _wrapper_instance is None:
        _wrapper_instance = AsyncToolWrapper()
    return _wrapper_instance
