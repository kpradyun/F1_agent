"""
Performance Metrics Tracking
Tracks agent query performance, tool usage, and cache statistics
"""

class PerformanceMetrics:
    """Track agent performance metrics"""
    
    def __init__(self):
        self.queries = 0
        self.total_time = 0.0
        self.tool_calls = {}
        self.cache_hits = 0
        self.cache_misses = 0
    
    def record_query(self, duration: float):
        """Record a query execution time"""
        self.queries += 1
        self.total_time += duration
    
    def record_tool(self, tool_name: str):
        """Record a tool call"""
        self.tool_calls[tool_name] = self.tool_calls.get(tool_name, 0) + 1
    
    def get_summary(self) -> str:
        """Generate performance summary report"""
        if self.queries == 0:
            return "No queries yet"
        
        avg_time = self.total_time / self.queries
        cache_rate = (self.cache_hits / max(1, self.cache_hits + self.cache_misses)) * 100
        
        summary = f"""
[cyan]Performance Summary:[/cyan]
- Total Queries: {self.queries}
- Avg Response Time: {avg_time:.2f}s
- Cache Hit Rate: {cache_rate:.1f}%
- Total Tool Calls: {sum(self.tool_calls.values())}
- Top Tools: {', '.join(sorted(self.tool_calls, key=self.tool_calls.get, reverse=True)[:3])}
"""
        return summary
