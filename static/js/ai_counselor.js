// AI 辅导员聊天功能
let currentSessionId = null;
let isStreaming = false;
let hljsReady = false;
let markedReady = false;

// 等待 hljs 和 marked 加载完成
function initLibraries() {
    // 配置 marked.js
    if (typeof marked !== 'undefined') {
        markedReady = true;
        marked.setOptions({
            highlight: function(code, lang) {
                if (!hljsReady) return code;
                if (lang && hljs.getLanguage(lang)) {
                    try {
                        return hljs.highlight(code, { language: lang }).value;
                    } catch (err) {
                        console.error('代码高亮失败:', err);
                    }
                }
                return hljs.highlightAuto(code).value;
            },
            breaks: true,
            gfm: true
        });
    }
    
    // 检查 hljs 是否加载
    if (typeof hljs !== 'undefined') {
        hljsReady = true;
    }
}

// ====================页面加载 ====================
document.addEventListener('DOMContentLoaded', function() {
    initLibraries();
    loadSessions();
    setupInputHandlers();
    
    // 点击屏幕其他区域关闭所有菜单
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.session-item')) {
            closeAllMenus();
        }
    });
});

// ==================== 移动端侧边栏控制 ====================
function toggleSidebar() {
    const sidebar = document.getElementById('chatSidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const isOpen = sidebar.classList.contains('open');
    if (isOpen) {
        closeSidebar();
    } else {
        sidebar.classList.add('open');
        overlay.classList.add('active');
    }
}

function closeSidebar() {
    const sidebar = document.getElementById('chatSidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
}

// ==================== 会话管理 ====================
async function loadSessions() {
    try {
        const response = await fetch('/ai-counselor/api/sessions/', {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            renderSessions(data.sessions);
        } else {
            showMessage('加载会话列表失败', 'error');
        }
    } catch (e) {
        console.error('加载会话失败:', e);
        document.getElementById('sessionsList').innerHTML = 
            '<div class="loading-sessions">加载失败</div>';
    }
}

function renderSessions(sessions) {
    const container = document.getElementById('sessionsList');
    
    if (sessions.length === 0) {
        container.innerHTML = '<div class="loading-sessions">暂无对话记录</div>';
        return;
    }
    
    container.innerHTML = sessions.map(session => `
        <div class="session-item ${session.id === currentSessionId ? 'active' : ''}" 
             data-session-id="${session.id}"
             onclick="handleSessionClick(event, ${session.id})">
            <div class="session-item-content">
                <div class="session-title" id="session-title-${session.id}">${escapeHtml(session.title)}</div>
                <div class="session-time">${session.updated_at}</div>
            </div>
            <button class="btn-session-menu" onclick="toggleSessionMenu(event, ${session.id})" title="更多操作">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/>
                </svg>
            </button>
            <div class="session-menu-dropdown" id="session-menu-${session.id}">
                <button onclick="startRename(event, ${session.id})">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    重命名
                </button>
                <button class="danger" onclick="deleteSession(event, ${session.id})">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
                    删除
                </button>
            </div>
        </div>
    `).join('');
}

// 会话项点击（区分点击菜单和加载会话）
function handleSessionClick(event, sessionId) {
    if (event.target.closest('.btn-session-menu') || event.target.closest('.session-menu-dropdown')) {
        return;
    }
    // 仅在移动端侧边栏已展开时才关闭
    const sidebar = document.getElementById('chatSidebar');
    if (sidebar && sidebar.classList.contains('open')) {
        closeSidebar();
    }
    loadSession(sessionId);
}

async function createNewSession() {
    currentSessionId = null;
    clearMessages();
    showWelcomeMessage();
    document.getElementById('userInput').focus();
}

async function loadSession(sessionId) {
    if (isStreaming) {
        showMessage('请等待当前消息发送完成', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/ai-counselor/api/sessions/${sessionId}/`, {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            currentSessionId = sessionId;
            clearMessages();
            renderMessages(data.messages);
            updateActiveSession(sessionId);
        } else {
            showMessage('加载会话失败', 'error');
        }
    } catch (e) {
        console.error('加载会话失败:', e);
        showMessage('加载会话失败', 'error');
    }
}

function updateActiveSession(sessionId) {
    document.querySelectorAll('.session-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 使用 data-session-id 属性查找元素
    const activeItem = document.querySelector(`.session-item[data-session-id="${sessionId}"]`);
    if (activeItem) {
        activeItem.classList.add('active');
    }
}

// ==================== 三点菜单控制 ====================
function toggleSessionMenu(event, sessionId) {
    event.stopPropagation();
    const menu = document.getElementById(`session-menu-${sessionId}`);
    const isOpen = menu.classList.contains('open');
    closeAllMenus();
    if (!isOpen) {
        menu.classList.add('open');
    }
}

function closeAllMenus() {
    document.querySelectorAll('.session-menu-dropdown.open').forEach(m => m.classList.remove('open'));
}

// ==================== 重命名功能 ====================
function startRename(event, sessionId) {
    event.stopPropagation();
    closeAllMenus();
    
    const titleEl = document.getElementById(`session-title-${sessionId}`);
    const currentTitle = titleEl.textContent;
    
    // 替换为输入框
    titleEl.innerHTML = `<input class="session-title-input" type="text" value="${escapeHtml(currentTitle)}" maxlength="100">`;
    const input = titleEl.querySelector('input');
    input.focus();
    input.select();
    
    const commit = async () => {
        const newTitle = input.value.trim();
        if (!newTitle || newTitle === currentTitle) {
            titleEl.textContent = currentTitle;
            return;
        }
        await submitRename(sessionId, newTitle, titleEl);
    };
    
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); commit(); }
        if (e.key === 'Escape') { titleEl.textContent = currentTitle; }
    });
    input.addEventListener('blur', commit);
}

async function submitRename(sessionId, newTitle, titleEl) {
    try {
        const resp = await fetch(`/ai-counselor/api/sessions/${sessionId}/rename/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ title: newTitle })
        });
        const data = await resp.json();
        if (data.status === 'success') {
            titleEl.textContent = data.title;
        } else {
            showMessage('重命名失败: ' + data.message, 'error');
            titleEl.textContent = newTitle;
        }
    } catch (e) {
        showMessage('重命名失败', 'error');
        titleEl.textContent = newTitle;
    }
}

