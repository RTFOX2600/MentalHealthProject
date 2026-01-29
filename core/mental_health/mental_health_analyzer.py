from datetime import datetime
from typing import Dict, List, Any
import io
import warnings
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from starlette.exceptions import HTTPException


warnings.filterwarnings('ignore')


class MentalHealthAnalyzer:
    def __init__(self, params=None):
        """
        初始化分析器
        """
        self.data = {}
        self.students_info = {}
        self.at_risk_students = []
        # 默认参数
        self.params = {
            'contamination': 0.15,
            'night_start': 23
        }
        if params:
            # 强制类型转换，防止前端传入字符串导致 numpy 比较报错
            for k, v in params.items():
                try:
                    if k == 'night_start':
                        self.params[k] = int(v)
                    else:
                        self.params[k] = float(v)
                except (ValueError, TypeError):
                    pass

    def load_data_from_dict(self, data_dict: Dict):
        """
        从字典加载数据（替代从文件加载）
        """
        try:
            # 从字典加载各个表格
            self.data['canteen'] = pd.DataFrame(data_dict.get('canteen', []))
            self.data['school_gate'] = pd.DataFrame(data_dict.get('school_gate', []))
            self.data['dorm_gate'] = pd.DataFrame(data_dict.get('dorm_gate', []))
            self.data['network'] = pd.DataFrame(data_dict.get('network', []))
            self.data['grades'] = pd.DataFrame(data_dict.get('grades', []))

            print(f"{self.__class__.__name__} 数据加载完成！"
                  f"食堂消费记录: {len(self.data.get('canteen', []))} 条。"
                  f"校门进出记录: {len(self.data.get('school_gate', []))} 条。"
                  f"寝室门禁记录: {len(self.data.get('dorm_gate', []))} 条。"
                  f"校园网记录: {len(self.data.get('network', []))} 条。"
                  f"成绩记录: {len(self.data.get('grades', []))} 条。")

            # 转换时间格式
            self._preprocess_data()

            return True

        except Exception as e:
            print(f"加载数据失败: {e}")
            raise HTTPException(status_code=400, detail=f"数据加载失败: {str(e)}")

    def _preprocess_data(self):
        """数据预处理 - 强制转换为本地时区"""
        # 转换时间列
        time_columns = {
            'school_gate': '校门进出时间',
            'dorm_gate': '寝室进出时间',
            'network': '开始时间'
        }

        for table, cols in time_columns.items():
            if table in self.data and len(self.data[table]) > 0:
                if cols in self.data[table].columns:
                    series = pd.to_datetime(self.data[table][cols], errors='coerce')
                    # 如果时间带有偏差（来自数据库），转换为上海时区；如果是naive，保持原样
                    if series.dt.tz is not None:
                        series = series.dt.tz_convert('Asia/Shanghai')
                    self.data[table][cols] = series

        # 提取月份信息
        if 'canteen' in self.data and '年份-月份' in self.data['canteen'].columns and len(self.data['canteen']) > 0:
            self.data['canteen']['月份'] = pd.to_datetime(
                self.data['canteen']['年份-月份'] + '-01', errors='coerce'
            )

        # 处理成绩表的月份信息
        if 'grades' in self.data and '年份-月份' in self.data['grades'].columns and len(self.data['grades']) > 0:
            self.data['grades']['月份'] = pd.to_datetime(
                self.data['grades']['年份-月份'] + '-01', errors='coerce'
            )

    def analyze_student_behavior(self):
        """分析学生行为模式"""
        # 获取所有学生
        all_students = set()
        for table_name, table_data in self.data.items():
            if '学号' in table_data.columns and len(table_data) > 0:
                all_students.update(table_data['学号'].unique())

        all_students = list(all_students)

        # 为每个学生计算行为指标
        student_metrics = {}

        for student_id in all_students:
            metrics = self._calculate_student_metrics(student_id)
            if metrics:
                student_metrics[student_id] = metrics

        self.students_info = student_metrics
        return student_metrics

    def _calculate_student_metrics(self, student_id: str) -> Dict:
        """计算单个学生的行为指标"""
        metrics: dict[str, Any] = {'学号': student_id}

        try:
            # 1. 食堂消费分析
            if len(self.data['canteen']) > 0:
                canteen_data: pd.DataFrame = self.data['canteen'][self.data['canteen']['学号'] == student_id]
                if not canteen_data.empty:
                    metrics['食堂消费_月均'] = canteen_data['食堂消费额度（本月）'].mean()
                    metrics['食堂消费_波动'] = canteen_data['食堂消费额度（本月）'].std()
                    if len(canteen_data) > 1:
                        metrics['食堂消费_趋势'] = self._calculate_trend(
                            canteen_data.sort_values('月份')['食堂消费额度（本月）'].values
                        )
                    else:
                        metrics['食堂消费_趋势'] = 0
                    metrics['食堂消费_最低月'] = canteen_data['食堂消费额度（本月）'].min()
                    metrics['食堂消费_连续低消费'] = self._count_low_consumption_months(
                        canteen_data['食堂消费额度（本月）'].values
                    )

            # 2. 校门进出分析
            if len(self.data['school_gate']) > 0:
                school_gate_data = self.data['school_gate'][self.data['school_gate']['学号'] == student_id]
                if not school_gate_data.empty:
                    date_count = len(school_gate_data['校门进出时间'].dt.date.unique())
                    metrics['校门_日均进出'] = len(school_gate_data) / max(1, date_count)

                    # 夜间外出 (参数化起始时间，校门外出通常从20:00开始计算，这里取21)
                    gate_night_start = 21
                    night_out = school_gate_data[
                        (school_gate_data['进出方向'].astype(str).str.contains('出|out|离开', case=False)) &
                        ((school_gate_data['校门进出时间'].dt.hour >= gate_night_start) |
                         (school_gate_data['校门进出时间'].dt.hour < 6))
                        ]
                    metrics['校门_夜间外出次数'] = len(night_out)

                    # 周末外出比例
                    total_out_mask = school_gate_data['进出方向'].astype(str).str.contains('出|out|离开', case=False)
                    weekend_out = school_gate_data[
                        total_out_mask &
                        (school_gate_data['校门进出时间'].dt.weekday >= 5)
                        ]
                    total_out_count = len(school_gate_data[total_out_mask])
                    metrics['校门_周末外出比例'] = len(weekend_out) / max(1, total_out_count)

                    # 长时间外出（超过6小时）
                    metrics['校门_长时间外出比例'] = self._calculate_long_absence_ratio(school_gate_data)

            # 3. 寝室门禁分析
            if len(self.data['dorm_gate']) > 0:
                dorm_gate_data = self.data['dorm_gate'][self.data['dorm_gate']['学号'] == student_id]
                if not dorm_gate_data.empty:
                    date_count = len(dorm_gate_data['寝室进出时间'].dt.date.unique())
                    metrics['寝室_日均进出'] = len(dorm_gate_data) / max(1, date_count)

                    # 深夜进出 (参数化起始时间)
                    late_night = dorm_gate_data[
                        (dorm_gate_data['寝室进出时间'].dt.hour >= int(self.params['night_start'])) |
                        (dorm_gate_data['寝室进出时间'].dt.hour < 6)
                        ]
                    metrics['寝室_深夜进出次数'] = len(late_night)

                    # 规律性（标准差越小越规律）
                    if len(dorm_gate_data) > 1:
                        return_times = dorm_gate_data[
                            dorm_gate_data['进出方向'] == '进'
                            ]['寝室进出时间'].dt.hour
                        if not return_times.empty:
                            metrics['寝室_归寝规律性'] = return_times.std()
                        else:
                            metrics['寝室_归寝规律性'] = np.nan

            # 4. 网络访问分析
            if len(self.data['network']) > 0:
                network_data = self.data['network'][self.data['network']['学号'] == student_id]
                if not network_data.empty:
                    date_count = len(network_data['开始时间'].dt.date.unique())
                    metrics['网络_日均访问次数'] = len(network_data) / max(1, date_count)

                    # 夜间访问 (参数化起始时间)
                    night_access = network_data[
                        (network_data['开始时间'].dt.hour >= int(self.params['night_start'])) |
                        (network_data['开始时间'].dt.hour < 6)
                        ]
                    metrics['网络_夜间访问比例'] = len(night_access) / max(1, len(network_data))

                    # VPN使用统计
                    if '是否使用VPN' in network_data.columns:
                        vpn_count = (network_data['是否使用VPN'] == '是').sum()
                        metrics['网络_VPN使用比例'] = vpn_count / max(1, len(network_data))

                    # 访问域名多样性（只统计非VPN访问）
                    if '访问域名' in network_data.columns:
                        non_vpn_data = network_data[network_data['访问域名'] != '']
                        if not non_vpn_data.empty:
                            unique_domains = non_vpn_data['访问域名'].nunique()
                            metrics['网络_域名多样性'] = unique_domains

                            # 访问时段分布
                            access_hours = network_data['开始时间'].dt.hour
                            metrics['网络_访问时段集中度'] = access_hours.std() if len(access_hours) > 1 else 0

            # 5. 成绩分析
            if 'grades' in self.data and len(self.data['grades']) > 0:
                grades_data = self.data['grades'][self.data['grades']['学号'] == student_id]
                if not grades_data.empty:
                    # 获取所有科目列（排除学号和年份-月份）
                    grade_columns = [col for col in grades_data.columns
                                     if col not in ['学号', '年份-月份', '月份']]

                    if grade_columns:
                        # 计算平均成绩
                        all_grades = grades_data[grade_columns].values.flatten()

                        # 安全地转换为数值类型并移除NaN值
                        all_grades_numeric = []
                        for grade in all_grades:
                            try:
                                if pd.notna(grade):  # 使用pandas的notna更安全
                                    grade_float = float(grade)
                                    all_grades_numeric.append(grade_float)
                            except (ValueError, TypeError):
                                # 跳过无法转换为数字的值
                                continue

                        all_grades = np.array(all_grades_numeric)

                        if len(all_grades) > 0:
                            metrics['成绩_平均分'] = np.mean(all_grades)
                            metrics['成绩_最低分'] = np.min(all_grades)
                            metrics['成绩_波动'] = np.std(all_grades)

                            # 不及格科目数量（低于60分）
                            metrics['成绩_不及格科次'] = int(np.sum(all_grades < 60))

                            # 成绩趋势分析（如果有多个时间点）
                            if len(grades_data) > 1:
                                # 按月份排序
                                grades_sorted = grades_data.sort_values('月份')
                                # 计算每个时间点的平均成绩
                                avg_grades_per_month = []
                                for _, row in grades_sorted.iterrows():
                                    month_grades = []
                                    for col in grade_columns:
                                        try:
                                            if pd.notna(row[col]):
                                                month_grades.append(float(row[col]))
                                        except (ValueError, TypeError):
                                            continue
                                    if month_grades:
                                        avg_grades_per_month.append(np.mean(month_grades))

                                if len(avg_grades_per_month) > 1:
                                    metrics['成绩_趋势'] = self._calculate_trend(np.array(avg_grades_per_month))
                                else:
                                    metrics['成绩_趋势'] = 0
                            else:
                                metrics['成绩_趋势'] = 0

                            # 计算低分科目比例
                            low_score_count = np.sum(all_grades < 70)  # 低于70分算低分
                            metrics['成绩_低分比例'] = low_score_count / len(all_grades) if len(all_grades) > 0 else 0

        except Exception as e:
            print(f"计算学生 {student_id} 指标时出错: {e}")
            # 返回基础信息
            return {'学号': student_id}

        return metrics

    @staticmethod
    def _calculate_trend(values: np.ndarray) -> float:
        """计算趋势（线性回归斜率）"""
        if len(values) < 2:
            return 0
        try:
            x = np.arange(len(values))
            slope, _ = np.polyfit(x, values, 1)
            return slope
        except:
            return 0

    @staticmethod
    def _count_low_consumption_months(values: np.ndarray, threshold: float = 300) -> int:
        """计算连续低消费月数"""
        if len(values) == 0:
            return 0

        max_consecutive = 0
        current_consecutive = 0

        for value in values:
            if value < threshold:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    @staticmethod
    def _calculate_long_absence_ratio(gate_data: pd.DataFrame) -> float:
        """计算长时间外出比例"""
        if len(gate_data) < 2:
            return 0

        try:
            # 按时间排序
            sorted_data = gate_data.sort_values('校门进出时间')

            long_absences = 0
            total_out = 0

            for i in range(len(sorted_data) - 1):
                if (sorted_data.iloc[i]['进出方向'] == '出' and
                        sorted_data.iloc[i + 1]['进出方向'] == '进'):

                    out_time = sorted_data.iloc[i]['校门进出时间']
                    in_time = sorted_data.iloc[i + 1]['校门进出时间']

                    if (in_time - out_time).total_seconds() / 3600 > 6:  # 超过6小时
                        long_absences += 1
                    total_out += 1

            return long_absences / max(1, total_out)
        except:
            return 0

    def identify_at_risk_students(self):
        """
        识别需要关注的学生
        """
        if not self.students_info:
            self.analyze_student_behavior()

        # 转换为DataFrame
        df_metrics = pd.DataFrame(self.students_info.values())

        if len(df_metrics) == 0:
            return []

        # 处理缺失值
        df_metrics.fillna(df_metrics.median(numeric_only=True), inplace=True)

        # 选择特征列
        feature_cols = [
            '食堂消费_月均', '食堂消费_波动', '食堂消费_趋势',
            '食堂消费_最低月', '食堂消费_连续低消费',
            '校门_日均进出', '校门_夜间外出次数', '校门_周末外出比例',
            '校门_长时间外出比例', '寝室_日均进出', '寝室_深夜进出次数',
            '寝室_归寝规律性', '网络_日均访问次数', '网络_夜间访问比例',
            '网络_VPN使用比例', '网络_域名多样性', '网络_访问时段集中度',
            '成绩_平均分', '成绩_最低分', '成绩_波动', '成绩_不及格科次',
            '成绩_趋势', '成绩_低分比例'
        ]

        # 只保留存在的列
        available_cols = [col for col in feature_cols if col in df_metrics.columns]

        if not available_cols:
            print(f"{self.__class__.__name__} 没有可用的特征列！")
            return []

        X = df_metrics[available_cols]

        # 标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # 使用孤立森林方法（应用前端传来的污染率参数）
        try:
            iso_forest = IsolationForest(
                contamination=float(self.params.get('contamination', 0.1)),
            )
            labels = iso_forest.fit_predict(X_scaled)
            at_risk_indices = np.where(labels == -1)[0]
        except:
            # 如果失败，根据比例选择前 N 个
            ratio = float(self.params.get('contamination', 0.1))
            at_risk_indices = list(range(max(1, int(len(X_scaled) * ratio))))

        # 获取需要关注的学生
        at_risk_students = []
        for idx in at_risk_indices:
            student_info = df_metrics.iloc[idx].to_dict()

            # 计算风险原因
            risk_reasons = self._analyze_risk_reasons(student_info)

            # 计算风险等级
            risk_level = self._calculate_risk_level(student_info, risk_reasons)

            at_risk_students.append({
                '学号': student_info['学号'],
                '风险等级': risk_level,
                '风险原因': risk_reasons,
                '行为指标': student_info
            })

        self.at_risk_students = at_risk_students
        return at_risk_students

    @staticmethod
    def _isolation_forest_method(X_scaled: np.ndarray, df_metrics: pd.DataFrame) -> List[int]:
        """孤立森林方法"""
        try:
            iso_forest = IsolationForest(
                contamination=0.15,  # 异常比例
            )
            labels = iso_forest.fit_predict(X_scaled)
            at_risk_indices = np.where(labels == -1)[0]  # -1表示异常
            return at_risk_indices.tolist()
        except:
            # 如果孤立森林失败，返回前15%作为关注对象
            return list(range(max(1, len(X_scaled) // 6)))

    @staticmethod
    def _analyze_risk_reasons(student_info: Dict) -> List[str]:
        """分析风险原因"""
        reasons = []

        # 食堂消费相关
        if '食堂消费_月均' in student_info and student_info['食堂消费_月均'] < 300:
            reasons.append("月均食堂消费过低（低于300元）")

        if '食堂消费_连续低消费' in student_info and student_info['食堂消费_连续低消费'] >= 2:
            reasons.append(f"连续{student_info['食堂消费_连续低消费']}个月低消费")

        if '食堂消费_趋势' in student_info and student_info['食堂消费_趋势'] < -50:
            reasons.append("消费呈明显下降趋势")

        # 校门进出相关
        if '校门_夜间外出次数' in student_info and student_info['校门_夜间外出次数'] > 5:
            reasons.append("夜间外出次数过多")

        if '校门_周末外出比例' in student_info and student_info['校门_周末外出比例'] > 0.8:
            reasons.append("周末外出比例过高")

        if '校门_长时间外出比例' in student_info and student_info['校门_长时间外出比例'] > 0.5:
            reasons.append("长时间外出比例过高")

        # 寝室门禁相关
        if '寝室_深夜进出次数' in student_info and student_info['寝室_深夜进出次数'] > 10:
            reasons.append("深夜进出寝室次数过多")

        if '寝室_归寝规律性' in student_info and student_info['寝室_归寝规律性'] > 3:
            reasons.append("归寝时间不规律")

        # 网络使用相关
        if '网络_日均访问次数' in student_info and student_info['网络_日均访问次数'] > 50:  # 过度访问
            reasons.append("日均网络访问次数过多")

        if '网络_夜间访问比例' in student_info and student_info['网络_夜间访问比例'] > 0.3:
            reasons.append("夜间网络访问比例过高")

        if '网络_VPN使用比例' in student_info and student_info['网络_VPN使用比例'] > 0.5:
            reasons.append("VPN使用频率较高")

        # 成绩相关
        if '成绩_平均分' in student_info and student_info['成绩_平均分'] < 65:
            reasons.append(f"平均成绩过低（{student_info['成绩_平均分']:.1f}分）")

        if '成绩_不及格科次' in student_info and student_info['成绩_不及格科次'] >= 2:
            reasons.append(f"有{int(student_info['成绩_不及格科次'])}科次不及格")

        if '成绩_趋势' in student_info and student_info['成绩_趋势'] < -5:
            reasons.append("成绩呈明显下降趋势")

        if '成绩_低分比例' in student_info and student_info['成绩_低分比例'] > 0.5:
            reasons.append(f"超过半数科目成绩偏低（{student_info['成绩_低分比例'] * 100:.0f}%）")

        # 如果没有特定原因，添加综合原因
        if not reasons:
            reasons.append("综合行为模式异常")

        return reasons

    @staticmethod
    def _calculate_risk_level(student_info: Dict, risk_reasons: List[str]) -> str:
        """计算风险等级"""
        risk_score = 0

        # 食堂消费
        if '食堂消费_月均' in student_info and student_info['食堂消费_月均'] < 300:
            risk_score += 2
        elif '食堂消费_月均' in student_info and student_info['食堂消费_月均'] < 500:
            risk_score += 1

        if '食堂消费_连续低消费' in student_info and student_info['食堂消费_连续低消费'] >= 2:
            risk_score += student_info['食堂消费_连续低消费']

        # 夜间活动
        if '校门_夜间外出次数' in student_info and student_info['校门_夜间外出次数'] > 5:
            risk_score += 2

        if '寝室_深夜进出次数' in student_info and student_info['寝室_深夜进出次数'] > 10:
            risk_score += 2

        if '网络_夜间访问比例' in student_info and student_info['网络_夜间访问比例'] > 0.3:
            risk_score += 1

        # 规律性
        if '寝室_归寝规律性' in student_info and student_info['寝室_归寝规律性'] > 3:
            risk_score += 1

        # 成绩相关
        if '成绩_平均分' in student_info:
            if student_info['成绩_平均分'] < 60:
                risk_score += 3
            elif student_info['成绩_平均分'] < 70:
                risk_score += 2

        if '成绩_不及格科次' in student_info and student_info['成绩_不及格科次'] >= 2:
            risk_score += student_info['成绩_不及格科次']

        if '成绩_趋势' in student_info and student_info['成绩_趋势'] < -5:
            risk_score += 2

        # 根据分数确定等级
        if risk_score >= 5:
            return "高风险"
        elif risk_score >= 3:
            return "中风险"
        else:
            return "低风险"

    def _generate_detailed_analysis_excel(self) -> io.BytesIO:
        """
        生成学生思想健康详细分析Excel文件
        返回BytesIO对象供前端下载
        """
        if not self.at_risk_students:
            # 如果没有识别到风险学生，创建空报告
            detailed_results = [{
                '学号': '无风险学生',
                '风险等级': '无风险',
                '风险原因': '[]',
                '食堂消费_月均': 0,
                '校门_夜间外出次数': 0,
                '寝室_深夜进出次数': 0,
                '网络_夜间在线比例': 0,
                '建议谈话重点': '无需特别关注'
            }]
        else:
            # 生成详细分析结果
            detailed_results = []
            for student in self.at_risk_students:
                detailed_results.append({
                    '学号': student['学号'],
                    '风险等级': student['风险等级'],
                    '风险原因': '；'.join(student['风险原因']),
                    '食堂消费_月均': round(student['行为指标'].get('食堂消费_月均', 0), 2),
                    '校门_夜间外出次数': int(student['行为指标'].get('校门_夜间外出次数', 0)),
                    '寝室_深夜进出次数': int(student['行为指标'].get('寝室_深夜进出次数', 0)),
                    '网络_夜间访问比例': round(student['行为指标'].get('网络_夜间访问比例', 0), 3),
                    '成绩_平均分': round(student['行为指标'].get('成绩_平均分', 0), 1),
                    '成绩_不及格科次': int(student['行为指标'].get('成绩_不及格科次', 0)),
                    '建议谈话重点': self._get_talking_points(student)
                })

        # 创建DataFrame
        detailed_df = pd.DataFrame(detailed_results)

        # 创建Excel文件在内存中
        output = io.BytesIO()

        # noinspection PyTypeChecker
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            detailed_df.to_excel(writer, sheet_name='思想健康分析', index=False)

            # 获取工作表进行格式调整
            worksheet = writer.sheets['思想健康分析']

            # 设置列宽
            column_widths = {
                'A': 15,  # 学号
                'B': 10,  # 风险等级
                'C': 50,  # 风险原因
                'D': 15,  # 食堂消费
                'E': 18,  # 校门夜间外出
                'F': 18,  # 寝室深夜进出
                'G': 18,  # 网络夜间在线
                'H': 12,  # 成绩平均分
                'I': 15,  # 成绩不及格科次
                'J': 35  # 建议谈话重点
            }

            for col, width in column_widths.items():
                worksheet.column_dimensions[col].width = width

        output.seek(0)
        return output

    @staticmethod
    def _get_talking_points(student_info: Dict) -> str:
        """获取谈话重点"""
        reasons = student_info['风险原因']
        points = []

        for reason in reasons:
            if "食堂消费" in reason:
                points.append("了解经济状况和饮食习惯")
            elif "夜间" in reason:
                points.append("了解夜间活动原因和安全")
            elif "在线" in reason:
                points.append("了解网络使用情况和学习状态")
            elif "规律" in reason:
                points.append("了解作息规律和社交情况")
            elif "成绩" in reason or "不及格" in reason:
                points.append("了解学习困难和课业压力")
            else:
                points.append("了解近期学习和生活状况")

        return "；".join(list(set(points))[:3])  # 最多3个重点

    def start_analyze(self, data_dict: Dict) -> Dict:
        """
        分析入口
        返回分析结果摘要和 Excel 文件数据
        """
        try:
            # 1. 加载数据
            self.load_data_from_dict(data_dict)

            # 2. 分析学生行为
            self.analyze_student_behavior()

            # 3. 识别风险学生
            self.identify_at_risk_students()

            # 4. 生成分析摘要
            summary = {
                '分析时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                '总学生数': len(self.students_info),
                '需要关注学生数': len(self.at_risk_students),
                '风险等级分布': {
                    '高风险': len([s for s in self.at_risk_students if s['风险等级'] == '高风险']),
                    '中风险': len([s for s in self.at_risk_students if s['风险等级'] == '中风险']),
                    '低风险': len([s for s in self.at_risk_students if s['风险等级'] == '低风险'])
                }
            }

            # 5. 生成Excel文件
            excel_file = self._generate_detailed_analysis_excel()

            return {
                'status': 'success',
                'summary': summary,
                'excel_data': excel_file.getvalue(),
                'filename': f'学生思想健康详细分析_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'分析失败: {str(e)}'
            }
