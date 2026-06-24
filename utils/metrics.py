"""
Performance Metrics Tracking
Tracks agent query performance and tool usage.
"""
from __future__ import annotations

__all__ = ["PerformanceMetrics"]


class PerformanceMetrics:
    """Track agent performance metrics."""

    def __init__(self) -> None:
        self.queries: int = 0
        self.total_time: float = 0.0
        self.tool_calls: dict[str, int] = {}
        self.cache_hits: int = 0
        self.cache_misses: int = 0

    def record_query(self, duration: float) -> None:
        """Record a query execution time."""
        self.queries += 1
        self.total_time += duration

    def record_tool(self, tool_name: str) -> None:
        """Record a tool call."""
        self.tool_calls[tool_name] = self.tool_calls.get(tool_name, 0) + 1

    def get_stats(self) -> dict[str, object]:
        """Return metrics as a plain dict."""
        avg = self.total_time / self.queries if self.queries else 0.0
        top_tools = sorted(self.tool_calls, key=self.tool_calls.get, reverse=True)[:3]
        return {
            "queries": self.queries,
            "avg_time": avg,
            "top_tools": top_tools,
            "total_tool_calls": sum(self.tool_calls.values()),
        }

    def get_summary(self) -> str:
        """Return Rich-formatted one-liner for inline use."""
        s = self.get_stats()
        tools_str = ", ".join(s["top_tools"]) if s["top_tools"] else "none"
        return (
            f"[cyan]Queries:[/cyan] {s['queries']} | "
            f"[cyan]Avg:[/cyan] {s['avg_time']:.2f}s | "
            f"[cyan]Top tools:[/cyan] {tools_str}"
        )
