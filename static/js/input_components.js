/**
 * Global UI Components Logic
 */

// 1. Utility Functions
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

function showToast(message, type = 'info') {
    const toastEl = document.getElementById('mh-toast');
    const toastBody = document.getElementById('mh-toast-body');
    if (!toastEl || !toastBody) return;
    
    // Support bootstrap colors (success, danger, info, etc.)
    toastEl.className = `toast align-items-center border-0 text-white bg-${type}`;
    toastBody.innerText = message;
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
}

// 2. Numeric Stepper Logic
function adjustStepper(inputId, delta) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    let val = parseFloat(input.value) || 0;
    val += delta;
    
    const step = parseFloat(input.getAttribute('step')) || 1;
    const decimals = step.toString().split('.')[1]?.length || 0;
    input.value = val.toFixed(decimals);
    
    input.dispatchEvent(new Event('input', { bubbles: true }));
}

// 3. Custom Dropdown Logic
function initDropdowns() {
    document.querySelectorAll('.custom-dropdown').forEach(dropdown => {
        const trigger = dropdown.querySelector('.dropdown-trigger');
        const items = dropdown.querySelectorAll('.dropdown-item');
        const hiddenInput = dropdown.querySelector('input[type="hidden"]');
        const selectedText = dropdown.querySelector('.selected-text');

        if (!trigger || dropdown.dataset.initialized) return;

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.custom-dropdown.active').forEach(active => {
                if (active !== dropdown) active.classList.remove('active');
            });
            dropdown.classList.toggle('active');
        });

        items.forEach(item => {
            item.addEventListener('click', () => {
                const value = item.getAttribute('data-value');
                // 获取纯文本（移除图标）
                const text = item.textContent.trim();
                if (selectedText) selectedText.textContent = text;
                if (hiddenInput) hiddenInput.value = value;
                items.forEach(i => i.classList.remove('selected'));
                item.classList.add('selected');
                dropdown.classList.remove('active');
                
                // 触发自定义事件
                dropdown.dispatchEvent(new CustomEvent('item-selected', {
                    detail: { value: value, text: text }
                }));
                
                if (hiddenInput) hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
            });
        });
        
        dropdown.dataset.initialized = "true";
    });
}

// 别名函数，保持向后兼容
function initAllDropdowns() {
    initDropdowns();
}

// 4. Range Slider Value Sync
function initRangeSliders() {
    document.querySelectorAll('.form-range').forEach(range => {
        const targetId = range.dataset.valueTarget;
        if (!targetId) return;
        
        const target = document.getElementById(targetId);
        if (!target) return;
        
        range.addEventListener('input', () => {
            const unit = range.dataset.unit || '';
            target.innerText = range.value + unit;
        });
    });
}

// 5. Upload Component Logic
function initUploadComponents() {
    document.querySelectorAll('.upload-item').forEach(item => {
        const area = item.querySelector('.upload-area');
        const input = item.querySelector('input[type="file"]');
        const info = item.querySelector('.selected-file');
        const btn = item.querySelector('button');
        
        if (!area || !input || item.dataset.initialized) return;

        // Drag & Drop
        area.addEventListener('dragover', (e) => { e.preventDefault(); area.classList.add('dragover'); });
        area.addEventListener('dragleave', () => area.classList.remove('dragover'));
        area.addEventListener('drop', (e) => {
            e.preventDefault();
            area.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const dt = new DataTransfer(); dt.items.add(files[0]);
                input.files = dt.files;
                handleLocalFileSelect(input, info, btn);
            }
        });

        // Click to select
        area.addEventListener('click', () => input.click());
        input.addEventListener('change', () => handleLocalFileSelect(input, info, btn));
        
        item.dataset.initialized = "true";
    });
}

function handleLocalFileSelect(input, infoDiv, btn) {
    const file = input.files[0];
    if (!file) return;
    if (infoDiv) {
        infoDiv.innerHTML = `<strong>${file.name}</strong> (${(file.size/1024).toFixed(1)} KB)`;
        infoDiv.style.display = 'block';
    }
    if (btn) btn.disabled = false;
}

