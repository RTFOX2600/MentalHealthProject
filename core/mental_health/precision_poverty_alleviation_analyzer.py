import warnings
from datetime import datetime
from typing import Dict, List
import io

import numpy as np
import pandas as pd


warnings.filterwarnings('ignore')


class PrecisionPovertyAlleviationAnalyzer:
    """
    精准扶贫分析器
    基于食堂消费等经济指标识别需要经济帮助的学生
    """

    def __init__(self, params=None):
        self.students_info = {}
        self.data = {}
        
        # 默认参数
        self.params = {
            'poverty_threshold': 300.0,  # 低于此金额判定为潜在困难
            'trend_threshold': -50.0     # 消费趋势下降超过此值需警惕
        }
        if params:
            # 强制类型转换，防止前端传入字符串导致 numpy 比较报错
            for k, v in params.items():
                try:
                    self.params[k] = float(v)
                except (ValueError, TypeError):
                    pass

    def load_data_from_dict(self, data_dict: Dict):
        """从字典加载数据"""
        self.data['canteen'] = pd.DataFrame(data_dict.get('canteen', []))
        self.data['school_gate'] = pd.DataFrame(data_dict.get('school_gate', []))

        # 转换时间格式
        if len(self.data['canteen']) > 0 and '年份-月份' in self.data['canteen'].columns:
            self.data['canteen']['月份'] = pd.to_datetime(
                self.data['canteen']['年份-月份'] + '-01', errors='coerce'
            )

        if len(self.data['school_gate']) > 0 and '校门进出时间' in self.data['school_gate'].columns:
            self.data['school_gate']['校门进出时间'] = pd.to_datetime(
                self.data['school_gate']['校门进出时间'], errors='coerce'
            )

        print(f"{self.__class__.__name__} 数据加载完成！"
              f"食堂消费记录: {len(self.data.get('canteen', []))} 条。"
              f"校门进出记录: {len(self.data.get('school_gate', []))} 条。")

    def _calculate_poverty_indicators(self, student_id: str) -> Dict:
        """计算学生的贫困指标"""
        indicators = {'学号': student_id}

        # 1. 食堂消费分析
        if not self.data['canteen'].empty:
            canteen_data = self.data['canteen'][self.data['canteen']['学号'] == student_id]
            if not canteen_data.empty:
                indicators['月均消费'] = canteen_data['食堂消费额度（本月）'].mean()
                indicators['最低月消费'] = canteen_data['食堂消费额度（本月）'].min()
                indicators['消费波动'] = canteen_data['食堂消费额度（本月）'].std()

                # 低消费月份数（基于参数阈值）
                poverty_limit = float(self.params.get('poverty_threshold', 300))
                low_months = (canteen_data['食堂消费额度（本月）'] < poverty_limit).sum()
                # noinspection PyTypeChecker
                indicators['低消费月份数'] = int(low_months)

                # 消费趋势
                if len(canteen_data) > 1:
                    sorted_data = canteen_data.sort_values('月份')
                    values = sorted_data['食堂消费额度（本月）'].values
                    x = np.arange(len(values))
                    slope, _ = np.polyfit(x, values, 1)
                    indicators['消费趋势'] = slope
                else:
                    # noinspection PyTypeChecker
                    indicators['消费趋势'] = 0

        # 2. 校门进出分析（作为辅助指标）
        if not self.data['school_gate'].empty:
            gate_data = self.data['school_gate'][self.data['school_gate']['学号'] == student_id]
            if not gate_data.empty:
                # 周末外出次数（周末很少外出可能是经济原因）
                weekend_out = gate_data[
                    (gate_data['进出方向'].astype(str).str.contains('出|out|离开', case=False)) &
                    (gate_data['校门进出时间'].dt.weekday >= 5)
                    ]
                date_count = len(gate_data['校门进出时间'].dt.date.unique())
                weekend_dates = len([d for d in gate_data['校门进出时间'].dt.date.unique()
                                     if pd.Timestamp(d).weekday() >= 5])
                # noinspection PyTypeChecker
                indicators['周末外出频率'] = len(weekend_out) / max(1, weekend_dates) if weekend_dates > 0 else 0

        return indicators

    def _determine_poverty_level(self, indicators: Dict) -> tuple:
        """
        判定贫困等级
        """
        if '月均消费' not in indicators:
            return '无数据', []

        avg_consumption = indicators['月均消费']
        min_consumption = indicators.get('最低月消费', avg_consumption)
        low_months = indicators.get('低消费月份数', 0)
        trend = indicators.get('消费趋势', 0)
        
        poverty_limit = float(self.params.get('poverty_threshold', 300))
        trend_limit = float(self.params.get('trend_threshold', -50.0))

        reasons = []
        level = '正常'

        # 特别困难判定 (基于动态阈值的 80%)
        if avg_consumption < (poverty_limit * 0.83): # 约 250
            level = '特别困难'
            reasons.append(f"月均消费仅{avg_consumption:.1f}元，远低于正常水平")
        elif min_consumption < (poverty_limit * 0.66) and low_months >= 2: # 约 200
            level = '特别困难'
            reasons.append(f"有{low_months}个月消费低于{poverty_limit}元，最低仅{min_consumption:.1f}元")
        # 困难判定 (基于动态阈值的 1.16 倍)
        elif avg_consumption < (poverty_limit * 1.16): # 约 350
            level = '困难'
            reasons.append(f"月均消费{avg_consumption:.1f}元，低于基本生活水平")
        # 一般困难判定 (基于动态阈值的 1.5 倍)
        elif avg_consumption < (poverty_limit * 1.5): # 约 450
            level = '一般困难'
            reasons.append(f"月均消费{avg_consumption:.1f}元，偏低")

        # 补充其他原因
        if level != '正常':
            if trend < trend_limit:
                reasons.append("消费呈明显下降趋势")
            if low_months >= 3:
                reasons.append(f"有{low_months}个月消费低于{poverty_limit}元")
            if '周末外出频率' in indicators and indicators['周末外出频率'] < 1:
                reasons.append("周末外出活动明显减少")

        return level, reasons

    @staticmethod
    def _generate_assistance_suggestions(level: str, indicators: Dict) -> str:
        """生成帮助建议"""
        suggestions = []

        if level == '特别困难':
            suggestions.append("建议立即启动一级助学金")
            suggestions.append("提供勤工助学岗位")
            suggestions.append("关注心理健康和学业情况")
        elif level == '困难':
            suggestions.append("建议申请二级助学金")
            suggestions.append("推荐勤工助学机会")
            suggestions.append("定期跟踪生活情况")
        elif level == '一般困难':
            suggestions.append("可申请三级助学金")
            suggestions.append("提供勤工助学信息")

        return "；".join(suggestions) if suggestions else "暂无需要"

    def analyze_students(self) -> List[Dict]:
        """分析所有学生的经济状况"""
        if self.data['canteen'].empty:
            return []

        all_students = self.data['canteen']['学号'].unique()
        results = []

        for student_id in all_students:
            indicators = self._calculate_poverty_indicators(student_id)
            level, reasons = self._determine_poverty_level(indicators)

            # 只记录需要帮助的学生
            if level != '正常' and level != '无数据':
                suggestions = self._generate_assistance_suggestions(level, indicators)

                results.append({
                    '学号': student_id,
                    '困难等级': level,
                    '月均消费': round(indicators.get('月均消费', 0), 2),
                    '最低月消费': round(indicators.get('最低月消费', 0), 2),
                    '低消费月份数': indicators.get('低消费月份数', 0),
                    '消费趋势': round(indicators.get('消费趋势', 0), 2),
                    '困难原因': '；'.join(reasons),
                    '帮助建议': suggestions
                })

        # 按困难等级排序
        level_order = {'特别困难': 0, '困难': 1, '一般困难': 2}
        results.sort(key=lambda x: (level_order.get(x['困难等级'], 99), x['月均消费']))

        self.students_info = {r['学号']: r for r in results}
        return results

    @staticmethod
    def _generate_report_excel(analysis_results: List[Dict]) -> io.BytesIO:
        """生成精准扶贫分析报告"""
        if not analysis_results:
            df = pd.DataFrame([{
                '学号': '无需帮助学生',
                '困难等级': '-',
                '月均消费': 0,
                '备注': '所有学生经济状况良好'
            }])
        else:
            df = pd.DataFrame(analysis_results)

        output = io.BytesIO()
        # noinspection PyTypeChecker
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='精准扶贫分析', index=False)

            worksheet = writer.sheets['精准扶贫分析']
            column_widths = {
                'A': 15, 'B': 12, 'C': 12, 'D': 12,
                'E': 15, 'F': 12, 'G': 40, 'H': 40
            }
            for col, width in column_widths.items():
                worksheet.column_dimensions[col].width = width

        output.seek(0)
        return output

    def start_analyze(self, data_dict: Dict) -> Dict:
        """分析入口"""
        try:
            self.load_data_from_dict(data_dict)
            results = self.analyze_students()

            # 统计摘要
            level_distribution = {}
            for r in results:
                level = r['困难等级']
                level_distribution[level] = level_distribution.get(level, 0) + 1

            total_students = len(self.data['canteen']['学号'].unique()) if not self.data['canteen'].empty else 0

            summary = {
                '分析时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                '总学生数': total_students,
                '需帮助学生数': len(results),
                '困难等级分布': level_distribution,
                '帮助覆盖率': f"{len(results) / max(1, total_students) * 100:.1f}%"
            }

            excel_file = self._generate_report_excel(results)

            return {
                'status': 'success',
                'summary': summary,
                'excel_data': excel_file.getvalue(),
                'filename': f'精准扶贫分析报告_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'分析失败: {str(e)}'
            }