// ==================== 删除会话 ====================
async function deleteSession(event, sessionId) {
    event.stopPropagation();
    closeAllMenus();
    
    showConfirmDialog({
        title: '删除对话',
        message: '确定要删除这条对话吗？此操作不可恢复。',
        primaryText: '确认删除',
        secondaryText: '取消',
        onPrimary: async function() {
            try {
                const resp = await fetch(`/ai-counselor/api/sessions/${sessionId}/delete/`, {
                    method: 'DELETE',
                    headers: { 'X-CSRFToken': getCookie('csrftoken') }
                });
                const data = await resp.json();
                if (data.status === 'success') {
                    if (currentSessionId === sessionId) {
                        currentSessionId = null;
                        clearMessages();
                        showWelcomeMessage();
                    }
                    loadSessions();
                } else {
                    showMessage('删除失败: ' + data.message, 'error');
                }
            } catch (e) {
                showMessage('删除失败', 'error');
            }
        }
    });
}

// ==================== 消息显示 ====================
function clearMessages() {
    document.getElementById('chatMessages').innerHTML = '';
}

function showWelcomeMessage() {
    const container = document.getElementById('chatMessages');
    container.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon">🤗</div>
            <h3>你好！我是小智</h3>
            <p>我是你的 AI 心理辅导员，可以帮助你：</p>
            <ul>
                <li>倾听你的困扰和烦恼</li>
                <li>提供学习、生活、情感方面的建议</li>
                <li>帮助你分析和解决问题</li>
            </ul>
            <p class="welcome-tip">💡 有什么想聊的吗？随时开始吧～</p>
        </div>
    `;
}

function renderMessages(messages) {
    const container = document.getElementById('chatMessages');
    
    messages.forEach(msg => {
        if (msg.role !== 'system') {
            appendMessage(msg.role, msg.content, false);
        }
    });
    
    forceScrollToBottom(); // 加载历史消息后滚到底部
}

function appendMessage(role, content, animate = true) {
    const container = document.getElementById('chatMessages');
    
    // 移除欢迎消息
    const welcome = container.querySelector('.welcome-message');
    if (welcome) {
        welcome.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;
    if (!animate) {
        messageDiv.style.animation = 'none';
    }
    
    // 使用图标而非 emoji
    const avatarIcon = role === 'user' 
        ? '<span class="icon" style="-webkit-mask-image: url(/static/icons/user.svg); mask-image: url(/static/icons/user.svg); width: 1.5rem; height: 1.5rem; margin: 0; background: white;"></span>'
        : '<span class="icon" style="-webkit-mask-image: url(/static/icons/message-circle.svg); mask-image: url(/static/icons/message-circle.svg); width: 1.5rem; height: 1.5rem; margin: 0; background: white;"></span>';
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatarIcon}</div>
        <div class="message-content" data-role="${role}"></div>
    `;
    
    const contentDiv = messageDiv.querySelector('.message-content');
    if (role === 'assistant') {
        contentDiv.innerHTML = markedReady ? marked.parse(content) : escapeHtml(content);
    } else {
        // 用户消息用 textContent 赋値，避免模板字符串缩进被 pre-wrap 显示
        contentDiv.textContent = content;
    }
    
    container.appendChild(messageDiv);
    // 发送消息时强制滚到底部
    forceScrollToBottom();
    
    // 代码高亮
    if (role === 'assistant' && hljsReady) {
        messageDiv.querySelectorAll('pre code').forEach(block => {
            try {
                // 获取语言
                const classes = block.className.split(' ');
                const langClass = classes.find(cls => cls.startsWith('language-'));
                const language = langClass ? langClass.replace('language-', '') : 'code';
                
                // 为 pre 添加 data-language 属性
                const pre = block.parentElement;
                if (pre && pre.tagName === 'PRE') {
                    pre.setAttribute('data-language', language);
                }
                
                // 高亮代码
                hljs.highlightElement(block);
                
                // 添加行号
                addLineNumbers(block);
            } catch (err) {
                console.error('代码高亮失败:', err);
            }
        });
    }
}

