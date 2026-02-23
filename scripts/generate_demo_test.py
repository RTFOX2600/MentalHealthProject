import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import warnings
import os
from typing import Any, Optional

warnings.filterwarnings('ignore')


class MultiTableCampusDataGenerator:
    def __init__(self,
                 student_count: int = 1000,
                 start_date: str = "2024-01-01",
                 months: int = 6,
                 random_seed: int = 42,
                 selected_colleges: list = None,
                 selected_majors: list = None):
        """
        初始化多表数据生成器
        
        Args:
            student_count: 学生数量
            start_date: 开始日期
            months: 月份数
            random_seed: 随机种子
            selected_colleges: 选择的学院列表（默认['CS']）
            selected_majors: 选择的专业列表（默认['CS01']即软件工程）
        """
        self.student_count = student_count
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.months = months
        self.end_date = self.start_date + timedelta(days=30 * months)

        # 生成学号列表 (格式: 2400001)
        self.student_ids = [f"24{str(i).zfill(5)}" for i in range(1, student_count + 1)]

        # 计算结束日期（更精确的方式：下一个月的1号）
        target_month = self.start_date.month - 1 + months
        end_year = self.start_date.year + target_month // 12
        end_month = (target_month % 12) + 1
        self.end_date = datetime(end_year, end_month, 1)

        # 初始化随机种子
        np.random.seed(random_seed)
        random.seed(random_seed)
        self.random_seed = random_seed

        # 创建输出目录到桌面
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.output_dir = os.path.join(desktop_path, "精准思政测试数据")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # 所有学院和专业代码
        self.all_majors = {
            'AD': ['AD01', 'AD02', 'AD03'],  # 艺术设计学院
            'AS': ['AS01', 'AS02', 'AS03', 'AS04'],  # 动物科学与营养工程学院
            'BA': ['BA01', 'BA02'],  # 商学院
            'BT': ['BT01', 'BT02', 'BT03', 'BT04', 'BT05'],  # 生命科学与技术学院
            'CA': ['CA01', 'CA02', 'CA03', 'CA04'],  # 土木工程与建筑学院
            'CE': ['CE01', 'CE02', 'CE03'],  # 化学与环境工程学院
            'CS': ['CS01', 'CS02', 'CS03', 'CS04'],  # 数学与计算机学院
            'EC': ['EC01', 'EC02', 'EC03'],  # 经济学院
            'EL': ['EL01', 'EL02', 'EL03', 'EL04'],  # 电气与电子工程学院
            'ET': ['ET01', 'ET02'],  # 电子工程学院
            'FL': ['FL01', 'FL02'],  # 外国语学院
            'FS': ['FS01', 'FS02', 'FS03', 'FS04', 'FS05'],  # 食品科学与工程学院
            'HM': ['HM01', 'HM02', 'HM03'],  # 人文与传媒学院
            'LA': ['LA01'],  # 文学院
            'ME': ['ME01', 'ME02', 'ME03', 'ME04'],  # 机械工程学院
            'MG': ['MG01', 'MG02', 'MG03', 'MG04', 'MG05', 'MG06'],  # 管理学院
            'MH': ['MH01', 'MH02', 'MH03'],  # 医学与健康学院
            'SE': ['SE01']  # 硒科学与工程现代产业学院
        }
        
        # 设置选中的学院和专业
        if selected_colleges is None:
            self.selected_colleges = ['CS']  # 默认数计学院
        else:
            self.selected_colleges = selected_colleges
        
        if selected_majors is None:
            self.selected_majors = ['CS01']  # 默认软件工程
        else:
            self.selected_majors = selected_majors
        
        # 验证专业是否属于选中的学院
        self.majors = {}
        for college in self.selected_colleges:
            if college in self.all_majors:
                college_majors = [m for m in self.selected_majors if m in self.all_majors[college]]
                if college_majors:
                    self.majors[college] = college_majors
        
        # 如果没有有效的专业，使用默认值
        if not self.majors:
            self.majors = {'CS': ['CS01']}
            self.selected_colleges = ['CS']
            self.selected_majors = ['CS01']
        
        self.grade = 2024  # 固定年级为2024

    def _get_year_month_date(self, month_offset: int) -> datetime:
        """
        根据起始日期和月份偏移量获取对应的日期对象
        """
        total_months = self.start_date.month - 1 + month_offset
        year = self.start_date.year + total_months // 12
        month = (total_months % 12) + 1
        return datetime(year, month, 1)
    
    def generate_table0_students(self) -> pd.DataFrame:
        """
        表格0：学生基本信息
        格式：姓名, 学号, 学院代码, 专业代码, 年级
        """
        print("生成表格0：学生基本信息...")
        
        # 中文姓氏库
        surnames = ['李', '王', '张', '刘', '陈', '杨', '黄', '赵', '周', '吴',
                   '徐', '孙', '马', '朱', '胡', '郭', '林', '何', '高', '罗',
                   '郑', '梁', '谢', '宋', '唐', '许', '韩', '冯', '邓', '曹']
        given_names_male = ['伟', '磊', '军', '涛', '明', '强', '飞', '铭', '浩', '志',
                           '杰', '鹏', '晨', '辉', '明', '建', '国', '文', '宇', '博']
        given_names_female = ['芝', '芙', '莉', '芋', '雪', '雯', '霜', '冰', '梅', '瑜',
                             '艳', '娜', '婷', '婉', '婷', '敏', '萌', '琪', '琪', '琪']
        
        data = []
        
        # 获取所有专业列表
        all_selected_majors = []
        for college in self.majors:
            for major in self.majors[college]:
                all_selected_majors.append((college, major))
        
        # 计算每个专业应该分配的学生数
        majors_count = len(all_selected_majors)
        students_per_major = self.student_count // majors_count
        remaining_students = self.student_count % majors_count
        
        # 为每个学生分配专业
        student_major_assignment = []
        for i, (college, major) in enumerate(all_selected_majors):
            count = students_per_major + (1 if i < remaining_students else 0)
            student_major_assignment.extend([(college, major)] * count)
        
        for i, student_id in enumerate(self.student_ids):
            # 随机选择姓氏
            surname = random.choice(surnames)
            # 根据索引随机分配性别
            is_male = (i % 2 == 0)
            if is_male:
                given_name = ''.join(random.sample(given_names_male, 1))
            else:
                given_name = ''.join(random.sample(given_names_female, 1 if random.random() < 0.7 else 2))
            
            name = surname + given_name
            
            # 使用预先分配的专业
            college, major = student_major_assignment[i]
            grade = self.grade  # 固定年级
            
            data.append({
                "姓名": name,
                "学号": student_id,
                "学院代码": college,
                "专业代码": major,
                "年级": grade
            })
        
        return pd.DataFrame(data)

    def generate_table1_canteen(self) -> pd.DataFrame:
        """
        表格1：学号、月份、消费金额
        """
        print("生成表格1：食堂消费数据...")
        data = []

        for student_id in self.student_ids:
            for month_offset in range(self.months):
                current_date = self._get_year_month_date(month_offset)
                year_month = current_date.strftime("%Y-%m")

                # 生成基础消费金额
                student_base: float = np.random.normal(800, 150)
                month_factor: float = np.random.uniform(0.8, 1.2)

                # 季节性波动
                month_num = current_date.month
                if month_num in [1, 2, 7, 8]:
                    season_factor = np.random.uniform(0.3, 0.6)
                elif month_num in [9, 10]:
                    season_factor = np.random.uniform(1.1, 1.4)
                else:
                    season_factor = np.random.uniform(0.9, 1.1)

                amount = max(100.0, student_base * month_factor * season_factor)

                data.append({
                    "学号": student_id,
                    "月份": year_month,
                    "消费金额": round(amount, 2)
                })

        df = pd.DataFrame(data)

        # 添加5%的异常值
        anomaly_count = int(len(df) * 0.05)
        if anomaly_count > 0:
            anomaly_indices = np.random.choice(len(df), anomaly_count, replace=False)
            for idx in anomaly_indices:
                if random.random() < 0.5:
                    df.loc[idx, "消费金额"] = round(df.loc[idx, "消费金额"] * np.random.uniform(2, 5), 2)
                else:
                    df.loc[idx, "消费金额"] = round(df.loc[idx, "消费金额"] * np.random.uniform(0.1, 0.3), 2)

        return df

    def generate_table2_school_gate(self) -> pd.DataFrame:
        """
        表格2：学号、时间、校门位置、进出方向
        目标：100人3个月约18000条（平均每人每天1进1出）
        特征：5%夜间活动者 + 1%夜不归宿者
        """
        print("生成表格2：校门进出记录...")
        data = []
        gates = ["南门", "北门", "东门", "西门", "小南门"]
        
        # 为每个学生生成个性化偏好
        student_gate_behavior = {}
        for i, student_id in enumerate(self.student_ids):
            # 1%的学生偶尔夜不归宿
            is_stay_out = (i % 100 == 0)  # 1%
            # 5%的学生是夜间活动者（喜欢晚上出门）
            is_night_person = (i % 20 == 0)  # 5%
            student_gate_behavior[student_id] = {
                'is_stay_out': is_stay_out,
                'is_night_person': is_night_person
            }

        # 生成每一天的数据
        current_date = self.start_date
        day_count = 0

        while current_date < self.end_date:
            day_count += 1
            if day_count % 10 == 0:
                print(f"  处理第 {day_count} 天...")

            is_weekend = current_date.weekday() >= 5

            for student_id in self.student_ids:
                behavior = student_gate_behavior[student_id]
                is_stay_out = behavior['is_stay_out']
                is_night_person = behavior['is_night_person']
                
                # 夜不归宿者在周末有20%概率夜不归宿
                will_stay_out_tonight = is_stay_out and is_weekend and random.random() < 0.2
                
                # 决定当天的进出次数（平均每天约2次）
                if is_weekend:
                    entry_count = np.random.poisson(2.5)  # 周末稍多
                else:
                    entry_count = np.random.poisson(1.8)  # 平日

                entry_count = max(0, min(entry_count, 5))  # 限制0-5次

                for visit_idx in range(entry_count):
                    # 出门时间（夜间活动者更多晚上出门）
                    if is_night_person:
                        # 夜间活动者：偏好晚上和深夜
                        if is_weekend:
                            out_hour = np.random.choice([10, 14, 18, 19, 20, 21, 22, 23],
                                                        p=[0.1, 0.1, 0.15, 0.15, 0.15, 0.15, 0.1, 0.1])
                        else:
                            out_hour = np.random.choice([12, 17, 18, 19, 20, 21, 22],
                                                        p=[0.1, 0.15, 0.2, 0.2, 0.15, 0.1, 0.1])
                    else:
                        # 普通学生：白天为主
                        if is_weekend:
                            out_hour = np.random.choice([9, 10, 11, 14, 15, 16, 19, 20],
                                                        p=[0.15, 0.2, 0.15, 0.15, 0.15, 0.1, 0.05, 0.05])
                        else:
                            out_hour = np.random.choice([7, 8, 12, 13, 16, 17, 18],
                                                        p=[0.1, 0.2, 0.2, 0.15, 0.15, 0.1, 0.1])

                    out_minute = np.random.randint(0, 60)
                    out_time = current_date.replace(hour=out_hour, minute=out_minute, second=np.random.randint(0, 60))

                    # 选择校门
                    gate = np.random.choice(gates, p=[0.4, 0.3, 0.1, 0.1, 0.1])

                    # 添加出门记录
                    data.append({
                        "学号": student_id,
                        "时间": out_time,
                        "校门位置": gate,
                        "进出方向": "出"
                    })

                    # 决定回来时间
                    if will_stay_out_tonight and visit_idx == entry_count - 1:
                        # 夜不归宿：第二天早上7-9点回来
                        next_day = current_date + timedelta(days=1)
                        in_hour = np.random.choice([7, 8, 9], p=[0.3, 0.4, 0.3])
                        in_time = next_day.replace(
                            hour=in_hour,
                            minute=np.random.randint(0, 60),
                            second=np.random.randint(0, 60)
                        )
                    else:
                        # 正常情况：在校外时长（30分钟-6小时）
                        outside_duration = np.random.randint(30, 360)
                        in_time = out_time + timedelta(minutes=outside_duration)
                        
                        # 如果超过当天23:59，则限制为23:59
                        if in_time.date() != current_date.date():
                            in_time = current_date.replace(hour=23, minute=59, second=59)

                    # 添加进门记录
                    data.append({
                        "学号": student_id,
                        "时间": in_time,
                        "校门位置": gate,
                        "进出方向": "进"
                    })

            current_date += timedelta(days=1)

        df = pd.DataFrame(data)
        return df.sort_values("时间").reset_index(drop=True)

    def generate_table3_dorm_gate(self) -> pd.DataFrame:
        """
        表格3：学号、时间、寝室楼栋、进出方向
        目标：100人3个月约54000条（平均每人每天6次，3进3出）
        特征：1%夜不归宿 + 5%晚归者
        """
        print("生成表格3：寝室门禁进出记录...")
        data = []
        buildings = [f"{i}栋" for i in range(1, 21)]

        # 为每个学生分配寝室楼和行为特征
        student_dorm_behavior = {}
        for i, student_id in enumerate(self.student_ids):
            building = buildings[i % len(buildings)]
            # 1%的学生偶尔夜不归宿
            is_stay_out = (i % 100 == 0)
            # 5%的学生是晚归者（凌晨1-3点回寝室）
            is_late_returner = (i % 20 == 0)
            student_dorm_behavior[student_id] = {
                'building': building,
                'is_stay_out': is_stay_out,
                'is_late_returner': is_late_returner
            }

        # 生成每一天的数据
        current_date = self.start_date
        day_count = 0

        while current_date < self.end_date:
            day_count += 1
            if day_count % 10 == 0:
                print(f"  处理第 {day_count} 天...")

            is_weekend = current_date.weekday() >= 5

            for student_id in self.student_ids:
                behavior = student_dorm_behavior[student_id]
                dorm = behavior['building']
                is_stay_out = behavior['is_stay_out']
                is_late_returner = behavior['is_late_returner']
                
                # 夜不归宿者在周末有20%概率夜不归宿
                will_stay_out_tonight = is_stay_out and is_weekend and random.random() < 0.2

                # 每人每天6次进出（3进3出）
                if is_weekend:
                    patterns = [
                        (3, [9, 14, 20]),     # 3进3出：早上、下午、晚上
                        (3, [10, 15, 21]),    # 3进3出
                        (4, [8, 12, 16, 22]), # 4进4出
                    ]
                else:
                    patterns = [
                        (3, [7, 12, 18]),     # 3进3出：早上、中午、晚上
                        (3, [8, 13, 19]),     # 3进3出
                        (4, [7, 11, 17, 22]), # 4进4出
                    ]

                pattern_idx = np.random.choice(len(patterns))
                entry_count, hours = patterns[pattern_idx]

                for visit_idx, hour in enumerate(hours[:entry_count]):
                    # 出门时间
                    out_time = current_date.replace(
                        hour=hour,
                        minute=np.random.randint(0, 30),
                        second=np.random.randint(0, 60)
                    )

                    # 添加出门记录
                    data.append({
                        "学号": student_id,
                        "时间": out_time,
                        "寝室楼栋": dorm,
                        "进出方向": "出"
                    })

                    # 决定回寝时间
                    if will_stay_out_tonight and visit_idx == entry_count - 1:
                        # 夜不归宿：第二天早上6-9点回来
                        next_day = current_date + timedelta(days=1)
                        in_hour = np.random.choice([6, 7, 8, 9], p=[0.2, 0.3, 0.3, 0.2])
                        in_time = next_day.replace(
                            hour=in_hour,
                            minute=np.random.randint(0, 60),
                            second=np.random.randint(0, 60)
                        )
                    elif is_late_returner and hour >= 20 and random.random() < 0.3:
                        # 晚归者：晚上出门后有30%概率凌晨1-3点才回
                        next_day = current_date + timedelta(days=1)
                        in_hour = np.random.choice([1, 2, 3], p=[0.4, 0.4, 0.2])
                        in_time = next_day.replace(
                            hour=in_hour,
                            minute=np.random.randint(0, 60),
                            second=np.random.randint(0, 60)
                        )
                    else:
                        # 正常情况：回寝时间（1-4小时后）
                        in_hour = min(23, hour + np.random.randint(1, 5))
                        in_time = current_date.replace(
                            hour=in_hour,
                            minute=np.random.randint(0, 60),
                            second=np.random.randint(0, 60)
                        )

                    # 添加进门记录
                    data.append({
                        "学号": student_id,
                        "时间": in_time,
                        "寝室楼栋": dorm,
                        "进出方向": "进"
                    })

            current_date += timedelta(days=1)

        df = pd.DataFrame(data)
        return df.sort_values("时间").reset_index(drop=True)

    def generate_table4_network(self) -> pd.DataFrame:
        """
        表格4：学号、开始时间、结束时间、访问域名、是否使用VPN
        目标：100人3个月约90000条（平均每人每天10次）
        特征：20%凌晨上网者 + 5%凌晨VPN用户 + 域名个性化
        """
        print("生成表格4：网络访问记录...")
        data = []
            
        # 常用域名分类
        domain_categories = {
            'study': [
                'baidu.com', 'google.com', 'zhihu.com', 'csdn.net', 
                'stackoverflow.com', 'github.com', 'wikipedia.org', 'cnki.net',
                'scholar.google.com', 'arxiv.org', 'researchgate.net'
            ],
            'entertainment': [
                'bilibili.com', 'douyin.com', 'qq.com', 'weibo.com',
                'youtube.com', 'netflix.com', 'iqiyi.com', 'youku.com',
                'tiktok.com', 'twitch.tv'
            ],
            'social': [
                'wechat.com', 'qq.com', 'weibo.com', 'xiaohongshu.com',
                'twitter.com', 'facebook.com', 'instagram.com', 'linkedin.com'
            ],
            'shopping': [
                'taobao.com', 'jd.com', 'pinduoduo.com', 'tmall.com',
                'amazon.com', 'aliexpress.com', 'meituan.com', 'ele.me'
            ],
            'gaming': [
                'steam.com', 'epicgames.com', 'wegame.com', 'mihoyo.com',
                'riotgames.com', 'blizzard.com', '4399.com'
            ],
            'news': [
                'sina.com.cn', 'sohu.com', '163.com', 'toutiao.com',
                'thepaper.cn', 'people.com.cn', 'xinhuanet.com'
            ]
        }
                
        # 为每个学生生成个性化偏好
        student_preferences = {}
        for i, student_id in enumerate(self.student_ids):
            # VPN使用偏好：10%重度用户，20%轻度用户，70%很少使用
            np.random.seed(42 + i)
            vpn_type = np.random.choice(['heavy', 'light', 'rare'], p=[0.1, 0.2, 0.7])
            if vpn_type == 'heavy':
                vpn_probability = np.random.uniform(0.5, 0.8)  # 50%-80%
            elif vpn_type == 'light':
                vpn_probability = np.random.uniform(0.15, 0.35)  # 15%-35%
            else:
                vpn_probability = np.random.uniform(0.0, 0.1)  # 0%-10%
                            
            # 凌晨深夜上网者：10%的学生喜欢在凌晨0:30之后上网（较小众）
            is_deep_night_user = (i % 10 == 0)  # 10%
                                    
            # 凌晨VPN用户：5%的学生凌晨喜欢使用VPN
            is_midnight_vpn_user = (i % 20 == 0)  # 5%
                
            # 域名访问偏好（每个学生有自己的偏好权重）
            domain_weights = {
                'study': np.random.uniform(0.2, 0.5),
                'entertainment': np.random.uniform(0.15, 0.35),
                'social': np.random.uniform(0.1, 0.25),
                'shopping': np.random.uniform(0.05, 0.15),
                'gaming': np.random.uniform(0.0, 0.2),
                'news': np.random.uniform(0.05, 0.15)
            }
            # 归一化权重
            total_weight = sum(domain_weights.values())
            domain_weights = {k: v/total_weight for k, v in domain_weights.items()}
                                
            student_preferences[student_id] = {
                'vpn_probability': vpn_probability,
                'vpn_type': vpn_type,
                'is_deep_night_user': is_deep_night_user,
                'is_midnight_vpn_user': is_midnight_vpn_user,
                'domain_weights': domain_weights
            }
                
        # 重置随机种子
        np.random.seed(self.random_seed)
        random.seed(self.random_seed)
        
        # 生成每一天的数据
        current_date = self.start_date
        day_count = 0
        
        while current_date < self.end_date:
            day_count += 1
            if day_count % 10 == 0:
                print(f"  处理第 {day_count} 天...")
        
            is_weekend = current_date.weekday() >= 5
        
            for student_id in self.student_ids:
                # 获取该学生的偏好
                preferences = student_preferences[student_id]
                vpn_prob = preferences['vpn_probability']
                is_deep_night_user = preferences['is_deep_night_user']
                is_midnight_vpn_user = preferences['is_midnight_vpn_user']
                domain_weights = preferences['domain_weights']
                        
                # 每人每天平均10次网络访问
                if is_weekend:
                    visit_count = np.random.poisson(12)  # 周末更多
                else:
                    visit_count = np.random.poisson(10)  # 平日
                        
                visit_count = max(5, min(visit_count, 25))  # 限学5-25次
        
                for _ in range(visit_count):
                    # 生成访问时间（符合大学生作息习惯）
                    if is_deep_night_user:
                        # 凌晨深夜上网者（小众）：偏好0:30之后，但晚上也会上网
                        if is_weekend:
                            hour = np.random.choice([0, 1, 2, 3, 4, 10, 14, 16, 19, 20, 21, 22, 23],
                                                   p=[0.12, 0.12, 0.10, 0.03, 0.01, 0.05, 0.07, 0.05, 0.06, 0.07, 0.10, 0.12, 0.10])
                        else:
                            hour = np.random.choice([0, 1, 2, 3, 9, 12, 16, 19, 20, 21, 22, 23],
                                                   p=[0.12, 0.10, 0.08, 0.02, 0.06, 0.06, 0.06, 0.08, 0.10, 0.12, 0.14, 0.06])
                    else:
                        # 普通学生：主要在晚上19:00~23:00上网，符合大多数大学生作息
                        if is_weekend:
                            # 周末：白天和晚上都会上网，晚上更多
                            hour = np.random.choice([9, 10, 11, 14, 15, 16, 19, 20, 21, 22, 23],
                                                   p=[0.06, 0.08, 0.08, 0.08, 0.10, 0.08, 0.12, 0.14, 0.12, 0.10, 0.04])
                        else:
                            # 工作日：下午和晚上为主，19:00~23:00高峰
                            hour = np.random.choice([9, 10, 12, 14, 15, 16, 18, 19, 20, 21, 22, 23],
                                                   p=[0.04, 0.05, 0.06, 0.08, 0.10, 0.08, 0.08, 0.12, 0.15, 0.12, 0.09, 0.03])
                                            
                    minute = np.random.randint(0, 60)
                    second = np.random.randint(0, 60)
                    start_time = current_date.replace(hour=hour, minute=minute, second=second)
                                            
                    # 生成结束时间（5-120分钟后，允许跨日）
                    duration_minutes = np.random.randint(5, 120)
                    end_time = start_time + timedelta(minutes=duration_minutes)
                    
                    # 决定VPN使用：凌晨VPN用户在凌晨0:30之后使用VPN概率更高
                    if is_midnight_vpn_user and (start_time.hour == 0 and start_time.minute >= 30) or (1 <= start_time.hour < 5):
                        # 凌晨VPN用户在深夜有60-90%概率使用VPN
                        use_vpn = random.random() < np.random.uniform(0.6, 0.9)
                    else:
                        # 正常VPN使用概率
                        use_vpn = random.random() < vpn_prob
                    
                    # 根据是否使用VPN决定域名显示
                    if use_vpn:
                        # 使用VPN时，校园网无法看到域名（被加密）
                        domain = ""
                        vpn_status = "是"
                    else:
                        # 不使用VPN时，根据个性化权重选择域名类别
                        category = np.random.choice(
                            list(domain_weights.keys()),
                            p=list(domain_weights.values())
                        )
                        domain = np.random.choice(domain_categories[category])
                        vpn_status = "否"
        
                    data.append({
                        "学号": student_id,
                        "开始时间": start_time,
                        "结束时间": end_time,
                        "访问域名": domain,
                        "是否使用VPN": vpn_status
                    })
        
            current_date += timedelta(days=1)
        
        df = pd.DataFrame(data)
        return df.sort_values("开始时间").reset_index(drop=True)

    def generate_table5_grades(self) -> pd.DataFrame:
        """
        表格5：学号、月份、平均成绩
        """
        print("生成表格5：各科成绩数据...")
        data = []

        for student_id in self.student_ids:
            # 为每个学生生成基础能力系数
            student_ability = np.random.normal(75, 10)  # 基础成绩水平

            for month_offset in range(self.months):
                current_date = self._get_year_month_date(month_offset)
                year_month = current_date.strftime("%Y-%m")

                # 生成平均成绩（带有小波动）
                month_factor = np.random.uniform(0.95, 1.05)  # 月度波动
                average_score = student_ability * month_factor
                
                # 添加随机波动
                average_score += np.random.normal(0, 3)
                
                # 确保成绩在合理范围内
                average_score = max(40.0, min(100.0, average_score))

                data.append({
                    "学号": student_id,
                    "月份": year_month,
                    "平均成绩": round(average_score, 2)
                })

        df = pd.DataFrame(data)

        # 添加5%的异常成绩（成绩显著下降的情况）
        anomaly_count = int(len(df) * 0.05)
        if anomaly_count > 0:
            anomaly_indices = np.random.choice(len(df), anomaly_count, replace=False)
            for idx in anomaly_indices:
                current_score = df.loc[idx, "平均成绩"]
                # 成绩降低20-40分
                df.loc[idx, "平均成绩"] = round(max(40.0, current_score - np.random.uniform(20, 40)), 2)

        return df

    def generate_all_tables(self, output_format: str = "csv"):
        """
        生成所有表格并保存
        """
        print("=" * 50)
        print("开始生成校园行为数据表格...")
        print(f"学生数量: {self.student_count}")
        print(f"选择学院: {', '.join(self.selected_colleges)}")
        print(f"选择专业: {', '.join(self.selected_majors)}")
        print(f"时间范围: {self.start_date.strftime('%Y-%m-%d')} 至 "
              f"{(self.end_date - timedelta(days=1)).strftime('%Y-%m-%d')}")
        print("=" * 50)

        # 生成各个表格
        try:
            table0 = self.generate_table0_students()
            print(f"表格0生成完成: {len(table0)} 条记录")

            table1 = self.generate_table1_canteen()
            print(f"表格1生成完成: {len(table1)} 条记录")

            table2 = self.generate_table2_school_gate()
            print(f"表格2生成完成: {len(table2)} 条记录")

            table3 = self.generate_table3_dorm_gate()
            print(f"表格3生成完成: {len(table3)} 条记录")

            table4 = self.generate_table4_network()
            print(f"表格4生成完成: {len(table4)} 条记录")

            table5 = self.generate_table5_grades()
            print(f"表格5生成完成: {len(table5)} 条记录")

        except Exception as e:
            print(f"生成数据时出错: {e}")
            import traceback
            traceback.print_exc()
            return None

        # 保存数据（只保存CSV格式）
        print("\n保存为CSV文件...")
        try:
            table0.to_csv(os.path.join(self.output_dir, "1_学生基本信息表.csv"), index=False, encoding='utf-8-sig')
            table1.to_csv(os.path.join(self.output_dir, "2_食堂消费月度表.csv"), index=False, encoding='utf-8-sig')
            table2.to_csv(os.path.join(self.output_dir, "3_校门进出记录表.csv"), index=False, encoding='utf-8-sig')
            table3.to_csv(os.path.join(self.output_dir, "4_寝室门禁记录表.csv"), index=False, encoding='utf-8-sig')
            table4.to_csv(os.path.join(self.output_dir, "5_网络访问记录表.csv"), index=False, encoding='utf-8-sig')
            table5.to_csv(os.path.join(self.output_dir, "6_各科成绩表.csv"), index=False, encoding='utf-8-sig')
            print(f"CSV文件已保存到 {self.output_dir} 目录")
        except Exception as e:
            print(f"保存CSV文件时出错: {e}")

        # 打印统计信息
        print("\n" + "=" * 50)
        print("数据生成完成！统计信息:")
        print("=" * 50)
        print(f"1. 学生基本信息表: {len(table0)} 条记录")
        if len(table0) > 0:
            print(f"   学院数量: {table0['学院代码'].nunique()} 个")
            print(f"   专业数量: {table0['专业代码'].nunique()} 个")
            print(f"   年级: {table0['年级'].iloc[0]}")

        print(f"\n2. 食堂消费月度表: {len(table1)} 条记录")
        print(f"   平均每月消费: ￥{table1['消费金额'].mean():.2f}")

        print(f"\n3. 校门进出记录表: {len(table2)} 条记录")
        if len(table2) > 0:
            direction_counts = table2['进出方向'].value_counts()
            print(f"   出门记录: {direction_counts.get('出', 0)} 条")
            print(f"   进门记录: {direction_counts.get('进', 0)} 条")

        print(f"\n4. 寝室门禁记录表: {len(table3)} 条记录")
        if len(table3) > 0:
            dorm_direction_counts = table3['进出方向'].value_counts()
            print(f"   出门记录: {dorm_direction_counts.get('出', 0)} 条")
            print(f"   进门记录: {dorm_direction_counts.get('进', 0)} 条")

        print(f"\n5. 网络访问记录表: {len(table4)} 条记录")
        if len(table4) > 0:
            vpn_count = (table4['是否使用VPN'] == '是').sum()
            non_vpn_count = (table4['是否使用VPN'] == '否').sum()
            print(f"   使用VPN访问: {vpn_count} 条 ({vpn_count/len(table4)*100:.1f}%)")
            print(f"   未使用VPN访问: {non_vpn_count} 条 ({non_vpn_count/len(table4)*100:.1f}%)")

        print(f"\n6. 各科成绩表: {len(table5)} 条记录")
        if len(table5) > 0:
            print(f"   平均成绩: {table5['平均成绩'].mean():.2f} 分")
            print(f"   最高成绩: {table5['平均成绩'].max():.1f} 分")
            print(f"   最低成绩: {table5['平均成绩'].min():.1f} 分")

        return {
            "学生信息": table0,
            "食堂消费": table1,
            "校门进出": table2,
            "寝室门禁": table3,
            "网络访问": table4,
            "各科成绩": table5
        }


