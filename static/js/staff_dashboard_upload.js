/**
 * 工作台数据上传逻辑
 */

// API 端点映射
const API_ENDPOINTS = {
    'students': '/api/staff-dashboard/import/students',
    'canteen': '/api/staff-dashboard/import/canteen',
    'school-gate': '/api/staff-dashboard/import/school-gate',
    'dormitory': '/api/staff-dashboard/import/dormitory',
    'network': '/api/staff-dashboard/import/network',
    'academic': '/api/staff-dashboard/import/academic',
    'calculate-stats': '/api/staff-dashboard/calculate-daily-statistics'
};

/**
 * 上传文件
 */
async function uploadFile(type) {
    const file = document.getElementById(`${type}-file`).files[0];
    const btn = document.getElementById(`btn-upload-${type}`);
    const progress = document.getElementById(`${type}-progress`);
    const result = document.getElementById(`${type}-result`);

    await performUpload({
        file: file,
        url: API_ENDPOINTS[type],
        statusUrlPrefix: '/api/staff-dashboard/import-status/',
        btn: btn,
        progressBar: progress,
        resultDiv: result,
        onSuccess: () => {
            // 上传成功后刷新统计数据
            loadStatistics();
        }
    });
}

/**
 * 加载统计数据
 */
async function loadStatistics() {
    try {
        const response = await fetch('/api/staff-dashboard/import-summary', {
            method: 'GET',
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // 调试：输出API返回数据
            // console.log('API返回数据:', data);
            // console.log('每日统计数量:', data.total_records.daily_statistics);
            
            // 更新统计卡片
            document.getElementById('stat-students').textContent = formatNumber(data.total_students);
            document.getElementById('stat-canteen').textContent = formatNumber(data.total_records.canteen);
            document.getElementById('stat-gate').textContent = formatNumber(data.total_records.school_gate);
            document.getElementById('stat-dorm').textContent = formatNumber(data.total_records.dormitory);
            document.getElementById('stat-network').textContent = formatNumber(data.total_records.network);
            document.getElementById('stat-academic').textContent = formatNumber(data.total_records.academic);
            document.getElementById('stat-daily-stats').textContent = formatNumber(data.total_records.daily_statistics);
        }
    } catch (e) {
        console.error('加载统计数据失败:', e);
    }
}

/**
 * 格式化数字（添加千位分隔符）
 */
function formatNumber(num) {
    // 处理 undefined、null 和非数字情况
    if (num === undefined || num === null || num === '' || isNaN(num)) {
        return '-';
    }
    // 处理数字 0
    if (num === 0) {
        return '0';
    }
    // 正常格式化
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// 页面加载时初始化
window.addEventListener('DOMContentLoaded', () => {
    loadStatistics();
});

/**
 * 触发统计计算
 */
async function triggerStatisticsCalculation() {
    const btn = document.getElementById('btn-calculate-stats');
    const startDate = document.getElementById('stats-start-date').value || null;
    const endDate = document.getElementById('stats-end-date').value || null;
    
    // 确认弹窗
    const rangeText = startDate && endDate 
        ? `${startDate} 至 ${endDate}` 
        : '最近30天数据';
    
    window.showConfirmDialog({
        title: '统计数据',
        message: `确定要统计 ${rangeText} 吗？\n\n此操作将计算每日统计结果，可能需要较长时间。`,
        primaryText: '开始统计',
        secondaryText: '取消',
        onPrimary: async function() {
            try {
                // 禁用按钮
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>统计中...';
                
                // 发起统计请求
                const response = await fetch(API_ENDPOINTS['calculate-stats'], {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        start_date: startDate,
                        end_date: endDate
                    })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.detail || '统计请求失败');
                }
                
                if (data.status === 'submitted') {
                    window.showMessage(`统计任务已提交，正在后台计算 ${rangeText}...`, 'info', 3000);
                    
                    // 轮询任务状态
                    await pollStatisticsTask(data.task_id);
                }
                
            } catch (error) {
                console.error('统计错误:', error);
                window.showMessage(`统计失败：${error.message}`, 'error', 5000);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<span class="icon" style="-webkit-mask-image: url(/static/icons/chart.svg); mask-image: url(/static/icons/chart.svg); width: 1rem; height: 1rem; display: inline-block; background: currentColor; margin-right: 0.35rem; vertical-align: -0.125rem;"></span>统计数据';
            }
        }
    });
}

/**
 * 轮询统计任务状态
 */
async function pollStatisticsTask(taskId) {
    const maxAttempts = 600;  // 最多轮询600次（约10分钟）
    let attempts = 0;
    
    while (attempts < maxAttempts) {
        try {
            const response = await fetch(`/api/staff-dashboard/import-status/${taskId}`);
            const status = await response.json();
            
            if (status.status === 'success') {
                showToast(`统计完成：${status.message}`, 'success');
                return;
            } else if (status.status === 'error') {
                showToast(`统计失败：${status.message}`, 'error');
                return;
            } else if (status.status === 'processing') {
                // 更新按钮文字显示进度
                const btn = document.getElementById('btn-calculate-stats');
                btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>统计中... ${status.current || 0}%`;
            }
            
            // 等待1秒后继续轮询
            await new Promise(resolve => setTimeout(resolve, 1000));
            attempts++;
            
        } catch (error) {
            console.error('查询任务状态错误:', error);
            attempts++;
        }
    }
    
    showToast('统计任务超时', 'error');
}

/**
 * 获取Cookie值
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * 确认清空每日统计
 */
function confirmClearStatistics() {
    window.showConfirmDialog({
        title: '清空每日统计',
        message: '此操作将永久删除所有每日统计结果。\n' +
            '此操作不可恢复，请确认是否继续？',
        primaryText: '确认清空',
        secondaryText: '取消',
        onPrimary: function() {
            clearStatistics();
        }
    });
}

/**
 * 清空每日统计
 */
async function clearStatistics() {
    const btn = document.getElementById('btn-clear-statistics');
    const originalContent = btn.innerHTML;
    
    try {
        // 禁用按钮
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>正在清空...';
        
        const response = await fetch('/api/staff-dashboard/clear-statistics', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || '清空统计失败');
        }
        
        if (data.status === 'success') {
            window.showMessage('每日统计清空成功！已删除 ' + data.deleted_count + ' 条统计记录', 'success', 3000);
            
            // 刷新统计数据
            loadStatistics();
        }
        
    } catch (error) {
        console.error('清空统计错误:', error);
        window.showMessage('清空失败：' + error.message, 'error', 5000);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalContent;
    }
}

/**
 * 确认清空数据
 */
function confirmClearData() {
    window.showConfirmDialog({
        title: '清空所有数据',
        message: '此操作将永久删除所有学生信息、行为数据及统计结果。\n' +
            '此操作不可恢复，请确认是否继续？',
        primaryText: '确认清空',
        secondaryText: '取消',
        onPrimary: function() {
            clearAllData();
        }
    });
}

/**
 * 清空所有数据
 */
async function clearAllData() {
    const btn = document.getElementById('btn-clear-data');
    const originalContent = btn.innerHTML;
    
    try {
        // 禁用按钮
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>正在清空...';
        
        const response = await fetch('/api/staff-dashboard/clear-all-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || '清空数据失败');
        }
        
        if (data.status === 'success') {
            window.showMessage('数据清空成功！已删除 ' + data.deleted_counts.students + ' 名学生及其所有相关数据', 'success', 3000);
            
            // 刷新统计数据
            loadStatistics();
        }
        
    } catch (error) {
        console.error('清空数据错误:', error);
        window.showMessage('清空失败：' + error.message, 'error', 5000);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalContent;
    }
}