function showTypingIndicator() {
    const container = document.getElementById('chatMessages');
    const indicator = document.createElement('div');
    indicator.className = 'message message-assistant';
    indicator.id = 'typingIndicator';
    indicator.innerHTML = `
        <div class="message-avatar">
            <span class="icon" style="-webkit-mask-image: url('/static/icons/message-circle.svg'); mask-image: url('/static/icons/message-circle.svg'); width: 1.5rem; height: 1.5rem; margin: 0; background: white;"></span>
        </div>
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    container.appendChild(indicator);
    forceScrollToBottom(); // 显示加载指示器时强制滚到底部
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

// 智能滚动：仅当用户已在底部附近时才跟随
function scrollToBottom() {
    const container = document.getElementById('chatMessages');
    const threshold = 120; // px
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    if (distanceFromBottom <= threshold) {
        container.scrollTop = container.scrollHeight;
    }
}

// 强制滚到底部（发送消息时使用）
function forceScrollToBottom() {
    const container = document.getElementById('chatMessages');
    container.scrollTop = container.scrollHeight;
}

// ==================== 发送消息 ====================
async function sendMessage() {
    if (isStreaming) {
        return;
    }
    
    const input = document.getElementById('userInput');
    const message = input.value.trim();
    
    if (!message) {
        return;
    }
    
    // 显示用户消息
    appendMessage('user', message);
    input.value = '';
    autoResizeTextarea(input);
    
    // 禁用输入
    isStreaming = true;
    input.disabled = true;
    document.getElementById('btnSend').disabled = true;
    
    // 显示加载指示器
    showTypingIndicator();
    
    try {
        const response = await fetch('/ai-counselor/api/chat/stream/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                session_id: currentSessionId,
                message: message
            })
        });
        
        if (!response.ok) {
            throw new Error('请求失败');
        }
        
        // 处理 SSE 流（加载指示器将在第一次接收内容时移除）
        await handleStreamResponse(response);
        
    } catch (e) {
        console.error('发送消息失败:', e);
        removeTypingIndicator();
        showMessage('发送消息失败，请重试', 'error');
    } finally {
        isStreaming = false;
        input.disabled = false;
        document.getElementById('btnSend').disabled = false;
        input.focus();
    }
}

async function handleStreamResponse(response) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let assistantMessage = '';
    let messageElement = null;
    let isFirstContent = true;  // 标记是否是第一次接收内容
    
    while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // 保留不完整的行
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try {
                    const data = JSON.parse(line.slice(6));
                    
                    if (data.type === 'session_id') {
                        currentSessionId = data.session_id;
                        loadSessions(); // 刷新会话列表
                    } else if (data.type === 'content') {
                        // 第一次接收内容时移除加载指示器
                        if (isFirstContent) {
                            removeTypingIndicator();
                            isFirstContent = false;
                        }
                        
                        assistantMessage += data.content;
                        
                        // 创建或更新消息元素
                        if (!messageElement) {
                            const container = document.getElementById('chatMessages');
                            messageElement = document.createElement('div');
                            messageElement.className = 'message message-assistant';
                            messageElement.innerHTML = `
                                <div class="message-avatar">
                                    <span class="icon" style="-webkit-mask-image: url('/static/icons/message-circle.svg'); mask-image: url('/static/icons/message-circle.svg'); width: 1.5rem; height: 1.5rem; margin: 0; background: white;"></span>
                                </div>
                                <div class="message-content"></div>
                            `;
                            container.appendChild(messageElement);
                        }
                        
                        // 实时渲染 Markdown
                        const contentDiv = messageElement.querySelector('.message-content');
                        if (markedReady) {
                            contentDiv.innerHTML = marked.parse(assistantMessage);
                        } else {
                            contentDiv.textContent = assistantMessage;
                        }
                        
                        // 代码高亮
                        if (hljsReady) {
                            contentDiv.querySelectorAll('pre code').forEach(block => {
                                try {
                                    // 获取语言
                                    const classes = block.className.split(' ');
                                    const langClass = classes.find(cls => cls.startsWith('language-'));
                                    const language = langClass ? langClass.replace('language-', '') : 'code';
                                    
                                    // 为 pre 添加 data-language 属性
                                    const pre = block.parentElement;
                                    if (pre && pre.tagName === 'PRE') {
                                        pre.setAttribute('data-language', language);
                                    }
                                    
                                    // 高亮代码
                                    hljs.highlightElement(block);
                                    
                                    // 添加行号
                                    addLineNumbers(block);
                                } catch (err) {
                                    console.error('代码高亮失败:', err);
                                }
                            });
                        }
                        
                        scrollToBottom();
                    } else if (data.type === 'done') {
                        // 流结束
                        break;
                    } else if (data.type === 'error') {
                        throw new Error(data.message);
                    }
                } catch (e) {
                    console.error('解析 SSE 数据失败:', e);
                }
            }
        }
    }
}

// ==================== 输入处理 ====================
function setupInputHandlers() {
    const input = document.getElementById('userInput');
    
    // Enter 发送，Shift+Enter 换行
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // 自动调整高度
    input.addEventListener('input', function() {
        autoResizeTextarea(this);
    });
}

function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
}

// ==================== 工具函数 ====================
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function addLineNumbers(codeBlock) {
    // 检查是否已经添加过行号
    if (codeBlock.querySelector('.line')) {
        return;
    }
    
    const lines = codeBlock.innerHTML.split('\n');
    // 处理每一行，确保空行也有内容占位
    const wrappedLines = lines.map(line => {
        // 如果是空行，添加一个不可见的空格保持行高
        const content = line.trim() === '' ? '&nbsp;' : line;
        return `<span class="line">${content}</span>`;
    }).join('');  // 不加 \n，避免 block 元素间的换行符造成额外空白
    codeBlock.innerHTML = wrappedLines;
}

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
