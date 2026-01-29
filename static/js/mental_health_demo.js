// 文件状态管理
const uploadedFiles = { 'canteen': false, 'school-gate': false, 'dorm-gate': false, 'network': false, 'grades': false };
const fileData = { 'canteen': null, 'school-gate': null, 'dorm-gate': null, 'network': null, 'grades': null };

// 初始化拖拽上传
document.querySelectorAll('.mh-upload-area').forEach(area => {
    area.addEventListener('dragover', (e) => { e.preventDefault(); area.classList.add('dragover'); });
    area.addEventListener('dragleave', () => area.classList.remove('dragover'));
    area.addEventListener('drop', (e) => {
        e.preventDefault();
        area.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const type = area.parentElement.id.replace('-form', '');
            const input = document.getElementById(`${type}-file`);
            const dt = new DataTransfer(); dt.items.add(files[0]);
            input.files = dt.files;
            handleFileSelect(input, type);
        }
    });
});

function handleFileSelect(input, type) {
    const file = input.files[0];
    if (!file) return;
    fileData[type] = file;
    const info = document.getElementById(`${type}-file-info`);
    info.innerHTML = `<strong>${file.name}</strong> (${(file.size/1024).toFixed(1)} KB)`;
    info.style.display = 'block';
    document.getElementById(`btn-upload-${type}`).disabled = false;
}

// 获取 CSRF Token
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

async function uploadFile(type) {
    const btn = document.getElementById(`btn-upload-${type}`);
    const progress = document.getElementById(`${type}-progress`);
    const bar = progress.querySelector('.progress-bar');
    const result = document.getElementById(`${type}-result`);
    
    btn.disabled = true;
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="loading-spinner"></span> 上传中...';
    progress.style.display = 'flex';
    bar.style.width = '0%';
    bar.textContent = '0%';
    
    const formData = new FormData();
    formData.append('file', fileData[type]);
    
    try {
        // 提交异步任务
        let uploadUrl = `/mental-health/upload/${type}/`;
        const response = await fetch(uploadUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'submitted') {
            // 任务已提交，开始轮询
            await pollUploadStatus(data.task_id, type, btn, progress, bar, result, originalText);
        } else {
            throw new Error(data.detail || '上传失败');
        }
    } catch (e) {
        bar.style.width = '0%';
        bar.textContent = '';
        result.innerHTML = `<div class="small text-danger">✗ ${e.message}</div>`;
        showToast(e.message, 'danger');
        btn.innerHTML = originalText;
        btn.disabled = false;
        setTimeout(() => { 
            progress.style.display = 'none';
        }, 3000);
    }
}

