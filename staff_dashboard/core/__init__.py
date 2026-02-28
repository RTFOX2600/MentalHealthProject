"""
staff_dashboard.core 模块
包含数据统计相关的核心算法
"""

from .statistics import (
    calculate_canteen_stats,
    calculate_gate_stats,
    calculate_dormitory_stats,
    calculate_network_stats,
    calculate_academic_stats,
)

__all__ = [
    'calculate_canteen_stats',
    'calculate_gate_stats',
    'calculate_dormitory_stats',
    'calculate_network_stats',
    'calculate_academic_stats',
]
