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