// 轮询上传任务状态
async function pollUploadStatus(taskId, type, btn, progress, bar, result, originalText) {
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/mental-health/upload-status/${taskId}/`, {
                method: 'GET',
                headers: { 'X-CSRFToken': getCookie('csrftoken') }
            });
            
            const data = await response.json();
            
            if (data.status === 'processing' || data.status === 'pending') {
                // 更新进度信息
                const progressPct = data.current ? Math.round((data.current / data.total) * 100) : 0;
                bar.style.width = `${progressPct}%`;
                bar.textContent = `${progressPct}%`;
                btn.innerHTML = `<span class="loading-spinner"></span> ${data.message}`;
            } else if (data.status === 'success') {
                // 任务完成
                clearInterval(pollInterval);
                bar.style.width = '100%';
                bar.textContent = '100%';
                btn.innerHTML = '<span class="loading-spinner"></span> 完成!';
                
                uploadedFiles[type] = true;
                result.innerHTML = `<div class="small text-success fw-bold">✓ 上传成功 (${data.records} 条记录)</div>`;
                showToast(`上传成功: ${fileData[type].name} (${data.records} 条记录)`, 'success');
                
                btn.innerHTML = originalText;
                btn.disabled = false;
                setTimeout(() => { 
                    progress.style.display = 'none';
                    bar.style.width = '0%';
                    bar.textContent = '';
                }, 3000);
            } else if (data.status === 'error') {
                // 任务失败
                clearInterval(pollInterval);
                throw new Error(data.message || '上传失败');
            }
        } catch (e) {
            clearInterval(pollInterval);
            bar.style.width = '0%';
            bar.textContent = '';
            result.innerHTML = `<div class="small text-danger">✗ ${e.message}</div>`;
            showToast(e.message, 'danger');
            btn.innerHTML = originalText;
            btn.disabled = false;
            setTimeout(() => { 
                progress.style.display = 'none';
            }, 3000);
        }
    }, 2000); // 每 2 秒轮询一次（上传比分析快）
}

function getFormattedTimestamp() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    return `${year}${month}${day}_${hours}${minutes}${seconds}`;
}

async function startAnalysis(type) {
    const btnId = type === 'comprehensive' ? 'btn-comp' : (type === 'ideology' ? 'btn-ideo' : 'btn-pov');
    const typeLabel = type === 'comprehensive' ? '综合分析' : (type === 'ideology' ? '精准思政分析' : '精准扶贫分析');
    const btn = document.getElementById(btnId);
    const btnText = btn.querySelector('.btn-text');
    const resultDiv = document.getElementById('analyse-result');
    
    const originalText = btnText.innerHTML;
    btn.disabled = true;
    btnText.innerHTML = '<span class="loading-spinner"></span> 正在提交任务...';
    resultDiv.style.display = 'none';

    // 获取参数
    let params = {};
    if (type === 'comprehensive') {
        params = {
            contamination: document.getElementById('param-comp-contamination').value / 100,
            night_start: document.getElementById('param-comp-night').value
        };
    } else if (type === 'ideology') {
        params = {
            positivity_high: document.getElementById('param-ideo-pos-high').value,
            positivity_low: document.getElementById('param-ideo-pos-low').value,
            intensity_high: document.getElementById('param-ideo-emo-high').value,
            intensity_low: document.getElementById('param-ideo-emo-low').value,
            radicalism_high: document.getElementById('param-ideo-rad-high').value,
            radicalism_low: document.getElementById('param-ideo-rad-low').value,
            night_start: document.getElementById('param-comp-night').value
        };
    } else if (type === 'poverty') {
        params = {
            poverty_threshold: document.getElementById('param-pov-threshold').value,
            trend_threshold: document.getElementById('param-pov-trend').value
        };
    }

    try {
        // 提交异步任务
        const response = await fetch(`/mental-health/analyze/${type}/`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(params)
        });

        const data = await response.json();
        
        if (data.status === 'submitted') {
            // 任务已提交，开始轮询
            btnText.innerHTML = '<span class="loading-spinner"></span> 正在分析中...';
            await pollTaskStatus(data.task_id, type, typeLabel, btnText, resultDiv, originalText, btn);
        } else {
            throw new Error(data.detail || '任务提交失败');
        }
    } catch (e) {
        resultDiv.innerHTML = `<h5 class="mb-2 fw-bold">✗ 分析失败</h5><p class="mb-0">${e.message}</p>`;
        resultDiv.className = 'mh-result error';
        resultDiv.style.display = 'block';
        showToast(e.message, 'danger');
        btnText.innerHTML = originalText;
        btn.disabled = false;
    }
}

// 轮询任务状态
async function pollTaskStatus(taskId, type, typeLabel, btnText, resultDiv, originalText, btn) {
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/mental-health/task-status/${taskId}/`, {
                method: 'GET',
                headers: { 'X-CSRFToken': getCookie('csrftoken') }
            });
            
            const data = await response.json();
            
            if (data.status === 'processing' || data.status === 'pending') {
                // 更新进度信息
                const progress = data.current ? Math.round((data.current / data.total) * 100) : 0;
                btnText.innerHTML = `<span class="loading-spinner"></span> ${data.message} (${progress}%)`;
            } else if (data.status === 'success') {
                // 任务完成，下载文件
                clearInterval(pollInterval);
                btnText.innerHTML = '<span class="loading-spinner"></span> 正在下载...';
                
                await downloadResult(taskId, typeLabel);
                
                resultDiv.innerHTML = '<h5 class="mb-2 fw-bold">✓ 分析成功</h5><p class="mb-0">报告已生成并开始下载。</p>';
                resultDiv.className = 'mh-result success';
                resultDiv.style.display = 'block';
                showToast('分析完成，报告已下载', 'success');
                
                btnText.innerHTML = originalText;
                btn.disabled = false;
            } else if (data.status === 'error') {
                // 任务失败
                clearInterval(pollInterval);
                throw new Error(data.message || '分析失败');
            }
        } catch (e) {
            clearInterval(pollInterval);
            resultDiv.innerHTML = `<h5 class="mb-2 fw-bold">✗ 分析失败</h5><p class="mb-0">${e.message}</p>`;
            resultDiv.className = 'mh-result error';
            resultDiv.style.display = 'block';
            showToast(e.message, 'danger');
            btnText.innerHTML = originalText;
            btn.disabled = false;
        }
    }, 2000); // 每 2 秒轮询一次
}

// 下载结果文件
async function downloadResult(taskId, typeLabel) {
    try {
        const response = await fetch(`/mental-health/download-result/${taskId}/`, {
            method: 'GET',
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const timestamp = getFormattedTimestamp();
            a.download = `${typeLabel}_${timestamp}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } else {
            const data = await response.json();
            throw new Error(data.detail || '文件下载失败');
        }
    } catch (e) {
        throw new Error('文件下载失败：' + e.message);
    }
}

// 显示提示信息
function showToast(message, type = 'info') {
    const toastEl = document.getElementById('mh-toast');
    const toastBody = document.getElementById('mh-toast-body');
    toastEl.className = `toast align-items-center border-0 text-white bg-${type}`;
    toastBody.innerText = message;
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
}

// 联动滑块值显示
document.getElementById('param-comp-contamination').addEventListener('input', (e) => {
    document.getElementById('val-comp-contamination').innerText = e.target.value + '%';
});

// 数字调整块逻辑 - 已迁移至 components.js

// 自定义下拉菜单交互逻辑 - 已迁移至 components.js