# 主程序
if __name__ == "__main__":
    print("校园行为数据生成器 - 自定义配置")
    print("=" * 50)
    
    # 学生数量
    student_count = int(input("学生数量 (默认100): ") or "100")
    
    # 月份数
    months = int(input("月份数 (默认3): ") or "3")
    
    # 学院选择
    print("\n可选学院:")
    print("  AD(艺术设计), AS(动物科学), BA(商学院), BT(生命科学), CA(土木建筑)")
    print("  CE(化学环境), CS(数计学院), EC(经济学院), EL(电气电子), ET(电子工程)")
    print("  FL(外国语), FS(食品科学), HM(人文传媒), LA(文学院), ME(机械工程)")
    print("  MG(管理学院), MH(医学健康), SE(硒科学)")
    colleges_input = input("选择学院 (多个用逗号分隔，默认CS): ").strip() or "CS"
    selected_colleges = [c.strip().upper() for c in colleges_input.split(',')]
    
    # 专业选择
    print("\n可选专业:")
    print("  AD: AD01(视觉传达设计), AD02(环境设计), AD03(产品设计)")
    print("  AS: AS01(动物科学), AS02(动物药学), AS03(水产养殖学), AS04(饲料工程)")
    print("  BA: BA01(工商管理), BA02(会计学)")
    print("  BT: BT01(生物工程), BT02(生物技术), BT03(生物信息学), BT04(制药工程), BT05(合成生物学)")
    print("  CA: CA01(土木工程), CA02(建筑学), CA03(智能建造), CA04(工程管理)")
    print("  CE: CE01(化学工程与工艺), CE02(环境工程), CE03(功能材料)")
    print("  CS: CS01(计算机科学与技术), CS02(软件工程), CS03(人工智能), CS04(信息与计算科学)")
    print("  EC: EC01(国际经济与贸易), EC02(金融学), EC03(数字经济)")
    print("  EL: EL01(电气工程及其自动化), EL02(自动化), EL03(通信工程), EL04(电子信息科学与技术)")
    print("  ET: ET01(电子信息工程), ET02(通信工程)")
    print("  FL: FL01(英语), FL02(翻译)")
    print("  FS: FS01(食品科学与工程), FS02(食品质量与安全), FS03(粮食工程), FS04(食品营养与健康), FS05(中英合作)")
    print("  HM: HM01(汉语言文学), HM02(网络与新媒体), HM03(广告学)")
    print("  LA: LA01(汉语言文学)")
    print("  ME: ME01(机械设计制造及其自动化), ME02(包装工程), ME03(材料成型及控制工程), ME04(智能制造工程)")
    print("  MG: MG01(工商管理), MG02(会计学), MG03(旅游管理), MG04(物流管理), MG05(行政管理), MG06(大数据管理与应用)")
    print("  MH: MH01(护理学), MH02(康复治疗学), MH03(药学)")
    print("  SE: SE01(应用生物科学)")
    majors_input = input("选择专业 (多个用逗号分隔，默认CS02): ").strip() or "CS02"
    selected_majors = [m.strip().upper() for m in majors_input.split(',')]
    
    # 生成数据
    generator = MultiTableCampusDataGenerator(
        student_count=student_count,
        start_date="2024-01-01",
        months=months,
        selected_colleges=selected_colleges,
        selected_majors=selected_majors
    )
    data = generator.generate_all_tables()

    if data:
        print("\n生成完成！")
        print(f"文件已保存到桌面的'精准思政测试数据'文件夹中")

    input("按 Enter 键退出...")
