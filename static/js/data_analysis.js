// 数据分析页面 JavaScript

// 本地缓存键名
const CACHE_KEY = 'data_analysis_filters';

// 全局状态变量
let currentPage = 1;
let currentOrderBy = 'student_id';
let currentOrder = 'asc';
let currentFilters = {};
let currentDataTable = 'basic'; // 当前选中的数据表
let pageSize = 20; // 每页显示条数
let totalCount = 0; // 总记录数
let apiUrl = ''; // API URL，从 HTML 的 data 属性中获取
let loadingMessageId = null; // 加载消息 ID

// 数据表对应的列配置
const tableColumns = {
    basic: [
        { field: 'student_id', label: '学号' },
        { field: 'name', label: '姓名' },
        { field: 'college', label: '学院' },
        { field: 'major', label: '专业' },
        { field: 'grade', label: '年级' }
    ],
    canteen: [
        { field: 'student_id', label: '学号' },
        { field: 'name', label: '姓名' },
        { field: 'avg_expense', label: '月均消费' },
        { field: 'min_expense', label: '最低消费' },
        { field: 'expense_trend', label: '消费趋势' }
    ],
    school_gate: [
        { field: 'student_id', label: '学号' },
        { field: 'name', label: '姓名' },
        { field: 'night_in_out_count', label: '夜间进出次数' },
        { field: 'late_night_in_out_count', label: '深夜进出次数' },
        { field: 'total_count', label: '总次数' }
    ],
    dormitory: [
        { field: 'student_id', label: '学号' },
        { field: 'name', label: '姓名' },
        { field: 'night_in_out_count', label: '夜间进出次数' },
        { field: 'late_night_in_out_count', label: '深夜进出次数' },
        { field: 'total_count', label: '总次数' }
    ],
    network: [
        { field: 'student_id', label: '学号' },
        { field: 'name', label: '姓名' },
        { field: 'vpn_usage_rate', label: 'VPN使用占比' },
        { field: 'night_usage_rate', label: '夜间上网占比' },
        { field: 'late_night_usage_rate', label: '深夜上网占比' },
        { field: 'avg_duration', label: '月均时长' },
        { field: 'max_duration', label: '最大月时长' }
    ],
    academic: [
        { field: 'student_id', label: '学号' },
        { field: 'name', label: '姓名' },
        { field: 'avg_score', label: '平均成绩' },
        { field: 'score_trend', label: '成绩趋势' }
    ]
};

// ========== 缓存相关功能 ==========

// 保存筛选条件到缓存
function saveFiltersToCache() {
    const filters = {
        college: getDropdownValue('dropdown-college'),
        major: getDropdownValue('dropdown-major'),
        grade: getDropdownValue('dropdown-grade'),
        search: document.getElementById('filter-search').value.trim(),
        dataTable: currentDataTable,
        startDate: document.getElementById('filter-start-date').value,
        endDate: document.getElementById('filter-end-date').value,
        pageSize: pageSize
    };
    
    try {
        localStorage.setItem(CACHE_KEY, JSON.stringify(filters));
    } catch (e) {
        console.warn('缓存保存失败:', e);
    }
}

// 从缓存读取筛选条件
function loadFiltersFromCache() {
    try {
        const cached = localStorage.getItem(CACHE_KEY);
        if (cached) {
            return JSON.parse(cached);
        }
    } catch (e) {
        console.warn('缓存读取失败:', e);
    }
    return null;
}

