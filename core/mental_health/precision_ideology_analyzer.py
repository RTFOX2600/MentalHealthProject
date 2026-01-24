import warnings
from datetime import datetime
from typing import Dict, List, Any
import io

import numpy as np
import pandas as pd


warnings.filterwarnings('ignore')


class PrecisionIdeologyAnalyzer:
    """
    精准思政分析器 - 深度优化版
    基于网络行为画像的三级指标体系：正向度、情绪强度、激进度
    """

    def __init__(self, params=None):
        self.students_profile = {}
        self.data = {}
        self.cohort_stats = {}  # 存储群体统计数据用于动态对齐

        # 增强域名分类体系
        self.domain_categories = {
            '学习科研': ['github.com', 'www.csdn.net', 'stackoverflow.com', 'www.cnki.net', 'www.wikipedia.org', 'leetcode.com',
                         'gitee.com'],
            '搜索引擎': ['www.baidu.com', 'www.google.com', 'bing.com'],
            '社交媒体': ['weibo.com', 'www.zhihu.com', 'www.douban.com', 'www.xiaohongshu.com', 'tieba.baidu.com', 'twitter.com'],
            '视频娱乐': ['www.bilibili.com', 'www.douyin.com', 'www.youtube.com', 'v.qq.com', 'iqiyi.com'],
            '电商购物': ['www.taobao.com', 'www.jd.com', 'pinduoduo.com', 'tmall.com'],
            '生活服务': ['meituan.com', 'amap.com', '12306.cn', 'ctrip.com'],
            '工具资讯': ['www.163.com', 'www.qq.com', 'pan.baidu.com', 'music.163.com', 'notion.so']
        }

    def load_data_from_dict(self, data_dict: Dict):
        """加载数据并计算群体基准"""
        print("加载精准思政分析数据...")
        self.data['network'] = pd.DataFrame(data_dict.get('network', []))
        self.data['grades'] = pd.DataFrame(data_dict.get('grades', []))

        if not self.data['network'].empty:
            # 转换时间并强制转换为本地时区 (核心修复)
            series = pd.to_datetime(self.data['network']['开始时间'], errors='coerce')
            if series.dt.tz is not None:
                series = series.dt.tz_convert('Asia/Shanghai')
            self.data['network']['开始时间'] = series

            net = self.data['network']

            # 计算群体日均访问次数中位数 (如果中位数太低，使用默认基准值15)
            daily_counts = net.groupby(['学号', net['开始时间'].dt.date]).size()
            median_daily = daily_counts.groupby('学号').mean().median()
            self.cohort_stats['daily_avg_median'] = max(5, median_daily) if not pd.isna(median_daily) else 15

            # 计算群体夜间访问比例中位数
            night_mask = (net['开始时间'].dt.hour >= 23) | (net['开始时间'].dt.hour < 6)
            night_ratios = net.groupby('学号').apply(lambda x: (night_mask[x.index]).sum() / len(x))
            median_night = night_ratios.median()
            self.cohort_stats['night_ratio_median'] = max(0.05, median_night) if not pd.isna(median_night) else 0.1

    def _classify_domain(self, domain: str) -> str:
        if not domain or domain == '': return '其他'
        for category, domains in self.domain_categories.items():
            if any(d in domain.lower() for d in domains):
                return category
        return '其他'

    def _calculate_positivity(self, student_net: pd.DataFrame) -> str:
        """计算正向度：基于分值的综合判定"""
        if student_net.empty: return '不显著'

        score = 0
        # 1. 域名类别分值 (正向: 学习, 搜索引擎; 负向: 适度社交不加分, 过度社交扣分)
        cats = student_net['访问域名'].apply(self._classify_domain).value_counts(normalize=True)
        score += cats.get('学习科研', 0) * 10
        score += cats.get('搜索引擎', 0) * 5
        score -= cats.get('视频娱乐', 0) * 3

        # 2. VPN扣分
        vpn_ratio = (student_net['是否使用VPN'] == '是').sum() / len(student_net)
        score -= vpn_ratio * 8

        # 3. 访问多样性加分 (视野开阔)
        diversity = student_net['访问域名'].nunique() / len(student_net)
        score += diversity * 5

        if score > 3:
            return '正向'
        elif score < -1:
            return '负向'
        else:
            return '不显著'

    def _calculate_emotion_intensity(self, student_net: pd.DataFrame) -> str:
        """计算情绪强度：基于偏离群体的程度"""
        if student_net.empty: return '不显著'

        # 1. 计算日均次数与群体基准对比
        daily_avg = len(student_net) / max(1, student_net['开始时间'].dt.date.nunique())
        count_factor = daily_avg / max(1, self.cohort_stats.get('daily_avg_median', 15))

        # 2. 夜间访问
        night_mask = (student_net['开始时间'].dt.hour >= 23) | (student_net['开始时间'].dt.hour < 6)
        night_ratio = night_mask.sum() / len(student_net)
        night_factor = night_ratio / max(0.01, self.cohort_stats.get('night_ratio_median', 0.1))

        intensity_score = count_factor * 0.6 + night_factor * 0.4

        if intensity_score > 1.4:
            return '强'
        elif intensity_score < 0.6:
            return '弱'
        else:
            return '不显著'

    def _calculate_radicalism(self, student_net: pd.DataFrame, student_grades: pd.DataFrame) -> str:
        """计算激进度：结合行为突变与外部压力"""
        if student_net.empty: return '不显著'

        score = 0
        # 1. VPN频繁使用
        vpn_ratio = (student_net['是否使用VPN'] == '是').sum() / len(student_net)
        if vpn_ratio > 0.4: score += 2

        # 2. 社交媒体依赖
        cats = student_net['访问域名'].apply(self._classify_domain).value_counts(normalize=True)
        if cats.get('社交媒体', 0) > 0.5: score += 2

        # 3. 学业压力 (成绩波动大或明显下降)
        if not student_grades.empty and 'subject_grades' in student_grades.columns:
            all_scores = []
            for g_dict in student_grades['subject_grades']:
                all_scores.extend([float(v) for v in g_dict.values() if v is not None])
            if all_scores:
                std_dev = np.std(all_scores)
                if std_dev > 10: score += 2  # 成绩波动较大
                if np.mean(all_scores) < 65: score += 2  # 学业压力较大

        if score >= 3:
            return '强'
        elif score <= 1:
            return '弱'
        else:
            return '不显著'

    def _get_dynamic_scene(self, student_net: pd.DataFrame, profile_type: str) -> str:
        """根据学生最常访问的内容生成动态场景"""
        if student_net.empty: return "未知"

        # 获取排名前二的类别
        top_cats = student_net['访问域名'].apply(self._classify_domain).value_counts()
        # 排除“其他”
        top_cats = top_cats[top_cats.index != '其他']

        if top_cats.empty:
            return "校园基础应用"

        primary = top_cats.index[0]
        if len(top_cats) > 1:
            secondary = top_cats.index[1]
            return f"{primary}/{secondary}"
        return primary

    def _determine_profile_type(self, pos: str, emo: str, rad: str) -> tuple:
        """
        确定画像类型与策略 (全矩阵覆盖)
        """
        # 建立画像矩阵映射
        matrix = {
            ('正向', '弱', '弱'): ('学术深耕型', '肯定激励', '学术论坛/图书馆'),
            ('正向', '强', '弱'): ('活跃意见型', '引导正面传播', '专业社区'),
            ('正向', '强', '强'): ('激进先锋型', '关注内容合规', '社交平台'),
            ('不显著', '强', '强'): ('活跃激进型', '重点关注', '微博/贴吧'),
            ('不显著', '不显著', '弱'): ('小心翼翼型', '关爱疏导', '社交软件'),
            ('不显著', '弱', '弱'): ('沉溺当下型', '丰富课外生活', '短视频/生活App'),
            ('负向', '强', '强'): ('潜在风险型', '预警研判', '境外平台/VPN'),
            ('负向', '强', '弱'): ('匿名吐槽型', '解决实际困难', '校内树洞'),
            ('负向', '弱', '弱'): ('消极退缩型', '心理疏导', '网游/小众社区'),
            ('正向', '不显著', '不显著'): ('专业博主型', '支持创作', 'B站/知乎'),
            ('不显著', '不显著', '不显著'): ('平稳普通型', '日常关注', '综合门户')
        }

        res = matrix.get((pos, emo, rad))
        if res: return res

        # 模糊匹配默认项
        if rad == '强': return ('激进倾向型', '加强监管', '社交媒体')
        if pos == '正向': return ('潜力骨干型', '培养选拔', '学术/资讯')
        if pos == '负向': return ('重点关注型', '谈心谈话', '多元平台')

        return ('常规关注型', '定期了解', '综合场景')

    def analyze_students(self) -> List[Dict]:
        if self.data['network'].empty: return []

        results = []
        for student_id in self.data['network']['学号'].unique():
            s_net = self.data['network'][self.data['network']['学号'] == student_id]
            s_grades = self.data['grades'][self.data['grades']['学号'] == student_id] if not self.data['grades'].empty else pd.DataFrame()

            pos = self._calculate_positivity(s_net)
            emo = self._calculate_emotion_intensity(s_net)
            rad = self._calculate_radicalism(s_net, s_grades)

            profile, strategy, _ = self._determine_profile_type(pos, emo, rad)
            scene = self._get_dynamic_scene(s_net, profile)

            results.append({
                '学号': student_id,
                '画像类型': profile,
                '正向度': pos,
                '情绪强度': emo,
                '激进度': rad,
                '典型场景': scene,
                '工作策略': strategy,
                'VPN使用比例': round((s_net['是否使用VPN'] == '是').sum() / len(s_net), 3),
                '日均访问次数': round(len(s_net) / max(1, s_net['开始时间'].dt.date.nunique()), 1),
                '主要访问类别': '、'.join(s_net['访问域名'].apply(self._classify_domain).value_counts().index[:2])
            })

        self.students_profile = {r['学号']: r for r in results}
        return results

    def generate_report_excel(self, analysis_results: List[Dict]) -> io.BytesIO:
        df = pd.DataFrame(analysis_results)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='精准思政分析', index=False)
            ws = writer.sheets['精准思政分析']
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = 18
        output.seek(0)
        return output

    def analyze_comprehensive(self, data_dict: Dict) -> Dict:
        try:
            self.load_data_from_dict(data_dict)
            results = self.analyze_students()

            summary = {
                '分析时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                '总学生数': len(results),
                '指标覆盖率': '100%',
                '重点关注人数': len([r for r in results if r['激进度'] == '强' or r['正向度'] == '负向'])
            }

            return {
                'status': 'success',
                'summary': summary,
                'excel_data': self.generate_report_excel(results).getvalue(),
                'filename': f'精准思政多维分析报告_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
