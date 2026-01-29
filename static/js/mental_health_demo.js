// 文件状态管理 (仅保留业务状态)
const uploadedFiles = { 'canteen': false, 'school-gate': false, 'dorm-gate': false, 'network': false, 'grades': false };

/**
 * 业务特定的文件上传触发
 * 调用 components.js 中的 performUpload 通用函数
 */
async function uploadFile(type) {
    const file = document.getElementById(`${type}-file`).files[0];
    const btn = document.getElementById(`btn-upload-${type}`);
    const progress = document.getElementById(`${type}-progress`);
    const result = document.getElementById(`${type}-result`);

    await performUpload({
        file: file,
        url: `/api/mental-health/upload/${type}`,
        statusUrlPrefix: '/api/mental-health/upload-status/',
        btn: btn,
        progressBar: progress,
        resultDiv: result,
        onSuccess: () => { 
            uploadedFiles[type] = true; 
        }
    });
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

/**
 * 开始分析逻辑
 * 依然保留在这里，因为这是业务核心逻辑
 */
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
        const response = await fetch(`/api/mental-health/analyze/${type}`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(params)
        });

        const data = await response.json();
        
        if (data.status === 'submitted') {
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

async function pollTaskStatus(taskId, type, typeLabel, btnText, resultDiv, originalText, btn) {
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/mental-health/task-status/${taskId}`, {
                method: 'GET',
                headers: { 'X-CSRFToken': getCookie('csrftoken') }
            });
            
            const data = await response.json();
            
            if (data.status === 'processing' || data.status === 'pending') {
                const progress = data.current ? Math.round((data.current / data.total) * 100) : 0;
                btnText.innerHTML = `<span class="loading-spinner"></span> ${data.message} (${progress}%)`;
            } else if (data.status === 'success') {
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
    }, 2000);
}

async function downloadResult(taskId, typeLabel) {
    try {
        const response = await fetch(`/api/mental-health/download-result/${taskId}`, {
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
