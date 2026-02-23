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
    'academic': '/api/staff-dashboard/import/academic'
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
            
            // 更新统计卡片
            document.getElementById('stat-students').textContent = formatNumber(data.total_students);
            document.getElementById('stat-canteen').textContent = formatNumber(data.total_records.canteen);
            document.getElementById('stat-gate').textContent = formatNumber(data.total_records.school_gate);
            document.getElementById('stat-dorm').textContent = formatNumber(data.total_records.dormitory);
            document.getElementById('stat-network').textContent = formatNumber(data.total_records.network);
            document.getElementById('stat-academic').textContent = formatNumber(data.total_records.academic);
        }
    } catch (e) {
        console.error('加载统计数据失败:', e);
    }
}

/**
 * 格式化数字（添加千位分隔符）
 */
function formatNumber(num) {
    if (num === undefined || num === null) return '-';
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// 页面加载时初始化
window.addEventListener('DOMContentLoaded', () => {
    loadStatistics();
});

/**
 * 开始统计数据
 */
async function startStatistics() {
    const btn = document.getElementById('btn-start-statistics');
    const progress = document.getElementById('statistics-progress');
    const progressBar = progress.querySelector('.progress-bar');
    const result = document.getElementById('statistics-result');
    
    // 获取时间范围（可以从页面获取，这里使用默认值）
    const startDate = null;  // 默认30天前
    const endDate = null;    // 默认今天
    
    try {
        // 禁用按钮
        btn.disabled = true;
        btn.textContent = '统计中...';
        result.innerHTML = '';
        
        // 显示进度条
        progress.style.display = 'block';
        progressBar.style.width = '30%';
        
        // 发起统计请求
        const response = await fetch('/api/staff-dashboard/calculate-statistics', {
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
            // 轮询任务状态
            await pollTaskStatus(data.task_id, progressBar, result);
            
            // 统计完成后重新加载统计数据
            await loadStatistics();
        }
        
    } catch (error) {
        console.error('统计错误:', error);
        result.innerHTML = `<div class="alert alert-danger">统计失败：${error.message}</div>`;
        progress.style.display = 'none';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="icon" style="-webkit-mask-image: url(/static/icons/bar-chart.svg); mask-image: url(/static/icons/bar-chart.svg); width: 16px; height: 16px; background: currentColor; margin-right: 0.5rem;"></span>开始统计';
    }
}

/**
 * 轮询任务状态
 */
async function pollTaskStatus(taskId, progressBar, resultDiv) {
    const maxAttempts = 300;  // 最多轮询300次（约300秒）
    let attempts = 0;
    
    while (attempts < maxAttempts) {
        try {
            const response = await fetch(`/api/staff-dashboard/import-status/${taskId}`);
            const status = await response.json();
            
            // 更新进度条
            if (status.current !== undefined) {
                progressBar.style.width = `${status.current}%`;
            }
            
            if (status.status === 'success') {
                progressBar.style.width = '100%';
                resultDiv.innerHTML = `<div class="alert alert-success">${status.message}</div>`;
                setTimeout(() => {
                    progressBar.parentElement.style.display = 'none';
                }, 1000);
                return;
            } else if (status.status === 'error') {
                progressBar.style.width = '100%';
                progressBar.classList.add('bg-danger');
                resultDiv.innerHTML = `<div class="alert alert-danger">${status.message}</div>`;
                setTimeout(() => {
                    progressBar.parentElement.style.display = 'none';
                }, 2000);
                return;
            }
            
            // 等待1秒后继续轮询
            await new Promise(resolve => setTimeout(resolve, 1000));
            attempts++;
            
        } catch (error) {
            console.error('查询任务状态错误:', error);
            attempts++;
        }
    }
    
    throw new Error('统计任务超时');
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
 * 确认清空数据
 */
function confirmClearData() {
    window.showConfirmDialog({
        title: '清空所有数据',
        message: '此操作将永久删除所有学生信息及相关行为数据。\n' +
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