// 设置下拉菜单的选中值
function setDropdownValue(dropdownId, value) {
    const dropdown = document.getElementById(dropdownId);
    if (!dropdown) return;
    
    // 移除所有选中状态
    dropdown.querySelectorAll('.dropdown-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    // 查找匹配的项
    const targetItem = dropdown.querySelector(`.dropdown-item[data-value="${value}"]`);
    if (targetItem) {
        targetItem.classList.add('selected');
        // 更新显示文本
        const trigger = dropdown.querySelector('.selected-text');
        if (trigger) {
            trigger.textContent = targetItem.textContent;
        }
    }
}

// 恢复筛选条件
function restoreFiltersFromCache() {
    const cached = loadFiltersFromCache();
    if (!cached) return false;
    
    // 恢复下拉菜单
    if (cached.college !== undefined) setDropdownValue('dropdown-college', cached.college);
    if (cached.major !== undefined) setDropdownValue('dropdown-major', cached.major);
    if (cached.grade !== undefined) setDropdownValue('dropdown-grade', cached.grade);
    if (cached.dataTable !== undefined) {
        currentDataTable = cached.dataTable;
        setDropdownValue('dropdown-data-table', cached.dataTable);
        updateTableHeaders(currentDataTable);
    }
    if (cached.pageSize !== undefined) {
        pageSize = cached.pageSize;
        setDropdownValue('dropdown-page-size', cached.pageSize.toString());
    }
    
    // 恢复搜索框
    if (cached.search !== undefined) {
        document.getElementById('filter-search').value = cached.search;
    }
    
    // 恢复日期
    if (cached.startDate) {
        document.getElementById('filter-start-date').value = cached.startDate;
    }
    if (cached.endDate) {
        document.getElementById('filter-end-date').value = cached.endDate;
    }
    
    return true;
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    // 从 HTML 获取 API URL
    const config = document.getElementById('data-analysis-config');
    if (config) {
        apiUrl = config.dataset.apiUrl;
    }
    
    // 初始化所有自定义下拉菜单
    initDropdowns();
    
    // 绑定下拉菜单选择事件
    bindDropdownEvents();
    
    // 尝试从缓存恢复筛选条件
    const hasCache = restoreFiltersFromCache();
    
    // 如果没有缓存，设置默认时间范围（最近30天）
    if (!hasCache || !document.getElementById('filter-start-date').value) {
        setDefaultDateRange();
    }
    
    // 绑定滚动事件
    bindScrollEvent();
    
    // 绑定搜索框回车事件
    bindSearchEvent();
    
    // 初始化 currentFilters（确保包含所有筛选条件）
    currentFilters = {
        college: getDropdownValue('dropdown-college'),
        major: getDropdownValue('dropdown-major'),
        grade: getDropdownValue('dropdown-grade'),
        search: document.getElementById('filter-search').value.trim(),
        data_table: currentDataTable,
        start_date: document.getElementById('filter-start-date').value,
        end_date: document.getElementById('filter-end-date').value,
    };
    
    // 加载学生列表
    loadStudentList();
});

// 绑定滚动事件
function bindScrollEvent() {
    const filterCardTop = document.querySelector('.filter-card-top');
    const filterCardBottom = document.querySelector('.filter-card-bottom');
    const scrollThreshold = 150; // 滚动阈值（像素）
    const bufferZone = 20; // 缓冲区（像素），防止抽搐
    let isScrolled = false;
    
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // 使用缓冲区机制：向下滚动和向上滚动使用不同的阈值
        if (!isScrolled && scrollTop > scrollThreshold + bufferZone) {
            // 向下滚动超过阈值+缓冲区时隐藏上部卡片
            filterCardTop.classList.add('scrolled');
            filterCardBottom.classList.add('scrolled');
            isScrolled = true;
        } else if (isScrolled && scrollTop < scrollThreshold - bufferZone) {
            // 向上滚动低于阈值-缓冲区时显示上部卡片
            filterCardTop.classList.remove('scrolled');
            filterCardBottom.classList.remove('scrolled');
            isScrolled = false;
        }
    });
}

// 设置默认时间范围
function setDefaultDateRange() {
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    document.getElementById('filter-end-date').valueAsDate = today;
    document.getElementById('filter-start-date').valueAsDate = thirtyDaysAgo;
}

// 绑定下拉菜单事件
function bindDropdownEvents() {
    // 筛选条件下拉菜单（学院、专业、年级）自动触发查询
    const filterDropdowns = ['dropdown-college', 'dropdown-major', 'dropdown-grade'];
    filterDropdowns.forEach(id => {
        const dropdown = document.getElementById(id);
        dropdown.addEventListener('item-selected', function(e) {
            // 保存到缓存
            saveFiltersToCache();
            // 选择后自动刷新表格
            applyFilters();
        });
    });
    
    // 数据表切换
    const dataTableDropdown = document.getElementById('dropdown-data-table');
    dataTableDropdown.addEventListener('item-selected', function(e) {
        currentDataTable = e.detail.value;
        updateTableHeaders(currentDataTable);
        // 保存到缓存
        saveFiltersToCache();
        // 切换数据表后重新加载数据
        currentPage = 1;
        applyFilters();
    });
    
    // 每页显示条数切换
    const pageSizeDropdown = document.getElementById('dropdown-page-size');
    pageSizeDropdown.addEventListener('item-selected', function(e) {
        pageSize = parseInt(e.detail.value);
        // 保存到缓存
        saveFiltersToCache();
        currentPage = 1; // 重置到第一页
        loadStudentList();
    });
}

// 绑定搜索框回车事件
function bindSearchEvent() {
    document.getElementById('filter-search').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            applyFilters();
        }
    });
}

