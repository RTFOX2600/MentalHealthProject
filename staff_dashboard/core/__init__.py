"""
staff_dashboard.core 模块
包含数据统计相关的核心算法
"""

from .statistics import (
    calculate_canteen_stats_realtime,
    calculate_gate_stats_realtime,
    calculate_dormitory_stats_realtime,
    calculate_network_stats_realtime,
    calculate_academic_stats_realtime,
    aggregate_canteen_stats,
    aggregate_gate_stats,
    aggregate_dormitory_stats,
    aggregate_network_stats,
    aggregate_academic_stats,
)

__all__ = [
    'calculate_canteen_stats_realtime',
    'calculate_gate_stats_realtime',
    'calculate_dormitory_stats_realtime',
    'calculate_network_stats_realtime',
    'calculate_academic_stats_realtime',
    'aggregate_canteen_stats',
    'aggregate_gate_stats',
    'aggregate_dormitory_stats',
    'aggregate_network_stats',
    'aggregate_academic_stats',
]
