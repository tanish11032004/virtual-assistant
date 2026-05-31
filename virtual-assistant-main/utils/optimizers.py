from typing import List, Dict, Any
from functools import lru_cache

class QueryOptimizer:
    """SQL query optimization utilities"""
    
    @staticmethod
    def optimize_select(fields: List[str], table: str, conditions: Dict[str, Any] = None) -> str:
        """Generate optimized SELECT queries"""
        query = f"SELECT {', '.join(fields)} FROM {table}"
        if conditions:
            where_clause = " AND ".join(f"{k} = %s" for k in conditions.keys())
            query += f" WHERE {where_clause}"
        query += " USE INDEX (PRIMARY)"  # Use primary index
        return query

    @staticmethod
    @lru_cache(maxsize=100)
    def build_cached_query(query_type: str, table: str, fields: tuple) -> str:
        """Cache frequently used queries"""
        return f"SELECT {', '.join(fields)} FROM {table}"

class DataOptimizer:
    """Data structure optimization utilities"""
    
    @staticmethod
    def optimize_list(data: List[Any]) -> List[Any]:
        """Optimize list operations"""
        return list(set(data))  # Remove duplicates

    @staticmethod
    def optimize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize dictionary operations"""
        return {k: v for k, v in data.items() if v is not None}