// Reusable Upload Function
async function performUpload(options) {
    const { 
        file, 
        url, 
        statusUrlPrefix,
        btn, 
        progressBar, 
        resultDiv,
        onSuccess
    } = options;

    if (!file || !url) {
        showToast("未选择文件或配置错误", "danger");
        return;
    }

    const bar = progressBar?.querySelector('.progress-bar');
    const originalBtnHtml = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span> 上传中...';
    if (progressBar) progressBar.style.display = 'flex';
    if (bar) { bar.style.width = '0%'; bar.textContent = '0%'; }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(url, {
            method: 'POST',
            body: formData,
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        const data = await response.json();

        if (data.status === 'submitted' && statusUrlPrefix) {
            await pollUploadStatus(data.task_id, statusUrlPrefix, btn, progressBar, bar, resultDiv, originalBtnHtml, onSuccess);
        } else if (response.ok) {
            handleUploadSuccess(btn, progressBar, resultDiv, originalBtnHtml, "上传成功", onSuccess);
        } else {
            throw new Error(data.detail || '上传失败');
        }
    } catch (e) {
        handleUploadError(e.message, btn, progressBar, resultDiv, originalBtnHtml);
    }
}

async function pollUploadStatus(taskId, urlPrefix, btn, progress, bar, result, originalText, onSuccess) {
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${urlPrefix}${taskId}`, {
                method: 'GET',
                headers: { 'X-CSRFToken': getCookie('csrftoken') }
            });
            const data = await response.json();
            
            if (data.status === 'processing' || data.status === 'pending') {
                const pct = data.current ? Math.round((data.current / data.total) * 100) : 0;
                if (bar) { bar.style.width = `${pct}%`; bar.textContent = `${pct}%`; }
                btn.innerHTML = `<span class="loading-spinner"></span> ${data.message || '处理中...'}`;
            } else if (data.status === 'success') {
                clearInterval(pollInterval);
                if (bar) { bar.style.width = '100%'; bar.textContent = '100%'; }
                handleUploadSuccess(btn, progress, result, originalText, `成功 (${data.records || 0} 条)`, onSuccess);
            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                throw new Error(data.message || '处理失败');
            }
        } catch (e) {
            clearInterval(pollInterval);
            handleUploadError(e.message, btn, progress, result, originalText);
        }
    }, 2000);
}

function handleUploadSuccess(btn, progress, result, originalText, msg, callback) {
    if (btn) { btn.innerHTML = originalText; btn.disabled = false; }
    if (result) {
        result.innerHTML = `<div class="small text-success fw-bold">✓ ${msg}</div>`;
        result.style.display = 'block';
        result.className = 'mh-result success'; // 确保样式应用
    }
    showToast(`上传成功: ${msg}`, 'success');
    if (progress) setTimeout(() => { progress.style.display = 'none'; }, 3000);
    if (callback) callback();
}

function handleUploadError(msg, btn, progress, result, originalText) {
    if (btn) { btn.innerHTML = originalText; btn.disabled = false; }
    if (result) {
        result.innerHTML = `<div class="small text-danger">✗ ${msg}</div>`;
        result.style.display = 'block';
        result.className = 'mh-result error'; // 确保样式应用
    }
    showToast(msg, 'danger');
    if (progress) setTimeout(() => { progress.style.display = 'none'; }, 3000);
}

// 6. Checkbox Group with Auto-Sort (checked items on top)
function initCheckboxGroups() {
    document.querySelectorAll('.checkbox-group-scrollable').forEach(group => {
        if (group.dataset.initialized) return;
        
        const container = group.querySelector('.options-container');
        if (!container) return;
        
        // 查找 Django 渲染的外层 div (id以"id_"开头)
        const djangoContainer = container.querySelector('div[id^="id_"]');
        const targetContainer = djangoContainer || container;
        
        // 监听所有 checkbox 的变化
        const checkboxes = targetContainer.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                sortCheckboxOptions(targetContainer);
            });
        });
        
        // 初始化时排序一次
        sortCheckboxOptions(targetContainer);
        
        group.dataset.initialized = "true";
    });
}

function sortCheckboxOptions(container) {
    const labels = Array.from(container.querySelectorAll('label'));
    
    // 按选中状态排序：选中的在前，未选中的在后
    labels.sort((a, b) => {
        const checkboxA = a.querySelector('input[type="checkbox"]');
        const checkboxB = b.querySelector('input[type="checkbox"]');
        
        if (checkboxA.checked && !checkboxB.checked) return -1;
        if (!checkboxA.checked && checkboxB.checked) return 1;
        return 0;
    });
    
    // 重新添加到 DOM 中
    labels.forEach(label => {
        container.appendChild(label);
    });
}
document.addEventListener('click', () => {
    document.querySelectorAll('.custom-dropdown.active').forEach(dropdown => {
        dropdown.classList.remove('active');
    });
});

// Initialize on load
window.addEventListener('DOMContentLoaded', () => {
    initDropdowns();
    initRangeSliders();
    initUploadComponents();
    initCheckboxGroups();
});