// 更新表格表头
function updateTableHeaders(dataTable) {
    const columns = tableColumns[dataTable] || tableColumns.basic;
    const thead = document.querySelector('table thead tr');
    
    thead.innerHTML = columns.map(col => 
        `<th class="sortable" data-field="${col.field}" onclick="sortTable('${col.field}')">${col.label}</th>`
    ).join('');
}

// 获取下拉菜单选中值
function getDropdownValue(dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    const selected = dropdown.querySelector('.dropdown-item.selected');
    return selected ? selected.getAttribute('data-value') : '';
}

// 应用筛选
function applyFilters() {
    currentPage = 1;
    currentFilters = {
        college: getDropdownValue('dropdown-college'),
        major: getDropdownValue('dropdown-major'),
        grade: getDropdownValue('dropdown-grade'),
        search: document.getElementById('filter-search').value.trim(),
        data_table: currentDataTable,
        start_date: document.getElementById('filter-start-date').value,
        end_date: document.getElementById('filter-end-date').value,
    };
    // 保存到缓存
    saveFiltersToCache();
    loadStudentList();
}

// 排序
function sortTable(field) {
    if (currentOrderBy === field) {
        currentOrder = currentOrder === 'asc' ? 'desc' : 'asc';
    } else {
        currentOrderBy = field;
        currentOrder = 'asc';
    }
    
    // 更新表头样式
    document.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    const th = document.querySelector(`th[data-field="${field}"]`);
    th.classList.add(currentOrder === 'asc' ? 'sort-asc' : 'sort-desc');
    
    currentPage = 1;
    loadStudentList();
}

// 加载学生列表
function loadStudentList() {
    // 确保 currentFilters 包含 data_table
    if (!currentFilters.data_table) {
        currentFilters.data_table = currentDataTable;
    }
    
    const params = new URLSearchParams({
        page: currentPage,
        page_size: pageSize,
        order_by: currentOrderBy,
        order: currentOrder,
        ...currentFilters
    });

    // 根据当前数据表类型选择不同API
    let apiEndpoint;
    let isStatisticsApi = false;
    let messageStartTime = null;  // 记录消息显示开始时间
    
    if (currentDataTable === 'basic') {
        apiEndpoint = apiUrl;  // 学生基本信息 API
    } else {
        // 统计数据API
        apiEndpoint = '/dashboard/api/data-statistics/';
        isStatisticsApi = true;
        
        // 如果是第一页，显示"正在统计"提示
        if (currentPage === 1) {
            // 关闭之前的加载消息
            if (loadingMessageId) {
                window.closeMessage(loadingMessageId);
            }
            loadingMessageId = window.showMessage('数据加载中...', 'info', 0);
            messageStartTime = Date.now();  // 记录开始时间
        }
    }

    fetch(`${apiEndpoint}?${params}`)
        .then(response => response.json())
        .then(data => {
            // 确保消息至少显示0.5秒
            const closeLoadingMessage = () => {
                if (loadingMessageId) {
                    window.closeMessage(loadingMessageId);
                    loadingMessageId = null;
                }
            };
            
            if (messageStartTime) {
                const elapsed = Date.now() - messageStartTime;
                const remainingTime = Math.max(0, 500 - elapsed);  // 至少显示0.5秒
                setTimeout(closeLoadingMessage, remainingTime);
            } else {
                closeLoadingMessage();
            }
            
            if (data.success) {
                totalCount = data.total; // 更新总数
                renderStudentTable(data);
                renderPagination(data);
                document.getElementById('table-info').textContent = `总计 ${data.total} 人`;
            } else {
                console.error('加载失败');
                window.showMessage('加载数据失败', 'error', 3000);
            }
        })
        .catch(error => {
            // 关闭加载消息
            if (loadingMessageId) {
                window.closeMessage(loadingMessageId);
                loadingMessageId = null;
            }
            
            console.error('请求失败:', error);
            const columns = tableColumns[currentDataTable] || tableColumns.basic;
            document.getElementById('student-table-body').innerHTML = 
                `<tr><td colspan="${columns.length}" class="empty">加载失败，请刷新重试</td></tr>`;
            window.showMessage('请求失败，请检查网络连接', 'error', 3000);
        });
}

