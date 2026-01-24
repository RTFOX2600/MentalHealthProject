"""学生思想健康分析系统 - 模块入口

本模块提供三个核心分析器类：
1. MentalHealthAnalyzer - 综合思想健康分析
2. PrecisionIdeologyAnalyzer - 精准思政分析
3. PrecisionPovertyAlleviationAnalyzer - 精准扶贫分析

使用示例：
    from core.mental_health.analyse import MentalHealthAnalyzer
    
    analyzer = MentalHealthAnalyzer(params={'contamination': 0.15})
    result = analyzer.analyze_comprehensive(data_dict)
"""

from core.mental_health.mental_health_analyzer import MentalHealthAnalyzer
from core.mental_health.precision_ideology_analyzer import PrecisionIdeologyAnalyzer
from core.mental_health.precision_poverty_alleviation_analyzer import PrecisionPovertyAlleviationAnalyzer

__all__ = [
    'MentalHealthAnalyzer',
    'PrecisionIdeologyAnalyzer',
    'PrecisionPovertyAlleviationAnalyzer',
]