// 渲染学生表格
function renderStudentTable(data) {
    const tbody = document.getElementById('student-table-body');
    
    if (data.data.length === 0) {
        const columns = tableColumns[currentDataTable] || tableColumns.basic;
        tbody.innerHTML = `<tr><td colspan="${columns.length}" class="empty">暂无数据</td></tr>`;
        return;
    }
    
    // 格式化趋势显示（消费趋势、成绩趋势）
    function formatTrend(value) {
        if (value === undefined || value === null || value === 0) {
            return '<span style="color: #6c757d;">—</span>';  // 无趋势
        }
        const trend = parseFloat(value);
        if (trend > 0) {
            return `<span style="color: #28a745;">+${trend.toFixed(2)}%</span>`;  // 绿色表示上升
        } else if (trend < 0) {
            return `<span style="color: #dc3545;">${trend.toFixed(2)}%</span>`;  // 红色表示下降
        } else {
            return '<span style="color: #6c757d;">0.00%</span>';  // 灰色表示不变
        }
    }
    
    // 根据数据表类型渲染不同的内容
    let html = data.data.map(student => {
        switch(currentDataTable) {
            case 'canteen':
                return `
                    <tr>
                        <td>${student.student_id}</td>
                        <td>${student.name}</td>
                        <td>${student.avg_expense || '-'}</td>
                        <td>${student.min_expense || '-'}</td>
                        <td>${formatTrend(student.expense_trend)}</td>
                    </tr>
                `;
            case 'school_gate':
                return `
                    <tr>
                        <td>${student.student_id}</td>
                        <td>${student.name}</td>
                        <td>${student.night_in_out_count || 0}</td>
                        <td>${student.late_night_in_out_count || 0}</td>
                        <td>${student.total_count || 0}</td>
                    </tr>
                `;
            case 'dormitory':
                return `
                    <tr>
                        <td>${student.student_id}</td>
                        <td>${student.name}</td>
                        <td>${student.night_in_out_count || 0}</td>
                        <td>${student.late_night_in_out_count || 0}</td>
                        <td>${student.total_count || 0}</td>
                    </tr>
                `;
            case 'network':
                return `
                    <tr>
                        <td>${student.student_id}</td>
                        <td>${student.name}</td>
                        <td>${student.vpn_usage_rate || '-'}</td>
                        <td>${student.night_usage_rate || '-'}</td>
                        <td>${student.late_night_usage_rate || '-'}</td>
                        <td>${student.avg_duration || '-'}</td>
                        <td>${student.max_duration || '-'}</td>
                    </tr>
                `;
            case 'academic':
                return `
                    <tr>
                        <td>${student.student_id}</td>
                        <td>${student.name}</td>
                        <td>${student.avg_score || '-'}</td>
                        <td>${formatTrend(student.score_trend)}</td>
                    </tr>
                `;
            case 'basic':
            default:
                return `
                    <tr>
                        <td>${student.student_id}</td>
                        <td>${student.name}</td>
                        <td>${student.college.name}</td>
                        <td>${student.major.name}</td>
                        <td>${student.grade.name}</td>
                    </tr>
                `;
        }
    }).join('');
    
    // 添加空白行补全到pageSize行数
    const columns = tableColumns[currentDataTable] || tableColumns.basic;
    const emptyRowsNeeded = pageSize - data.data.length;
    for (let i = 0; i < emptyRowsNeeded; i++) {
        html += `<tr class="empty-row">${'<td>&nbsp;</td>'.repeat(columns.length)}</tr>`;
    }
    
    tbody.innerHTML = html;
}

// 渲染分页
function renderPagination(data) {
    const pagination = document.getElementById('pagination');
    const totalPages = data.total_pages;
    
    let html = `
        <button onclick="changePage(${data.page - 1})" ${data.page === 1 ? 'disabled' : ''}>上一页</button>
        <span class="page-info">第 ${data.page} / ${totalPages} 页</span>
        <button onclick="changePage(${data.page + 1})" ${data.page === totalPages ? 'disabled' : ''}>下一页</button>
        <div class="page-jump">
            <span>跳至</span>
            <input type="number" id="page-jump-input" min="1" max="${totalPages}" placeholder="${data.page}" />
            <span>页</span>
            <button onclick="jumpToPage()">跳转</button>
        </div>
    `;
    
    pagination.innerHTML = html;
    
    // 绑定回车事件
    const jumpInput = document.getElementById('page-jump-input');
    if (jumpInput) {
        jumpInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                jumpToPage();
            }
        });
    }
}

// 切换页码
function changePage(page) {
    currentPage = page;
    loadStudentList();
}

// 跳转到指定页面
function jumpToPage() {
    const input = document.getElementById('page-jump-input');
    const page = parseInt(input.value);
    const totalPages = Math.ceil(totalCount / pageSize);
    
    if (page && page >= 1 && page <= totalPages && page !== currentPage) {
        changePage(page);
        input.value = '';
    } else {
        input.value = '';
        input.placeholder = currentPage;
    }
}
