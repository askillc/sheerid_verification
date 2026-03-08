const API_BASE = '/api';
let authToken = localStorage.getItem('adminToken');
let allUsers = [];
let allJobs = [];
let currentUserId = null;
let currentPage = 1;
let totalPages = 1;
let searchTimeout = null;
const PAGE_SIZE = 15;

// Mobile menu state
let mobileMenuOpen = false;

// Helper function to format VIP expiry
function formatVipExpiry(vipExpiry, isVip) {
    if (!isVip) return '-';
    if (!vipExpiry) return '<span style="color:var(--warning)">⭐ Vĩnh viễn</span>';
    
    const expiry = new Date(vipExpiry);
    const now = new Date();
    const daysLeft = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
    
    if (daysLeft > 0) {
        const color = daysLeft <= 3 ? 'var(--danger)' : daysLeft <= 7 ? 'var(--warning)' : 'var(--success)';
        return `<span style="color:${color}">${expiry.toLocaleDateString('vi-VN')}</span><br><small style="color:var(--text-muted)">(còn ${daysLeft} ngày)</small>`;
    } else {
        return '<span style="color:var(--danger)">⚠️ Hết hạn</span>';
    }
}

// Mobile Menu Functions
function toggleMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobileOverlay');
    const menuIcon = document.getElementById('menuIcon');
    
    mobileMenuOpen = !mobileMenuOpen;
    
    if (mobileMenuOpen) {
        sidebar.classList.add('active');
        overlay.classList.add('active');
        menuIcon.classList.remove('fa-bars');
        menuIcon.classList.add('fa-times');
    } else {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        menuIcon.classList.remove('fa-times');
        menuIcon.classList.add('fa-bars');
    }
}

function closeMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobileOverlay');
    const menuIcon = document.getElementById('menuIcon');
    
    mobileMenuOpen = false;
    sidebar.classList.remove('active');
    overlay.classList.remove('active');
    menuIcon.classList.remove('fa-times');
    menuIcon.classList.add('fa-bars');
}

// Auto login if token exists
if (authToken) showDashboard();

// Login form handler
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('loginError');
    
    try {
        const response = await fetch(`${API_BASE}/admin/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await response.json();
        if (response.ok) {
            authToken = data.token;
            localStorage.setItem('adminToken', authToken);
            showDashboard();
        } else {
            errorDiv.textContent = data.error || 'Đăng nhập thất bại';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = 'Lỗi kết nối: ' + error.message;
        errorDiv.style.display = 'block';
    }
});

function showDashboard() {
    document.getElementById('loginBox').style.display = 'none';
    document.getElementById('dashboard').style.display = 'block';
    loadDashboardData();
}

function logout() {
    localStorage.removeItem('adminToken');
    location.reload();
}

async function loadDashboardData() {
    await Promise.all([loadStats(), loadUsers(), loadJobs(), loadTransactions(), loadSettings()]);
}


async function loadStats() {
    try {
        console.log('[DEBUG] Loading stats...');
        const response = await fetch(`${API_BASE}/admin/stats`, { 
            headers: { 'Authorization': `Bearer ${authToken}` } 
        });
        console.log('[DEBUG] Stats response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('[DEBUG] Stats data:', data);
            document.getElementById('totalUsers').textContent = data.totalUsers || 0;
            document.getElementById('vipUsers').textContent = data.vipUsers || 0;
            document.getElementById('blockedUsers').textContent = data.blockedUsers || 0;
            document.getElementById('totalJobs').textContent = data.totalJobs || 0;
            document.getElementById('totalTransactions').textContent = data.totalTransactions || 0;
        } else {
            console.error('[ERROR] Stats response not OK:', response.status, await response.text());
            // Set default values on error
            document.getElementById('totalUsers').textContent = '0';
            document.getElementById('vipUsers').textContent = '0';
            document.getElementById('blockedUsers').textContent = '0';
            document.getElementById('totalJobs').textContent = '0';
            document.getElementById('totalTransactions').textContent = '0';
        }
    } catch (error) { 
        console.error('[ERROR] Error loading stats:', error);
        // Set default values on error
        document.getElementById('totalUsers').textContent = '0';
        document.getElementById('vipUsers').textContent = '0';
        document.getElementById('blockedUsers').textContent = '0';
        document.getElementById('totalJobs').textContent = '0';
        document.getElementById('totalTransactions').textContent = '0';
    }
    
    // Load today's stats
    loadTodayStats();
}

async function loadTodayStats() {
    try {
        console.log('[DEBUG] Loading today stats...');
        const response = await fetch(`${API_BASE}/admin/stats/today`, { 
            headers: { 'Authorization': `Bearer ${authToken}` } 
        });
        console.log('[DEBUG] Today stats response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('[DEBUG] Today stats data:', data);
            document.getElementById('todayVerifyMain').textContent = data.todayVerify || 0;
            document.getElementById('todayCompletedMain').textContent = data.todayCompleted || 0;
            document.getElementById('todayNewUsers').textContent = data.todayNewUsers || 0;
            document.getElementById('todayTx').textContent = data.todayTransactions || 0;
            
            // Calculate success rate (only completed and failed, exclude fraud_reject, skipped, pending)
            const completed = data.todayCompleted || 0;
            const failed = data.todayFailed || 0;
            const denominator = completed + failed;
            const rate = denominator > 0 ? Math.round((completed / denominator) * 100) : 0;
            document.getElementById('todaySuccessRate').textContent = rate + '%';
            
            // Display today's revenue from SePay
            const revenue = data.todayRevenue || 0;
            document.getElementById('todayRevenue').textContent = formatCurrency(revenue);
        }
    } catch (error) { console.error('Error loading today stats:', error); }
}

// Format currency in VND - full detail
function formatCurrency(amount) {
    // Always show full number with thousand separators
    return amount.toLocaleString('vi-VN') + ' đ';
}

async function loadUsers(page = 1, search = '', filter = 'all') {
    try {
        const params = new URLSearchParams({ page, limit: PAGE_SIZE });
        if (search) params.append('search', search);
        if (filter && filter !== 'all') params.append('filter', filter);
        
        const response = await fetch(`${API_BASE}/admin/users?${params}`, { 
            headers: { 'Authorization': `Bearer ${authToken}` } 
        });
        if (response.ok) {
            const data = await response.json();
            allUsers = data.users || data;
            currentPage = data.page || 1;
            totalPages = data.totalPages || 1;
            displayUsers(allUsers);
        }
    } catch (error) { 
        document.getElementById('usersContent').innerHTML = '<p style="color:var(--danger)">Lỗi tải dữ liệu</p>'; 
    }
}

// Helper function to format VIP type badge
function getVipTypeBadge(user) {
    if (!user.is_vip) return '-';
    const vipType = user.vip_type || 'basic';
    const links = user.concurrent_links || 1;
    if (vipType === 'business') {
        return `<span class="badge" style="background:rgba(139,92,246,0.2);color:#8b5cf6"><i class="fas fa-gem"></i> Biz (${links})</span>`;
    } else if (vipType === 'pro') {
        return `<span class="badge" style="background:rgba(16,185,129,0.2);color:#10b981"><i class="fas fa-star"></i> Pro (${links})</span>`;
    }
    return `<span class="badge badge-warning"><i class="fas fa-crown"></i> Basic</span>`;
}

function displayUsers(users) {
    if (!users || users.length === 0) {
        document.getElementById('usersContent').innerHTML = '<p style="text-align:center;color:var(--text-muted)">Không có dữ liệu</p>';
        return;
    }
    const tableHtml = `<table>
        <thead><tr>
            <th>ID</th><th>Username</th><th>Coins</th><th>Cash</th><th>VIP</th><th>Trạng thái</th><th>Ngày tạo</th><th>Actions</th>
        </tr></thead>
        <tbody>${users.map(user => `<tr>
            <td><code>${user.telegram_id}</code></td>
            <td>${user.username || user.first_name || '-'}</td>
            <td><strong>${user.coins || 0}</strong></td>
            <td>${user.cash || 0}</td>
            <td>${getVipTypeBadge(user)}</td>
            <td>${user.is_blocked ? '<span class="badge badge-danger"><i class="fas fa-ban"></i> Khóa</span>' : '<span class="badge badge-success"><i class="fas fa-check"></i> Active</span>'}</td>
            <td>${user.created_at ? new Date(user.created_at).toLocaleDateString('vi-VN') : '-'}</td>
            <td style="display:flex;gap:6px"><button class="btn btn-sm btn-primary" onclick="viewUser(${user.telegram_id})"><i class="fas fa-eye"></i> Xem</button><button class="btn btn-sm" style="background:#0ea5e9;color:white" onclick="sendMessage(${user.telegram_id})" title="Gửi tin nhắn"><i class="fas fa-paper-plane"></i></button></td>
        </tr>`).join('')}</tbody>
    </table>`;
    
    const paginationHtml = `<div style="display:flex;justify-content:center;align-items:center;gap:12px;margin-top:20px;padding:16px 0">
        <button class="btn btn-sm btn-ghost" onclick="goToPage(1)" ${currentPage === 1 ? 'disabled' : ''}><i class="fas fa-angle-double-left"></i></button>
        <button class="btn btn-sm btn-ghost" onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}><i class="fas fa-angle-left"></i></button>
        <span style="padding:0 12px;color:var(--text)">Trang <strong>${currentPage}</strong> / ${totalPages}</span>
        <button class="btn btn-sm btn-ghost" onclick="goToPage(${currentPage + 1})" ${currentPage >= totalPages ? 'disabled' : ''}><i class="fas fa-angle-right"></i></button>
        <button class="btn btn-sm btn-ghost" onclick="goToPage(${totalPages})" ${currentPage >= totalPages ? 'disabled' : ''}><i class="fas fa-angle-double-right"></i></button>
    </div>`;
    
    document.getElementById('usersContent').innerHTML = tableHtml + paginationHtml;
}

function goToPage(page) {
    if (page < 1 || page > totalPages) return;
    const search = document.getElementById('userSearch').value.trim();
    const filter = document.getElementById('userFilter')?.value || 'all';
    loadUsers(page, search, filter);
}

function searchUsers() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        const query = document.getElementById('userSearch').value.trim();
        const filter = document.getElementById('userFilter')?.value || 'all';
        currentPage = 1;
        loadUsers(1, query, filter);
    }, 500);
}

function filterUsers() {
    const search = document.getElementById('userSearch').value.trim();
    const filter = document.getElementById('userFilter')?.value || 'all';
    currentPage = 1;
    loadUsers(1, search, filter);
}

async function viewUser(telegramId) {
    currentUserId = telegramId;
    try {
        const response = await fetch(`${API_BASE}/admin/users/${telegramId}`, { 
            headers: { 'Authorization': `Bearer ${authToken}` } 
        });
        const data = await response.json();
        
        if (!response.ok || data.error || !data.user) {
            alert('Lỗi: ' + (data.error || 'Không thể tải thông tin user'));
            return;
        }
        
        const user = data.user;
        // Format VIP type display
        const vipTypeDisplay = user.is_vip ? (() => {
            const vt = user.vip_type || 'basic';
            const links = user.concurrent_links || 1;
            if (vt === 'business') return `<span style="color:#8b5cf6;font-weight:700">💎 Business (${links} link)</span>`;
            if (vt === 'pro') return `<span style="color:#10b981;font-weight:700">⭐ Pro (${links} link)</span>`;
            return `<span style="color:#f59e0b;font-weight:700">👑 Basic (${links} link)</span>`;
        })() : '<span style="color:var(--text-muted)">Không</span>';
        
        document.getElementById('userDetailContent').innerHTML = `
            <div class="user-detail-grid">
                <div class="detail-item"><label>Telegram ID</label><span>${user.telegram_id}</span></div>
                <div class="detail-item"><label>Username</label><span>@${user.username || 'N/A'}</span></div>
                <div class="detail-item"><label>Tên</label><span>${user.first_name || ''} ${user.last_name || ''}</span></div>
                <div class="detail-item"><label>Coins</label><span style="color:var(--warning);font-weight:700">${user.coins || 0}</span></div>
                <div class="detail-item"><label>Cash</label><span style="color:var(--success);font-weight:700">${user.cash || 0}</span></div>
                <div class="detail-item"><label>VIP Type</label><span>${vipTypeDisplay}</span></div>
                <div class="detail-item"><label>Hạn VIP</label><span>${formatVipExpiry(user.vip_expiry, user.is_vip)}</span></div>
                <div class="detail-item"><label>Trạng thái</label><span>${user.is_blocked ? '🔒 Bị khóa' : '✅ Active'}</span></div>
                <div class="detail-item"><label>Ngôn ngữ</label><span>${user.language || 'vi'}</span></div>
            </div>
            <div class="mini-stats">
                <div class="mini-stat"><div class="value">${data.referralCount || 0}</div><div class="label">Referrals</div></div>
                <div class="mini-stat"><div class="value">${data.totalVerifications || 0}</div><div class="label">Tổng Verify</div></div>
                <div class="mini-stat"><div class="value">${data.successfulVerifications || 0}</div><div class="label">Thành công</div></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:15px">
                <button class="btn btn-success btn-sm" onclick="addCash(${user.telegram_id})" style="width:100%"><i class="fas fa-dollar-sign"></i> Cash</button>
                <button class="btn btn-warning btn-sm" onclick="addCoins(${user.telegram_id})" style="width:100%"><i class="fas fa-coins"></i> Xu</button>
                <button class="btn btn-primary btn-sm" onclick="setVip(${user.telegram_id})" style="width:100%"><i class="fas fa-crown"></i> VIP</button>
                <button class="btn ${user.is_blocked ? 'btn-success' : 'btn-danger'} btn-sm" onclick="toggleBlock(${user.telegram_id}, ${!user.is_blocked})" style="width:100%">
                    <i class="fas fa-${user.is_blocked ? 'unlock' : 'lock'}"></i> ${user.is_blocked ? 'Mở khóa' : 'Khóa'}
                </button>
                <button class="btn btn-ghost btn-sm" onclick="editUser(${user.telegram_id}); closeModal();" style="width:100%"><i class="fas fa-edit"></i> Sửa</button>
                <button class="btn btn-danger btn-sm" onclick="deleteUser(${user.telegram_id})" style="width:100%"><i class="fas fa-trash"></i> Xóa</button>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:20px">
                <button class="btn btn-sm" style="width:100%;background:var(--info);color:white" onclick="sendMessage(${user.telegram_id})"><i class="fas fa-paper-plane"></i> Gửi tin nhắn</button>
                <button class="btn btn-sm" style="width:100%;background:#9333ea;color:white" onclick="setDailyLimit(${user.telegram_id}, ${user.verify_limit || 0})"><i class="fas fa-shield-alt"></i> Giới hạn XU (${user.verify_limit || '∞'})</button>
                <button class="btn btn-sm" style="width:100%;background:#dc2626;color:white" onclick="setCashVerifyLimit(${user.telegram_id}, ${user.cash_verify_limit || 0})"><i class="fas fa-dollar-sign"></i> Giới hạn Cash (${user.cash_verify_limit || '∞'})</button>
            </div>
            <h4 style="margin:20px 0 12px;font-size:14px;color:var(--text-muted)">📜 Giao dịch gần đây</h4>
            <div id="userTransactionsContainer"></div>
        `;
        
        // Store transactions and render with pagination
        window.userTransactions = data.transactions || [];
        window.txPage = 1;
        renderUserTransactions();
        
        document.getElementById('userModal').classList.add('active');
    } catch (error) { alert('Lỗi: ' + error.message); }
}

function closeModal() { document.getElementById('userModal').classList.remove('active'); }
function closeEditModal() { document.getElementById('editModal').classList.remove('active'); }

// Render user transactions with pagination
function renderUserTransactions() {
    const TX_PER_PAGE = 5;
    const transactions = window.userTransactions || [];
    const page = window.txPage || 1;
    const totalPages = Math.ceil(transactions.length / TX_PER_PAGE) || 1;
    const start = (page - 1) * TX_PER_PAGE;
    const pageTx = transactions.slice(start, start + TX_PER_PAGE);
    
    let html = `<table style="font-size:13px"><thead><tr><th style="width:100px">Loại</th><th style="width:80px">Số tiền</th><th>Mô tả</th><th style="width:90px">Ngày</th></tr></thead><tbody>`;
    
    if (pageTx.length === 0) {
        html += '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Chưa có giao dịch</td></tr>';
    } else {
        pageTx.forEach(tx => {
            const isCash = tx.type && (tx.type.includes('cash') || tx.type.includes('deposit') || tx.type.includes('binance'));
            const amount = tx.amount || tx.coins || 0;
            const displayAmount = isCash ? amount.toLocaleString('vi-VN') + ' Cash' : amount + ' Xu';
            const badgeClass = tx.type && (tx.type.includes('deposit') || tx.type.includes('binance')) ? 'success' : 'primary';
            const desc = (tx.description || '-').length > 40 ? tx.description.substring(0, 40) + '...' : (tx.description || '-');
            html += `<tr>
                <td><span class="badge badge-${badgeClass}" style="font-size:10px">${tx.type}</span></td>
                <td style="color:${isCash ? 'var(--success)' : 'var(--warning)'}"><strong>${displayAmount}</strong></td>
                <td style="font-size:11px" title="${tx.description || ''}">${desc}</td>
                <td style="font-size:11px">${tx.created_at ? new Date(tx.created_at).toLocaleDateString('vi-VN') : '-'}</td>
            </tr>`;
        });
    }
    html += '</tbody></table>';
    
    // Pagination
    if (transactions.length > TX_PER_PAGE) {
        html += `<div style="display:flex;justify-content:center;align-items:center;gap:8px;margin-top:10px;font-size:12px">
            <button class="btn btn-sm btn-ghost" onclick="changeTxPage(-1)" ${page <= 1 ? 'disabled' : ''}><i class="fas fa-chevron-left"></i></button>
            <span style="color:var(--text-muted)">${page} / ${totalPages}</span>
            <button class="btn btn-sm btn-ghost" onclick="changeTxPage(1)" ${page >= totalPages ? 'disabled' : ''}><i class="fas fa-chevron-right"></i></button>
        </div>`;
    }
    
    document.getElementById('userTransactionsContainer').innerHTML = html;
}

function changeTxPage(delta) {
    const totalPages = Math.ceil((window.userTransactions || []).length / 5) || 1;
    window.txPage = Math.max(1, Math.min(totalPages, (window.txPage || 1) + delta));
    renderUserTransactions();
}

// Send direct message to user
async function sendMessage(telegramId) {
    const message = prompt('Nhập tin nhắn gửi cho user:');
    if (!message || message.trim() === '') return;
    
    try {
        const response = await fetch(`${API_BASE}/admin/users/${telegramId}/send-message`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message.trim() })
        });
        const data = await response.json();
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể gửi tin nhắn'));
            return;
        }
        alert('✅ Đã gửi tin nhắn thành công!');
    } catch (error) { alert('Lỗi kết nối: ' + error.message); }
}

// Set daily verify limit for user
async function setDailyLimit(telegramId, currentLimit) {
    const limit = prompt(`Giới hạn verify/ngày (0 = không giới hạn):\n\nHiện tại: ${currentLimit || 'Không giới hạn'}`, currentLimit || '0');
    if (limit === null) return;
    
    const limitNum = parseInt(limit) || 0;
    try {
        const response = await fetch(`${API_BASE}/admin/users/${telegramId}/set-daily-limit`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ daily_limit: limitNum })
        });
        const data = await response.json();
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể cập nhật'));
            return;
        }
        closeModal();
        loadUsers();
        alert(`✅ Đã cập nhật giới hạn: ${limitNum === 0 ? 'Không giới hạn' : limitNum + ' lượt/ngày'}`);
    } catch (error) { alert('Lỗi kết nối: ' + error.message); }
}

// Set daily cash verify limit for user
async function setCashVerifyLimit(telegramId, currentLimit) {
    const limit = prompt(`Giới hạn verify bằng CASH/ngày (0 = không giới hạn):\n\nHiện tại: ${currentLimit || 'Không giới hạn'}`, currentLimit || '0');
    if (limit === null) return;
    
    const limitNum = parseInt(limit) || 0;
    try {
        const response = await fetch(`${API_BASE}/admin/users/${telegramId}/set-cash-verify-limit`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ cash_verify_limit: limitNum })
        });
        const data = await response.json();
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể cập nhật'));
            return;
        }
        closeModal();
        loadUsers();
        alert(`✅ Đã cập nhật giới hạn Cash: ${limitNum === 0 ? 'Không giới hạn' : limitNum + ' lượt/ngày'}`);
    } catch (error) { alert('Lỗi kết nối: ' + error.message); }
}

async function editUser(telegramId) {
    const user = allUsers.find(u => u.telegram_id === telegramId);
    if (!user) return;
    currentUserId = telegramId;
    
    document.getElementById('editUserContent').innerHTML = `
        <form id="editUserForm">
            <div class="user-detail-grid">
                <div class="form-group">
                    <label>Coins</label>
                    <input type="number" id="editCoins" value="${user.coins || 0}">
                </div>
                <div class="form-group">
                    <label>Cash</label>
                    <input type="number" id="editCash" value="${user.cash || 0}">
                </div>
                <div class="form-group">
                    <label>Giới hạn Verify</label>
                    <input type="number" id="editVerifyLimit" value="${user.verify_limit || ''}" placeholder="Để trống = không giới hạn">
                </div>
            </div>
            <div style="display:flex;gap:20px;margin:20px 0">
                <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                    <input type="checkbox" id="editVip" ${user.is_vip ? 'checked' : ''}> ⭐ VIP
                </label>
                <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                    <input type="checkbox" id="editBlocked" ${user.is_blocked ? 'checked' : ''}> 🔒 Khóa tài khoản
                </label>
            </div>
            <div class="action-buttons">
                <button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Lưu thay đổi</button>
                <button type="button" class="btn btn-ghost" onclick="closeEditModal()">Hủy</button>
            </div>
        </form>
    `;
    document.getElementById('editModal').classList.add('active');
    
    document.getElementById('editUserForm').onsubmit = async (e) => {
        e.preventDefault();
        try {
            await fetch(`${API_BASE}/admin/users/${telegramId}`, {
                method: 'PATCH',
                headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    coins: parseInt(document.getElementById('editCoins').value),
                    cash: parseInt(document.getElementById('editCash').value),
                    verify_limit: document.getElementById('editVerifyLimit').value || null,
                    is_vip: document.getElementById('editVip').checked,
                    is_blocked: document.getElementById('editBlocked').checked
                })
            });
            closeEditModal();
            loadUsers();
            alert('✅ Đã cập nhật thành công!');
        } catch (error) { alert('Lỗi: ' + error.message); }
    };
}

async function toggleBlock(telegramId, blocked) {
    const reason = blocked ? prompt('Lý do khóa (tùy chọn):') : '';
    if (blocked && reason === null) return;
    
    try {
        const response = await fetch(`${API_BASE}/admin/users/${telegramId}/block`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ blocked, reason: reason || '' })
        });
        const data = await response.json();
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể cập nhật'));
            return;
        }
        closeModal();
        loadUsers();
        loadStats();
        alert(blocked ? '🔒 Đã khóa user!' : '🔓 Đã mở khóa user!');
    } catch (error) { alert('Lỗi kết nối: ' + error.message); }
}


async function addCash(telegramId) {
    const cash = prompt('Số cash cần thêm (số âm để trừ):');
    if (cash === null || cash === '') return;
    const reason = prompt('Lý do:') || 'Admin adjustment';
    
    try {
        const response = await fetch(`${API_BASE}/admin/users/${telegramId}/add-balance`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ coins: 0, cash: parseInt(cash) || 0, reason })
        });
        const data = await response.json();
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể cập nhật'));
            return;
        }
        closeModal();
        loadUsers();
        alert('💵 Đã cập nhật Cash!');
    } catch (error) { alert('Lỗi kết nối: ' + error.message); }
}

async function addCoins(telegramId) {
    const coins = prompt('Số xu cần thêm (số âm để trừ):');
    if (coins === null || coins === '') return;
    const reason = prompt('Lý do:') || 'Admin adjustment';
    
    try {
        const response = await fetch(`${API_BASE}/admin/users/${telegramId}/add-balance`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ coins: parseInt(coins) || 0, cash: 0, reason })
        });
        const data = await response.json();
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể cập nhật'));
            return;
        }
        closeModal();
        loadUsers();
        alert('🪙 Đã cập nhật Xu!');
    } catch (error) { alert('Lỗi kết nối: ' + error.message); }
}

async function setVip(telegramId) {
    // Show VIP tier selection dialog
    const vipType = prompt(`Chọn gói VIP:
    
1 = VIP Basic (1 link) - 800 cash
2 = VIP Pro (3 link song song) - 1200 cash  
3 = VIP Business (5 link song song) - 1500 cash
0 = Hủy VIP

Nhập số (1/2/3/0):`);
    
    if (vipType === null || vipType === '') return;
    
    const typeNum = parseInt(vipType);
    if (![0, 1, 2, 3].includes(typeNum)) {
        alert('❌ Vui lòng nhập 0, 1, 2 hoặc 3');
        return;
    }
    
    let vipTypeStr = 'basic';
    let concurrentLinks = 1;
    
    if (typeNum === 0) {
        // Cancel VIP
    } else if (typeNum === 2) {
        vipTypeStr = 'pro';
        concurrentLinks = 3;
    } else if (typeNum === 3) {
        vipTypeStr = 'business';
        concurrentLinks = 5;
    }
    
    const days = typeNum > 0 ? prompt('Số ngày VIP:', '7') : '0';
    if (days === null) return;
    
    try {
        const response = await fetch(`${API_BASE}/admin/users/${telegramId}/set-vip`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                is_vip: parseInt(days) > 0, 
                days: parseInt(days) || 30,
                vip_type: vipTypeStr,
                concurrent_links: concurrentLinks
            })
        });
        const data = await response.json();
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể cập nhật'));
            return;
        }
        closeModal();
        loadUsers();
        loadStats();
        const tierName = typeNum === 0 ? 'Đã hủy' : typeNum === 1 ? 'Basic' : typeNum === 2 ? 'Pro' : 'Business';
        alert(`⭐ Đã cập nhật VIP ${tierName}!`);
    } catch (error) { alert('Lỗi kết nối: ' + error.message); }
}

async function deleteUser(telegramId) {
    if (!confirm(`⚠️ Bạn có chắc muốn XÓA VĨNH VIỄN user ${telegramId}?\n\nTất cả dữ liệu sẽ bị xóa!`)) return;
    if (!confirm('🚨 XÁC NHẬN LẦN CUỐI: Xóa user này?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/admin/users/${telegramId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await response.json();
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể xóa'));
            return;
        }
        closeModal();
        loadUsers();
        loadStats();
        alert('🗑️ Đã xóa user!');
    } catch (error) { alert('Lỗi kết nối: ' + error.message); }
}

// ============================================
// REVENUE STATS - Thống kê doanh thu verify
// ============================================
async function loadRevenueStats() {
    try {
        document.getElementById('revenueContent').innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i><p>Đang tải...</p></div>';
        
        const response = await fetch(`${API_BASE}/admin/stats/revenue`, { 
            headers: { 'Authorization': `Bearer ${authToken}` } 
        });
        
        if (response.ok) {
            const data = await response.json();
            displayRevenueStats(data);
        } else {
            document.getElementById('revenueContent').innerHTML = '<p style="color:var(--danger)">Lỗi tải dữ liệu</p>';
        }
    } catch (error) { 
        console.error('Revenue stats error:', error);
        document.getElementById('revenueContent').innerHTML = '<p style="color:var(--danger)">Lỗi kết nối: ' + error.message + '</p>'; 
    }
}

function formatVND(amount) {
    return amount.toLocaleString('vi-VN') + ' đ';
}

function displayRevenueStats(data) {
    const types = data.types || {};
    const total = data.total || {};
    
    // Type icons and colors
    const typeConfig = {
        'perplexity': { icon: 'fa-brain', color: '#8b5cf6', name: 'Perplexity' },
        'gemini': { icon: 'fa-robot', color: '#6366f1', name: 'Gemini' },
        'spotify': { icon: 'fa-spotify', color: '#1db954', name: 'Spotify' }
    };
    
    let html = `
        <!-- Total Summary -->
        <div style="background:linear-gradient(135deg, #1e293b 0%, #334155 100%);border-radius:16px;padding:24px;margin-bottom:24px">
            <h3 style="color:#fff;margin:0 0 20px 0;font-size:18px"><i class="fas fa-chart-pie"></i> Tổng kết Doanh thu</h3>
            <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(150px, 1fr));gap:16px">
                <div style="background:rgba(16,185,129,0.2);border-radius:12px;padding:16px;text-align:center">
                    <div style="font-size:28px;font-weight:700;color:#10b981">${total.success || 0}</div>
                    <div style="color:#94a3b8;font-size:13px">Thành công</div>
                </div>
                <div style="background:rgba(59,130,246,0.2);border-radius:12px;padding:16px;text-align:center">
                    <div style="font-size:20px;font-weight:700;color:#3b82f6">${formatVND(total.revenue || 0)}</div>
                    <div style="color:#94a3b8;font-size:13px">Doanh thu</div>
                </div>
                <div style="background:rgba(239,68,68,0.2);border-radius:12px;padding:16px;text-align:center">
                    <div style="font-size:20px;font-weight:700;color:#ef4444">${formatVND(total.cost || 0)}</div>
                    <div style="color:#94a3b8;font-size:13px">Vốn</div>
                </div>
                <div style="background:rgba(245,158,11,0.2);border-radius:12px;padding:16px;text-align:center">
                    <div style="font-size:20px;font-weight:700;color:${total.profit >= 0 ? '#10b981' : '#ef4444'}">${formatVND(total.profit || 0)}</div>
                    <div style="color:#94a3b8;font-size:13px">Lợi nhuận (${total.profit_margin || 0}%)</div>
                </div>
            </div>
        </div>
        
        <!-- Per Type Stats -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(320px, 1fr));gap:20px">
    `;
    
    for (const [typeName, typeData] of Object.entries(types)) {
        const config = typeConfig[typeName] || { icon: 'fa-check', color: '#6366f1', name: typeName };
        const profitColor = typeData.profit >= 0 ? '#10b981' : '#ef4444';
        const profitIcon = typeData.profit >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';
        
        html += `
            <div style="background:var(--card-bg);border-radius:16px;padding:20px;border:1px solid var(--border)">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
                    <div style="width:48px;height:48px;border-radius:12px;background:${config.color}20;display:flex;align-items:center;justify-content:center">
                        <i class="fas ${config.icon}" style="font-size:20px;color:${config.color}"></i>
                    </div>
                    <div>
                        <h4 style="margin:0;color:var(--text);font-size:16px">${config.name}</h4>
                        <span style="color:var(--text-muted);font-size:12px">Vốn: ${formatVND(typeData.cost_per_unit)} | Bán: ${formatVND(typeData.sell_price)}</span>
                    </div>
                </div>
                
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
                    <div style="background:var(--bg);border-radius:8px;padding:12px">
                        <div style="font-size:24px;font-weight:700;color:#10b981">${typeData.success}</div>
                        <div style="color:var(--text-muted);font-size:12px">Thành công</div>
                    </div>
                    <div style="background:var(--bg);border-radius:8px;padding:12px">
                        <div style="font-size:24px;font-weight:700;color:#ef4444">${typeData.failed}</div>
                        <div style="color:var(--text-muted);font-size:12px">Thất bại</div>
                    </div>
                </div>
                
                <div style="background:var(--bg);border-radius:8px;padding:12px;margin-bottom:12px">
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                        <span style="color:var(--text-muted);font-size:13px">Doanh thu:</span>
                        <span style="color:#3b82f6;font-weight:600">${formatVND(typeData.revenue)}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                        <span style="color:var(--text-muted);font-size:13px">Vốn:</span>
                        <span style="color:#ef4444;font-weight:600">${formatVND(typeData.cost)}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;border-top:1px solid var(--border);padding-top:8px">
                        <span style="color:var(--text-muted);font-size:13px">Lợi nhuận:</span>
                        <span style="color:${profitColor};font-weight:700">
                            <i class="fas ${profitIcon}" style="font-size:10px"></i> ${formatVND(typeData.profit)}
                        </span>
                    </div>
                </div>
                
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <span style="color:var(--text-muted);font-size:12px">Tỷ lệ thành công:</span>
                    <span class="badge ${typeData.success_rate >= 50 ? 'badge-success' : 'badge-warning'}">${typeData.success_rate}%</span>
                </div>
            </div>
        `;
    }
    
    html += `</div>
        
        <!-- Price Info -->
        <div style="background:var(--card-bg);border-radius:12px;padding:16px;margin-top:24px;border:1px solid var(--border)">
            <h4 style="margin:0 0 12px 0;color:var(--text);font-size:14px"><i class="fas fa-info-circle"></i> Thông tin giá</h4>
            <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:12px;font-size:13px">
                <div style="color:var(--text-muted)">
                    <i class="fas fa-brain" style="color:#8b5cf6"></i> <strong>Perplexity:</strong> Vốn 12.5k, Bán 10k → <span style="color:#ef4444">Lỗ 2.5k/cái</span>
                </div>
                <div style="color:var(--text-muted)">
                    <i class="fas fa-robot" style="color:#6366f1"></i> <strong>Gemini:</strong> Vốn 5k, Bán 10k → <span style="color:#10b981">Lời 5k/cái</span>
                </div>
                <div style="color:var(--text-muted)">
                    <i class="fab fa-spotify" style="color:#1db954"></i> <strong>Spotify:</strong> Vốn 5k, Bán 10k → <span style="color:#10b981">Lời 5k/cái</span>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('revenueContent').innerHTML = html;
}

// Jobs pagination state
let jobsCurrentPage = 1;
const JOBS_PER_PAGE = 20;

async function loadJobs() {
    try {
        const response = await fetch(`${API_BASE}/admin/jobs`, { 
            headers: { 'Authorization': `Bearer ${authToken}` } 
        });
        if (response.ok) {
            allJobs = await response.json();
            jobsCurrentPage = 1; // Reset to first page
            displayJobs(allJobs);
        }
    } catch (error) { 
        document.getElementById('jobsContent').innerHTML = '<p style="color:var(--danger)">Lỗi tải dữ liệu</p>'; 
    }
}


function displayJobs(jobs) {
    if (!jobs || jobs.length === 0) {
        document.getElementById('jobsContent').innerHTML = '<p style="text-align:center;color:var(--text-muted)">Không có dữ liệu</p>';
        return;
    }
    
    // Pagination calculation
    const totalJobs = jobs.length;
    const totalPages = Math.ceil(totalJobs / JOBS_PER_PAGE);
    const startIndex = (jobsCurrentPage - 1) * JOBS_PER_PAGE;
    const endIndex = Math.min(startIndex + JOBS_PER_PAGE, totalJobs);
    const pageJobs = jobs.slice(startIndex, endIndex);
    
    // Helper function to get status badge
    function getStatusBadge(status) {
        if (status === 'completed' || status === 'success') return { class: 'success', icon: 'check', text: 'Thành công' };
        if (status === 'failed' || status === 'failure') return { class: 'danger', icon: 'times', text: 'Thất bại' };
        if (status === 'canceled' || status === 'cancelled') return { class: 'warning', icon: 'ban', text: 'Canceled' };
        if (status === 'fraud_reject') return { class: 'danger', icon: 'ban', text: 'FRAUD' };
        if (status === 'pending') return { class: 'warning', icon: 'clock', text: 'Đang xử lý' };
        if (status === 'processing') return { class: 'warning', icon: 'spinner', text: 'Đang xử lý' };
        if (status === 'invalid_link') return { class: 'danger', icon: 'exclamation-triangle', text: 'Link lỗi' };
        return { class: 'warning', icon: 'clock', text: status || 'Không rõ' };
    }
    
    // Helper function to get verification type display
    function getVerificationTypeDisplay(type, jobType) {
        if (jobType === 'sheerid_bot') {
            if (type === 'gemini') return '<span class="badge" style="background:rgba(99,102,241,0.2);color:#6366f1"><i class="fas fa-robot"></i> Gemini</span>';
            if (type === 'perplexity') return '<span class="badge" style="background:rgba(139,92,246,0.2);color:#8b5cf6"><i class="fas fa-brain"></i> Perplexity</span>';
            if (type === 'teacher') return '<span class="badge" style="background:rgba(245,158,11,0.2);color:#f59e0b"><i class="fas fa-chalkboard-teacher"></i> Teacher</span>';
        }
        // Legacy types
        if (type === 'sheerid' || type === 'legacy' || !type) return '<span class="badge" style="background:rgba(16,185,129,0.2);color:#10b981"><i class="fas fa-graduation-cap"></i> Student</span>';
        if (type === 'chatgpt') return '<span class="badge" style="background:rgba(245,158,11,0.2);color:#f59e0b"><i class="fas fa-chalkboard-teacher"></i> Teacher</span>';
        return `<span class="badge badge-primary">${type}</span>`;
    }
    
    // Helper to shorten job ID (first 16 chars for better visibility)
    function shortJobId(id) {
        return id ? id.substring(0, 16) + '...' : '-';
    }
    
    let html = `<table style="width:100%">
        <thead><tr>
            <th style="width:18%">Job ID</th>
            <th style="width:12%">User ID</th>
            <th style="width:12%">Status</th>
            <th style="width:15%">Type</th>
            <th style="width:25%">Trường</th>
            <th style="width:18%">Ngày</th>
        </tr></thead>
        <tbody>${pageJobs.map(job => {
            const badge = getStatusBadge(job.status);
            const typeDisplay = getVerificationTypeDisplay(job.verification_type, job.job_type);
            return `<tr>
            <td title="${job.job_id}"><code style="font-size:11px">${shortJobId(job.job_id)}</code></td>
            <td>${job.telegram_id}</td>
            <td><span class="badge badge-${badge.class}">
                <i class="fas fa-${badge.icon}"></i> ${badge.text}
            </span></td>
            <td>${typeDisplay}</td>
            <td title="${job.university || '-'}">${job.university || '-'}</td>
            <td>${job.created_at ? new Date(job.created_at).toLocaleString('vi-VN') : '-'}</td>
        </tr>`;
        }).join('')}</tbody>
    </table>`;
    
    // Add pagination controls
    html += `<div style="display:flex;justify-content:space-between;align-items:center;margin-top:16px;padding:12px 0;border-top:1px solid var(--border)">
        <div style="color:var(--text-muted);font-size:13px">
            Hiển thị ${startIndex + 1}-${endIndex} / ${totalJobs} jobs
        </div>
        <div style="display:flex;align-items:center;gap:8px">
            <button class="btn btn-sm btn-ghost" onclick="goToJobsPage(1)" ${jobsCurrentPage === 1 ? 'disabled' : ''}>
                <i class="fas fa-angle-double-left"></i>
            </button>
            <button class="btn btn-sm btn-ghost" onclick="goToJobsPage(${jobsCurrentPage - 1})" ${jobsCurrentPage === 1 ? 'disabled' : ''}>
                <i class="fas fa-angle-left"></i>
            </button>
            <span style="padding:0 12px;color:var(--text);font-size:13px">
                Trang <strong>${jobsCurrentPage}</strong> / ${totalPages}
            </span>
            <button class="btn btn-sm btn-ghost" onclick="goToJobsPage(${jobsCurrentPage + 1})" ${jobsCurrentPage >= totalPages ? 'disabled' : ''}>
                <i class="fas fa-angle-right"></i>
            </button>
            <button class="btn btn-sm btn-ghost" onclick="goToJobsPage(${totalPages})" ${jobsCurrentPage >= totalPages ? 'disabled' : ''}>
                <i class="fas fa-angle-double-right"></i>
            </button>
        </div>
    </div>`;
    
    document.getElementById('jobsContent').innerHTML = html;
}

function goToJobsPage(page) {
    const totalPages = Math.ceil(allJobs.length / JOBS_PER_PAGE);
    if (page < 1 || page > totalPages) return;
    jobsCurrentPage = page;
    
    // Check if there's a search filter active
    const query = document.getElementById('jobSearch').value.toLowerCase();
    if (query) {
        const filtered = allJobs.filter(job => 
            job.job_id.toLowerCase().includes(query) || 
            job.telegram_id.toString().includes(query)
        );
        displayJobs(filtered);
    } else {
        displayJobs(allJobs);
    }
}

function searchJobs() {
    const query = document.getElementById('jobSearch').value.toLowerCase();
    jobsCurrentPage = 1; // Reset to first page when searching
    const filtered = allJobs.filter(job => 
        job.job_id.toLowerCase().includes(query) || 
        job.telegram_id.toString().includes(query)
    );
    displayJobs(filtered);
}

async function loadTransactions() {
    try {
        const response = await fetch(`${API_BASE}/admin/transactions`, { 
            headers: { 'Authorization': `Bearer ${authToken}` } 
        });
        if (response.ok) {
            const transactions = await response.json();
            if (!transactions || transactions.length === 0) {
                document.getElementById('transactionsContent').innerHTML = '<p style="text-align:center;color:var(--text-muted)">Không có dữ liệu</p>';
                return;
            }
            document.getElementById('transactionsContent').innerHTML = `<table>
                <thead><tr><th>ID</th><th>User</th><th>Loại</th><th>Số tiền</th><th>Mô tả</th><th>Ngày</th></tr></thead>
                <tbody>${transactions.map(tx => `<tr>
                    <td>${tx.id}</td>
                    <td>${tx.user_id || tx.telegram_id}</td>
                    <td><span class="badge badge-primary">${tx.type}</span></td>
                    <td><strong>${tx.amount || tx.coins || 0}</strong></td>
                    <td>${tx.description || '-'}</td>
                    <td>${tx.created_at ? new Date(tx.created_at).toLocaleString('vi-VN') : '-'}</td>
                </tr>`).join('')}</tbody>
            </table>`;
        }
    } catch (error) { 
        document.getElementById('transactionsContent').innerHTML = '<p style="color:var(--danger)">Lỗi tải dữ liệu</p>'; 
    }
}


async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE}/admin/settings`, { 
            headers: { 'Authorization': `Bearer ${authToken}` } 
        });
        if (response.ok) {
            const settings = await response.json();
            const maintenanceToggle = document.getElementById('maintenanceToggle');
            const verifyToggle = document.getElementById('verifyMaintenanceToggle');
            
            if (settings.maintenance_mode) maintenanceToggle.classList.add('active');
            else maintenanceToggle.classList.remove('active');
            
            if (settings.verify_maintenance) verifyToggle.classList.add('active');
            else verifyToggle.classList.remove('active');
            
            // Load VC (Teacher) maintenance status
            const vcToggle = document.getElementById('vcMaintenanceToggle');
            if (vcToggle) {
                if (settings.vc_maintenance) vcToggle.classList.add('active');
                else vcToggle.classList.remove('active');
            }
            
            // Load fast mode status
            const fastModeToggle = document.getElementById('fastModeToggle');
            if (fastModeToggle) {
                if (settings.fast_mode) fastModeToggle.classList.add('active');
                else fastModeToggle.classList.remove('active');
            }
            
            // Load Binance maintenance status
            const binanceToggle = document.getElementById('binanceMaintenanceToggle');
            if (binanceToggle) {
                if (settings.binance_maintenance) binanceToggle.classList.add('active');
                else binanceToggle.classList.remove('active');
            }
        }
        
        // Load verify config
        loadVerifyConfig();
        
        // Load maintenance message settings
        loadMaintenanceMessage();
    } catch (error) { console.error('Error loading settings:', error); }
}

// Load verify configuration
async function loadVerifyConfig() {
    try {
        const response = await fetch(`${API_BASE}/admin/verify-config`, { 
            headers: { 'Authorization': `Bearer ${authToken}` } 
        });
        if (response.ok) {
            const config = await response.json();
            renderVerifyConfig(config);
        }
    } catch (error) { 
        console.error('Error loading verify config:', error);
        document.getElementById('verifyConfigContent').innerHTML = '<p style="color:var(--danger)">Lỗi tải cấu hình</p>';
    }
}

// Render verify config UI
function renderVerifyConfig(config) {
    const student = config.student || {};
    const teacher = config.teacher || {};
    
    document.getElementById('verifyConfigContent').innerHTML = `
        <div style="margin-bottom:20px">
            <h4 style="color:var(--primary);margin-bottom:12px">📚 Student Verification</h4>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
                <div class="form-group" style="margin:0">
                    <label style="font-size:12px;color:var(--text-muted)">Organization ID</label>
                    <input type="text" id="studentOrgId" value="${student.organization_id || ''}" style="width:100%;padding:8px;background:var(--card);border:1px solid var(--border);border-radius:6px;color:var(--text)">
                </div>
                <div class="form-group" style="margin:0">
                    <label style="font-size:12px;color:var(--text-muted)">Email Domain</label>
                    <input type="text" id="studentEmailDomain" value="${student.email_domain || ''}" placeholder="cos.edu" style="width:100%;padding:8px;background:var(--card);border:1px solid var(--border);border-radius:6px;color:var(--text)">
                </div>
            </div>
            <div class="form-group" style="margin:10px 0 0">
                <label style="font-size:12px;color:var(--text-muted)">Organization Name</label>
                <input type="text" id="studentOrgName" value="${student.organization_name || ''}" style="width:100%;padding:8px;background:var(--card);border:1px solid var(--border);border-radius:6px;color:var(--text)">
            </div>
            <div class="form-group" style="margin:10px 0 0">
                <label style="font-size:12px;color:var(--text-muted)">Card Template</label>
                <select id="studentCardTemplate" style="width:100%;padding:8px;background:var(--card);border:1px solid var(--border);border-radius:6px;color:var(--text)">
                    <option value="card-template-uk.png" ${student.card_template === 'card-template-uk.png' ? 'selected' : ''}>UK Template</option>
                    <option value="card-template-germany.png" ${student.card_template === 'card-template-germany.png' ? 'selected' : ''}>Germany Template</option>
                    <option value="card-template-us.png" ${student.card_template === 'card-template-us.png' ? 'selected' : ''}>US Template</option>
                </select>
            </div>
        </div>
        
        <div style="margin-bottom:20px">
            <h4 style="color:var(--warning);margin-bottom:12px">👨‍🏫 Teacher Verification</h4>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
                <div class="form-group" style="margin:0">
                    <label style="font-size:12px;color:var(--text-muted)">Organization ID</label>
                    <input type="text" id="teacherOrgId" value="${teacher.organization_id || ''}" style="width:100%;padding:8px;background:var(--card);border:1px solid var(--border);border-radius:6px;color:var(--text)">
                </div>
                <div class="form-group" style="margin:0">
                    <label style="font-size:12px;color:var(--text-muted)">Email Domain</label>
                    <input type="text" id="teacherEmailDomain" value="${teacher.email_domain || ''}" placeholder="gmail.com" style="width:100%;padding:8px;background:var(--card);border:1px solid var(--border);border-radius:6px;color:var(--text)">
                </div>
            </div>
            <div class="form-group" style="margin:10px 0 0">
                <label style="font-size:12px;color:var(--text-muted)">Organization Name</label>
                <input type="text" id="teacherOrgName" value="${teacher.organization_name || ''}" style="width:100%;padding:8px;background:var(--card);border:1px solid var(--border);border-radius:6px;color:var(--text)">
            </div>
        </div>
        
        <button class="btn btn-primary" onclick="saveVerifyConfig()" style="width:100%"><i class="fas fa-save"></i> Lưu cấu hình</button>
    `;
}

// Save verify config
async function saveVerifyConfig() {
    const config = {
        student: {
            organization_id: document.getElementById('studentOrgId').value,
            organization_name: document.getElementById('studentOrgName').value,
            email_domain: document.getElementById('studentEmailDomain').value,
            card_template: document.getElementById('studentCardTemplate').value
        },
        teacher: {
            organization_id: document.getElementById('teacherOrgId').value,
            organization_name: document.getElementById('teacherOrgName').value,
            email_domain: document.getElementById('teacherEmailDomain').value
        }
    };
    
    try {
        const response = await fetch(`${API_BASE}/admin/verify-config`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        const data = await response.json();
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể lưu'));
            return;
        }
        alert('✅ Đã lưu cấu hình! Cần deploy lại để áp dụng thay đổi vào code.');
    } catch (error) { alert('Lỗi kết nối: ' + error.message); }
}

function switchTab(tab) {
    // Close mobile menu when switching tabs
    closeMobileMenu();
    
    // Update nav links
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    event.target.closest('.nav-link').classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(tab + 'Tab').classList.add('active');
    
    // Load data for specific tabs
    if (tab === 'fraud') {
        loadFraudData();
    } else if (tab === 'proxy') {
        loadProxyStatus();
    } else if (tab === 'revenue') {
        loadRevenueStats();
    } else if (tab === 'config') {
        loadVerificationPrices();
    } else if (tab === 'shop') {
        loadShopProducts();
    } else if (tab === 'announcement') {
        loadAnnouncements();
    }
}

async function toggleMaintenance() {
    const toggle = document.getElementById('maintenanceToggle');
    const enabled = !toggle.classList.contains('active');
    
    try {
        const response = await fetch(`${API_BASE}/admin/settings/maintenance`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });
        const data = await response.json();
        if (response.ok && data.success) {
            toggle.classList.toggle('active');
            console.log('✅ Maintenance mode:', enabled);
        } else {
            alert('Lỗi: ' + (data.error || 'Không thể cập nhật'));
        }
    } catch (error) { 
        console.error('❌ Error:', error);
        alert('Lỗi: ' + error.message); 
    }
}

async function toggleVerifyMaintenance() {
    const toggle = document.getElementById('verifyMaintenanceToggle');
    const enabled = !toggle.classList.contains('active');
    
    try {
        const response = await fetch(`${API_BASE}/admin/settings/verify-maintenance`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });
        const data = await response.json();
        if (response.ok && data.success) {
            toggle.classList.toggle('active');
            console.log('✅ Verify maintenance:', enabled);
        } else {
            alert('Lỗi: ' + (data.error || 'Không thể cập nhật'));
        }
    } catch (error) { 
        console.error('❌ Error:', error);
        alert('Lỗi: ' + error.message); 
    }
}

async function toggleVcMaintenance() {
    const toggle = document.getElementById('vcMaintenanceToggle');
    const enabled = !toggle.classList.contains('active');
    
    try {
        const response = await fetch(`${API_BASE}/admin/settings/vc-maintenance`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });
        const data = await response.json();
        if (response.ok && data.success) {
            toggle.classList.toggle('active');
            console.log('🎓 VC Teacher maintenance:', enabled);
        } else {
            alert('Lỗi: ' + (data.error || 'Không thể cập nhật'));
        }
    } catch (error) { 
        console.error('❌ Error:', error);
        alert('Lỗi: ' + error.message); 
    }
}

async function toggleBinanceMaintenance() {
    const toggle = document.getElementById('binanceMaintenanceToggle');
    const enabled = !toggle.classList.contains('active');
    
    try {
        const response = await fetch(`${API_BASE}/admin/settings/binance-maintenance`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });
        const data = await response.json();
        if (response.ok && data.success) {
            toggle.classList.toggle('active');
            console.log('💰 Binance maintenance:', enabled);
        } else {
            alert('Lỗi: ' + (data.error || 'Không thể cập nhật'));
        }
    } catch (error) { 
        console.error('❌ Error:', error);
        alert('Lỗi: ' + error.message); 
    }
}

async function toggleFastMode() {
    const toggle = document.getElementById('fastModeToggle');
    const enabled = !toggle.classList.contains('active');
    
    try {
        const response = await fetch(`${API_BASE}/admin/settings/fast-mode`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });
        const data = await response.json();
        if (response.ok && data.success) {
            toggle.classList.toggle('active');
            console.log('⚡ Fast mode:', enabled);
        } else {
            alert('Lỗi: ' + (data.error || 'Không thể cập nhật'));
        }
    } catch (error) { 
        console.error('❌ Error:', error);
        alert('Lỗi: ' + error.message); 
    }
}

// ==================== MAINTENANCE MESSAGE FUNCTIONS ====================

async function loadMaintenanceMessage() {
    try {
        const response = await fetch(`${API_BASE}/admin/settings/maintenance-message`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (response.ok) {
            const data = await response.json();
            if (data.reason) document.getElementById('maintenanceReason').value = data.reason;
            if (data.time) document.getElementById('maintenanceTime').value = data.time;
            if (data.channel) document.getElementById('maintenanceChannel').value = data.channel;
            updateMaintenancePreview();
        }
    } catch (error) {
        console.error('❌ Error loading maintenance message:', error);
    }
}

function updateMaintenancePreview() {
    const reason = document.getElementById('maintenanceReason').value || 'Cập nhật hệ thống';
    const time = document.getElementById('maintenanceTime').value || '30 phút';
    const channel = document.getElementById('maintenanceChannel').value || 'https://t.me/channel_sheerid_vip_bot';
    
    const preview = `🔧 Bot đang trong chế độ bảo trì

📝 Lý do: ${reason}
⏰ Thời gian bảo trì dự kiến: ${time}
📢 Sẽ thông báo khi hoàn tất bảo trì tại kênh thông báo: ${channel}!

Cảm ơn bạn đã kiên nhẫn chờ đợi! 🙏`;
    
    document.getElementById('maintenancePreviewText').textContent = preview;
    document.getElementById('maintenancePreview').style.display = 'block';
}

async function saveMaintenanceMessage() {
    const reason = document.getElementById('maintenanceReason').value.trim();
    const time = document.getElementById('maintenanceTime').value.trim();
    const channel = document.getElementById('maintenanceChannel').value.trim();
    const statusEl = document.getElementById('maintenanceMsgStatus');
    
    if (!reason) {
        statusEl.innerHTML = '<span style="color:var(--danger)">❌ Vui lòng nhập lý do bảo trì</span>';
        return;
    }
    
    statusEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang lưu...';
    
    try {
        const response = await fetch(`${API_BASE}/admin/settings/maintenance-message`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ reason, time, channel })
        });
        const data = await response.json();
        
        if (response.ok && data.success) {
            statusEl.innerHTML = '<span style="color:var(--success)">✅ Đã lưu thành công!</span>';
            updateMaintenancePreview();
            setTimeout(() => { statusEl.innerHTML = ''; }, 3000);
        } else {
            statusEl.innerHTML = `<span style="color:var(--danger)">❌ ${data.error || 'Lỗi không xác định'}</span>`;
        }
    } catch (error) {
        console.error('❌ Error:', error);
        statusEl.innerHTML = `<span style="color:var(--danger)">❌ ${error.message}</span>`;
    }
}

// Add event listeners for live preview
document.addEventListener('DOMContentLoaded', function() {
    const inputs = ['maintenanceReason', 'maintenanceTime', 'maintenanceChannel'];
    inputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', updateMaintenancePreview);
    });
});

// ==================== GIFTCODE FUNCTIONS ====================

async function loadGiftcodes() {
    try {
        const response = await fetch(`${API_BASE}/admin/giftcodes`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await response.json();
        
        if (data && data.giftcodes) {
            let html = `<table>
                <thead><tr>
                    <th>Code</th><th>Loại</th><th>Số lượng</th><th>Đã dùng</th><th>Tối đa</th><th>Trạng thái</th><th>Actions</th>
                </tr></thead><tbody>`;
            
            data.giftcodes.forEach(g => {
                const statusBadge = g.is_active 
                    ? '<span class="badge badge-success"><i class="fas fa-check"></i> Active</span>' 
                    : '<span class="badge badge-danger"><i class="fas fa-times"></i> Inactive</span>';
                html += `<tr>
                    <td><strong>${g.code}</strong></td>
                    <td>${g.reward_type === 'coins' ? '🪙 Xu' : '💵 Cash'}</td>
                    <td>${g.reward_amount}</td>
                    <td>${g.current_uses || 0}</td>
                    <td>${g.max_uses}</td>
                    <td>${statusBadge}</td>
                    <td>
                        <button class="btn btn-sm btn-ghost" onclick="viewGiftcodeUsage(${g.id}, '${g.code}')"><i class="fas fa-eye"></i></button>
                        ${g.is_active ? `<button class="btn btn-sm btn-danger" onclick="deleteGiftcode(${g.id}, '${g.code}')"><i class="fas fa-trash"></i></button>` : ''}
                    </td>
                </tr>`;
            });
            html += '</tbody></table>';
            document.getElementById('giftcodesContent').innerHTML = html;
        }
    } catch (error) {
        document.getElementById('giftcodesContent').innerHTML = `<p style="color:var(--danger)">Lỗi: ${error.message}</p>`;
    }
}

async function createGiftcode() {
    const statusEl = document.getElementById('giftcodeStatus');
    const code = document.getElementById('newGiftcodeCode').value.trim().toUpperCase();
    const rewardType = document.getElementById('newGiftcodeType').value;
    const rewardAmount = parseInt(document.getElementById('newGiftcodeAmount').value);
    const maxUses = parseInt(document.getElementById('newGiftcodeMaxUses').value);

    if (!code) { statusEl.innerHTML = '<span style="color:var(--danger)">❌ Vui lòng nhập mã code</span>'; return; }
    if (!rewardAmount || rewardAmount <= 0) { statusEl.innerHTML = '<span style="color:var(--danger)">❌ Số lượng phải > 0</span>'; return; }

    statusEl.innerHTML = '<span style="color:var(--primary)"><i class="fas fa-spinner fa-spin"></i> Đang tạo...</span>';

    try {
        const response = await fetch(`${API_BASE}/admin/giftcodes`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, reward_type: rewardType, reward_amount: rewardAmount, max_uses: maxUses || 100 })
        });
        const data = await response.json();
        
        if (data.success) {
            statusEl.innerHTML = '<span style="color:var(--success)">✅ Tạo thành công!</span>';
            document.getElementById('newGiftcodeCode').value = '';
            document.getElementById('newGiftcodeAmount').value = '';
            loadGiftcodes();
        } else {
            statusEl.innerHTML = `<span style="color:var(--danger)">❌ ${data.error || 'Lỗi tạo giftcode'}</span>`;
        }
    } catch (error) {
        statusEl.innerHTML = `<span style="color:var(--danger)">❌ ${error.message}</span>`;
    }
    setTimeout(() => { statusEl.innerHTML = ''; }, 5000);
}

async function deleteGiftcode(id, code) {
    if (!confirm(`Bạn có chắc muốn vô hiệu hóa giftcode "${code}"?`)) return;
    try {
        const response = await fetch(`${API_BASE}/admin/giftcodes/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await response.json();
        if (data.success) {
            alert('✅ Đã vô hiệu hóa giftcode');
            loadGiftcodes();
        } else {
            alert('❌ Lỗi: ' + (data.error || 'Unknown error'));
        }
    } catch (error) { alert('❌ Lỗi: ' + error.message); }
}

async function viewGiftcodeUsage(id, code) {
    try {
        const response = await fetch(`${API_BASE}/admin/giftcodes/${id}/usage`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await response.json();
        
        if (data && data.usage) {
            let msg = `📊 Lịch sử sử dụng giftcode "${code}":\n\n`;
            if (data.usage.length === 0) {
                msg += 'Chưa có ai sử dụng.';
            } else {
                data.usage.forEach((u, i) => {
                    const user = u.users || {};
                    const name = user.username || user.first_name || user.telegram_id || 'Unknown';
                    const time = new Date(u.used_at).toLocaleString('vi-VN');
                    msg += `${i + 1}. ${name} - ${time}\n`;
                });
            }
            alert(msg);
        }
    } catch (error) { alert('Lỗi: ' + error.message); }
}

// ==================== CHART FUNCTIONS ====================

let verifyChart = null;

async function loadVerifyChart() {
    const days = document.getElementById('chartDays')?.value || 7;
    try {
        const response = await fetch(`${API_BASE}/admin/stats/verify-daily?days=${days}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await response.json();
        if (data && data.stats) {
            renderChart(data.stats);
        }
    } catch (error) { console.error('Load chart error:', error); }
}

async function loadVerifySummary() {
    try {
        const response = await fetch(`${API_BASE}/admin/stats/verify-summary`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await response.json();
        if (data) {
            document.getElementById('todayVerify').textContent = data.today?.total || 0;
            document.getElementById('todayCompleted').textContent = data.today?.completed || 0;
            document.getElementById('totalVerify').textContent = data.all_time?.total || 0;
            document.getElementById('totalCompleted').textContent = data.all_time?.completed || 0;
            document.getElementById('successRate').textContent = (data.success_rate || 0) + '%';
        }
    } catch (error) { console.error('Load summary error:', error); }
}

function renderChart(stats) {
    const ctx = document.getElementById('verifyChart')?.getContext('2d');
    if (!ctx) return;
    
    if (verifyChart) verifyChart.destroy();

    const labels = stats.map(s => s.date);
    const completedData = stats.map(s => s.completed);
    const failedData = stats.map(s => s.failed);

    verifyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Thành công',
                    data: completedData,
                    backgroundColor: 'rgba(16, 185, 129, 0.8)',
                    borderColor: 'rgba(16, 185, 129, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Thất bại',
                    data: failedData,
                    backgroundColor: 'rgba(239, 68, 68, 0.8)',
                    borderColor: 'rgba(239, 68, 68, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                x: { stacked: true, ticks: { color: '#9399b2' }, grid: { color: '#45475a' } },
                y: { stacked: true, beginAtZero: true, ticks: { color: '#9399b2' }, grid: { color: '#45475a' } }
            },
            plugins: {
                title: { display: true, text: 'Số lượng Verify theo ngày', color: '#cdd6f4' },
                legend: { position: 'top', labels: { color: '#cdd6f4' } }
            }
        }
    });
}

// Update switchTab to load data for new tabs
const originalSwitchTab = switchTab;
switchTab = function(tab) {
    // Close mobile menu when switching tabs
    closeMobileMenu();
    
    // Update nav links
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    event.target.closest('.nav-link').classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(tab + 'Tab').classList.add('active');
    
    // Load data for specific tabs
    if (tab === 'giftcodes') loadGiftcodes();
    if (tab === 'charts') { loadVerifyChart(); loadVerifySummary(); }
    if (tab === 'sellers') loadSellers();
    if (tab === 'proxy') loadProxyStatus();
};


// ==================== VIP & BLOCKED USERS FUNCTIONS ====================

// Show VIP Users Modal
async function showVipUsers() {
    document.getElementById('vipModal').classList.add('active');
    document.getElementById('vipUsersContent').innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Đang tải...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/admin/users?filter=vip&limit=100`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await response.json();
        const users = data.users || data || [];
        
        if (users.length === 0) {
            document.getElementById('vipUsersContent').innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:40px">Không có VIP user nào</p>';
            return;
        }
        
        // Count expired VIPs
        const expiredUsers = users.filter(u => u.vip_expiry && new Date(u.vip_expiry) < new Date());
        
        let html = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
            <span style="color:var(--text-muted)">Tổng: <strong style="color:var(--warning)">${users.length}</strong> VIP users</span>
            ${expiredUsers.length > 0 ? `<button class="btn btn-sm btn-danger" onclick="cleanupExpiredVips()"><i class="fas fa-broom"></i> Dọn ${expiredUsers.length} VIP hết hạn</button>` : ''}
        </div>`;
        html += `<table>
            <thead><tr>
                <th>ID</th><th>Username</th><th>Tên</th><th>Coins</th><th>Cash</th><th>Hạn VIP</th><th style="width:100px">Actions</th>
            </tr></thead>
            <tbody>`;
        
        users.forEach(user => {
            // Format VIP expiry
            let vipExpiryDisplay = '-';
            let isExpired = false;
            if (user.vip_expiry) {
                const expiry = new Date(user.vip_expiry);
                const now = new Date();
                const daysLeft = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
                if (daysLeft > 0) {
                    const color = daysLeft <= 3 ? 'var(--danger)' : daysLeft <= 7 ? 'var(--warning)' : 'var(--success)';
                    vipExpiryDisplay = `<span style="color:${color}">${expiry.toLocaleDateString('vi-VN')}</span><br><small style="color:var(--text-muted)">(còn ${daysLeft} ngày)</small>`;
                } else {
                    vipExpiryDisplay = `<span style="color:var(--danger)">⚠️ Hết hạn</span>`;
                    isExpired = true;
                }
            } else {
                vipExpiryDisplay = '<span style="color:var(--warning)">⭐ Vĩnh viễn</span>';
            }
            
            html += `<tr style="${isExpired ? 'background:rgba(239,68,68,0.1)' : ''}">
                <td><code>${user.telegram_id}</code></td>
                <td>${user.username ? '@' + user.username : '-'}</td>
                <td>${user.first_name || ''} ${user.last_name || ''}</td>
                <td style="color:var(--warning)"><strong>${user.coins || 0}</strong></td>
                <td style="color:var(--success)"><strong>${user.cash || 0}</strong></td>
                <td>${vipExpiryDisplay}</td>
                <td>
                    <div style="display:flex;gap:4px">
                        <button class="btn btn-sm btn-primary" onclick="closeVipModal(); viewUser(${user.telegram_id})" title="Xem chi tiết"><i class="fas fa-eye"></i></button>
                        <button class="btn btn-sm btn-danger" onclick="removeVip(${user.telegram_id})" title="Hủy VIP"><i class="fas fa-times"></i></button>
                    </div>
                </td>
            </tr>`;
        });
        
        html += '</tbody></table>';
        document.getElementById('vipUsersContent').innerHTML = html;
    } catch (error) {
        document.getElementById('vipUsersContent').innerHTML = `<p style="color:var(--danger);text-align:center;padding:40px">Lỗi: ${error.message}</p>`;
    }
}

// Remove VIP status
async function removeVip(telegramId) {
    if (!confirm('Bạn có chắc muốn hủy VIP của user này?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/admin/users/${telegramId}/set-vip`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_vip: false, days: 0 })
        });
        const data = await response.json();
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể cập nhật'));
            return;
        }
        alert('✅ Đã hủy VIP!');
        showVipUsers(); // Reload list
        loadStats(); // Update stats
    } catch (error) { alert('Lỗi: ' + error.message); }
}

function closeVipModal() {
    document.getElementById('vipModal').classList.remove('active');
}

// Cleanup all expired VIPs
async function cleanupExpiredVips() {
    if (!confirm('Bạn có chắc muốn hủy VIP của TẤT CẢ users đã hết hạn?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/admin/cleanup-expired-vips`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể dọn dẹp'));
            return;
        }
        alert(`✅ Đã hủy VIP của ${data.count || 0} users hết hạn!`);
        showVipUsers(); // Reload list
        loadStats(); // Update stats
    } catch (error) { alert('Lỗi: ' + error.message); }
}

// Show Blocked Users Modal
async function showBlockedUsers() {
    document.getElementById('blockedModal').classList.add('active');
    document.getElementById('blockedUsersContent').innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Đang tải...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/admin/users?filter=blocked&limit=100`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await response.json();
        const users = data.users || data || [];
        
        if (users.length === 0) {
            document.getElementById('blockedUsersContent').innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:40px">Không có tài khoản bị khóa nào</p>';
            return;
        }
        
        let html = `<div style="margin-bottom:16px;color:var(--text-muted)">Tổng: <strong style="color:var(--danger)">${users.length}</strong> tài khoản bị khóa</div>`;
        html += `<table>
            <thead><tr>
                <th>ID</th><th>Username</th><th>Tên</th><th>Coins</th><th>Cash</th><th>Ngày tạo</th><th>Actions</th>
            </tr></thead>
            <tbody>`;
        
        users.forEach(user => {
            html += `<tr>
                <td><code>${user.telegram_id}</code></td>
                <td>${user.username ? '@' + user.username : '-'}</td>
                <td>${user.first_name || ''} ${user.last_name || ''}</td>
                <td style="color:var(--warning)"><strong>${user.coins || 0}</strong></td>
                <td style="color:var(--success)"><strong>${user.cash || 0}</strong></td>
                <td>${user.created_at ? new Date(user.created_at).toLocaleDateString('vi-VN') : '-'}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="closeBlockedModal(); viewUser(${user.telegram_id})"><i class="fas fa-eye"></i></button>
                    <button class="btn btn-sm btn-success" onclick="unblockUser(${user.telegram_id})" title="Mở khóa"><i class="fas fa-unlock"></i></button>
                </td>
            </tr>`;
        });
        
        html += '</tbody></table>';
        document.getElementById('blockedUsersContent').innerHTML = html;
    } catch (error) {
        document.getElementById('blockedUsersContent').innerHTML = `<p style="color:var(--danger);text-align:center;padding:40px">Lỗi: ${error.message}</p>`;
    }
}

// Unblock user
async function unblockUser(telegramId) {
    if (!confirm('Bạn có chắc muốn mở khóa tài khoản này?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/admin/users/${telegramId}/block`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ blocked: false, reason: '' })
        });
        const data = await response.json();
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể cập nhật'));
            return;
        }
        alert('🔓 Đã mở khóa tài khoản!');
        showBlockedUsers(); // Reload list
        loadStats(); // Update stats
    } catch (error) { alert('Lỗi: ' + error.message); }
}

function closeBlockedModal() {
    document.getElementById('blockedModal').classList.remove('active');
}


// ==================== BROADCAST FUNCTIONS ====================

async function sendBroadcast() {
    const message = document.getElementById('broadcastMessage').value.trim();
    const statusEl = document.getElementById('broadcastStatus');
    const resultEl = document.getElementById('broadcastResult');
    const btn = document.getElementById('broadcastBtn');
    
    if (!message) {
        statusEl.innerHTML = '<span style="color:var(--danger)">❌ Vui lòng nhập nội dung tin nhắn</span>';
        return;
    }
    
    if (!confirm(`Bạn có chắc muốn gửi tin nhắn này đến TẤT CẢ users?\n\n"${message.substring(0, 100)}${message.length > 100 ? '...' : ''}"`)) {
        return;
    }
    
    // Disable button and show loading
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang gửi...';
    statusEl.innerHTML = '<span style="color:var(--primary)"><i class="fas fa-spinner fa-spin"></i> Đang gửi broadcast đến tất cả users, vui lòng đợi (có thể mất 1-2 phút)...</span>';
    resultEl.style.display = 'block';
    resultEl.innerHTML = '<div style="text-align:center;padding:20px"><i class="fas fa-paper-plane fa-3x" style="color:var(--primary);animation:pulse 1s infinite"></i><p style="margin-top:15px;color:var(--text-muted)">Đang gửi tin nhắn đến từng user...<br><small>Quá trình này có thể mất vài phút tùy số lượng users</small></p></div>';
    
    try {
        const response = await fetch(`${API_BASE}/admin/broadcast`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${authToken}`, 
                'Content-Type': 'application/json' 
            },
            body: JSON.stringify({ message })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            statusEl.innerHTML = `<span style="color:var(--danger)">❌ ${data.error || 'Lỗi gửi broadcast'}</span>`;
            resultEl.style.display = 'none';
            return;
        }
        
        // Show success result
        statusEl.innerHTML = '<span style="color:var(--success)">✅ Hoàn thành!</span>';
        
        const successRate = data.total > 0 ? Math.round((data.sent / data.total) * 100) : 0;
        let resultHtml = `
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:15px;text-align:center">
                <div style="padding:15px;background:var(--darker);border-radius:8px">
                    <div style="font-size:24px;font-weight:700;color:var(--primary)">${data.total}</div>
                    <div style="font-size:12px;color:var(--text-muted)">Tổng users</div>
                </div>
                <div style="padding:15px;background:var(--darker);border-radius:8px">
                    <div style="font-size:24px;font-weight:700;color:var(--success)">${data.sent}</div>
                    <div style="font-size:12px;color:var(--text-muted)">Gửi thành công</div>
                </div>
                <div style="padding:15px;background:var(--darker);border-radius:8px">
                    <div style="font-size:24px;font-weight:700;color:var(--danger)">${data.failed}</div>
                    <div style="font-size:12px;color:var(--text-muted)">Thất bại</div>
                </div>
            </div>
            <div style="margin-top:15px;text-align:center">
                <span style="font-size:14px;color:var(--text-muted)">Tỷ lệ thành công: </span>
                <span style="font-size:16px;font-weight:600;color:${successRate >= 90 ? 'var(--success)' : successRate >= 70 ? 'var(--warning)' : 'var(--danger)'}">${successRate}%</span>
            </div>
        `;
        
        if (data.failed > 0 && data.failed_users && data.failed_users.length > 0) {
            resultHtml += `
                <div style="margin-top:15px;padding:10px;background:rgba(239,68,68,0.1);border-radius:6px;font-size:12px">
                    <strong style="color:var(--danger)">Users thất bại:</strong> 
                    <span style="color:var(--text-muted)">${data.failed_users.join(', ')}${data.failed > 10 ? '...' : ''}</span>
                </div>
            `;
        }
        
        resultEl.innerHTML = resultHtml;
        resultEl.style.display = 'block';
        
        // Clear message input
        document.getElementById('broadcastMessage').value = '';
        
    } catch (error) {
        statusEl.innerHTML = `<span style="color:var(--danger)">❌ Lỗi kết nối: ${error.message}</span>`;
        resultEl.style.display = 'none';
    } finally {
        // Re-enable button
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-paper-plane"></i> Gửi Broadcast';
    }
}


// ==================== SELLER MANAGEMENT FUNCTIONS ====================

let allSellers = [];
let allSellerJobs = [];

// Load sellers data
async function loadSellers() {
    try {
        const response = await fetch(`${API_BASE}/admin/sellers`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await response.json();
        
        if (!response.ok) {
            document.getElementById('sellersContent').innerHTML = `<p style="color:var(--danger);text-align:center;padding:40px">Lỗi: ${data.error || 'Không thể tải dữ liệu'}</p>`;
            return;
        }
        
        allSellers = data.sellers || [];
        
        // Update stats
        const activeSellers = allSellers.filter(s => s.is_active);
        const totalCredits = allSellers.reduce((sum, s) => sum + (s.credits || 0), 0);
        const totalUsed = allSellers.reduce((sum, s) => sum + (s.total_used || 0), 0);
        
        document.getElementById('totalSellers').textContent = allSellers.length;
        document.getElementById('activeSellers').textContent = activeSellers.length;
        document.getElementById('totalSellerCredits').textContent = formatNumber(totalCredits);
        document.getElementById('totalSellerUsed').textContent = formatNumber(totalUsed);
        
        renderSellersTable(allSellers);
        loadSellerJobs();
    } catch (error) {
        document.getElementById('sellersContent').innerHTML = `<p style="color:var(--danger);text-align:center;padding:40px">Lỗi: ${error.message}</p>`;
    }
}

// Render sellers table
function renderSellersTable(sellers) {
    if (sellers.length === 0) {
        document.getElementById('sellersContent').innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:40px">Chưa có seller nào</p>';
        return;
    }
    
    let html = `<table>
        <thead><tr>
            <th>ID</th>
            <th>Tên</th>
            <th>Email</th>
            <th>API Key</th>
            <th>Credits</th>
            <th>Đã dùng</th>
            <th>Tỉ giá (VND/credit)</th>
            <th>Trạng thái</th>
            <th>Actions</th>
        </tr></thead>
        <tbody>`;
    
    sellers.forEach(seller => {
        const statusBadge = seller.is_active 
            ? '<span class="badge badge-success"><i class="fas fa-check"></i> Active</span>'
            : '<span class="badge badge-danger"><i class="fas fa-times"></i> Inactive</span>';
        
        const apiKeyShort = seller.api_key ? seller.api_key.substring(0, 12) + '...' : '-';
        
        html += `<tr>
            <td><code>${seller.id}</code></td>
            <td><strong>${seller.name || '-'}</strong></td>
            <td>${seller.email || '-'}</td>
            <td>
                <code style="font-size:11px">${apiKeyShort}</code>
                <button class="btn btn-sm btn-ghost" onclick="copyApiKey('${seller.api_key}')" title="Copy API Key">
                    <i class="fas fa-copy"></i>
                </button>
            </td>
            <td style="color:var(--warning)"><strong>${formatNumber(seller.credits || 0)}</strong></td>
            <td style="color:var(--success)">${formatNumber(seller.total_used || 0)}</td>
            <td>
                <div style="display:flex;align-items:center;gap:4px">
                    <input type="number" id="rate_${seller.id}" value="${seller.exchange_rate || 1000}" 
                        style="width:80px;padding:4px;border:1px solid var(--border);border-radius:4px;background:var(--bg-secondary);color:var(--text-primary)" min="1">
                    <button class="btn btn-sm btn-success" onclick="updateSellerRate(${seller.id})" title="Lưu tỉ giá">
                        <i class="fas fa-save"></i>
                    </button>
                </div>
            </td>
            <td>${statusBadge}</td>
            <td>
                <div style="display:flex;gap:4px">
                    <button class="btn btn-sm btn-primary" onclick="viewSellerDetail(${seller.id})" title="Chi tiết">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-warning" onclick="showAddCreditsModal(${seller.id}, '${seller.name}')" title="Thêm credits">
                        <i class="fas fa-coins"></i>
                    </button>
                    <button class="btn btn-sm ${seller.is_active ? 'btn-danger' : 'btn-success'}" onclick="toggleSellerStatus(${seller.id}, ${!seller.is_active})" title="${seller.is_active ? 'Tắt' : 'Bật'}">
                        <i class="fas fa-${seller.is_active ? 'ban' : 'check'}"></i>
                    </button>
                </div>
            </td>
        </tr>`;
    });
    
    html += '</tbody></table>';
    document.getElementById('sellersContent').innerHTML = html;
}

// Load seller jobs
async function loadSellerJobs() {
    try {
        const response = await fetch(`${API_BASE}/admin/seller-jobs?limit=50`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await response.json();
        
        if (!response.ok) {
            document.getElementById('sellerJobsContent').innerHTML = `<p style="color:var(--danger);text-align:center;padding:20px">Lỗi: ${data.error || 'Không thể tải'}</p>`;
            return;
        }
        
        allSellerJobs = data.jobs || [];
        renderSellerJobsTable(allSellerJobs);
    } catch (error) {
        document.getElementById('sellerJobsContent').innerHTML = `<p style="color:var(--danger);text-align:center;padding:20px">Lỗi: ${error.message}</p>`;
    }
}

// Render seller jobs table
function renderSellerJobsTable(jobs) {
    if (jobs.length === 0) {
        document.getElementById('sellerJobsContent').innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:40px">Chưa có job nào</p>';
        return;
    }
    
    let html = `<table>
        <thead><tr>
            <th>Job ID</th>
            <th>Seller</th>
            <th>Status</th>
            <th>SheerID URL</th>
            <th>Thời gian</th>
        </tr></thead>
        <tbody>`;
    
    jobs.forEach(job => {
        let statusBadge = '';
        switch(job.status) {
            case 'completed':
            case 'success':
                statusBadge = '<span class="badge badge-success"><i class="fas fa-check"></i> Completed</span>';
                break;
            case 'failed':
                statusBadge = '<span class="badge badge-danger"><i class="fas fa-times"></i> Failed</span>';
                break;
            case 'processing':
                statusBadge = '<span class="badge badge-primary"><i class="fas fa-spinner fa-spin"></i> Processing</span>';
                break;
            default:
                statusBadge = '<span class="badge badge-warning"><i class="fas fa-clock"></i> Pending</span>';
        }
        
        const sellerName = allSellers.find(s => s.id === job.seller_id)?.name || `Seller #${job.seller_id}`;
        const urlShort = job.sheerid_url ? job.sheerid_url.substring(0, 40) + '...' : '-';
        const createdAt = job.created_at ? new Date(job.created_at).toLocaleString('vi-VN') : '-';
        
        html += `<tr>
            <td><code style="font-size:11px">${job.job_id?.substring(0, 16) || '-'}...</code></td>
            <td>${sellerName}</td>
            <td>${statusBadge}</td>
            <td><small style="color:var(--text-muted)">${urlShort}</small></td>
            <td><small>${createdAt}</small></td>
        </tr>`;
    });
    
    html += '</tbody></table>';
    document.getElementById('sellerJobsContent').innerHTML = html;
}

// Search seller jobs
function searchSellerJobs() {
    const query = document.getElementById('sellerJobSearch').value.toLowerCase();
    const filtered = allSellerJobs.filter(job => 
        (job.job_id && job.job_id.toLowerCase().includes(query)) ||
        (job.sheerid_url && job.sheerid_url.toLowerCase().includes(query))
    );
    renderSellerJobsTable(filtered);
}

// Copy API key to clipboard
function copyApiKey(apiKey) {
    navigator.clipboard.writeText(apiKey).then(() => {
        alert('✅ Đã copy API Key!');
    }).catch(err => {
        prompt('Copy API Key:', apiKey);
    });
}

// Show add seller modal
function showAddSellerModal() {
    document.getElementById('addSellerModal').classList.add('active');
    document.getElementById('newSellerName').value = '';
    document.getElementById('newSellerEmail').value = '';
    document.getElementById('newSellerCredits').value = '0';
    document.getElementById('newSellerWebhook').value = '';
    document.getElementById('addSellerResult').style.display = 'none';
}

function closeAddSellerModal() {
    document.getElementById('addSellerModal').classList.remove('active');
    // Reset form
    document.getElementById('newSellerName').value = '';
    document.getElementById('newSellerTelegramId').value = '';
    document.getElementById('newSellerEmail').value = '';
    document.getElementById('newSellerCredits').value = '0';
    document.getElementById('newSellerExchangeRate').value = '1000';
    document.getElementById('newSellerWebhook').value = '';
    document.getElementById('addSellerResult').style.display = 'none';
}

// Create new seller
async function createSeller() {
    const name = document.getElementById('newSellerName').value.trim();
    const telegram_id = document.getElementById('newSellerTelegramId').value.trim();
    const email = document.getElementById('newSellerEmail').value.trim();
    const credits = parseInt(document.getElementById('newSellerCredits').value) || 0;
    const exchange_rate = parseInt(document.getElementById('newSellerExchangeRate').value) || 1000;
    const webhook_url = document.getElementById('newSellerWebhook').value.trim();
    
    if (!name) {
        alert('Vui lòng nhập tên seller!');
        return;
    }
    
    if (exchange_rate < 1) {
        alert('Tỉ giá phải >= 1');
        return;
    }
    
    try {
        const payload = { name, email, credits, exchange_rate, webhook_url };
        if (telegram_id) {
            payload.telegram_id = parseInt(telegram_id);
        }
        
        const response = await fetch(`${API_BASE}/admin/sellers`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể tạo seller'));
            return;
        }
        
        // Show API key with proper styling
        const resultEl = document.getElementById('addSellerResult');
        resultEl.style.display = 'block';
        resultEl.innerHTML = `
            <div style="padding:15px;background:rgba(16,185,129,0.1);border:1px solid var(--success);border-radius:8px">
                <p style="color:var(--success);font-weight:600;margin-bottom:10px">✅ Tạo seller thành công!</p>
                <p style="margin-bottom:8px"><strong>API Key:</strong></p>
                <div style="display:flex;gap:8px;align-items:stretch">
                    <div style="flex:1;padding:10px;background:var(--darker);border-radius:6px;font-family:monospace;font-size:12px;overflow-x:auto;white-space:nowrap;border:1px solid var(--border)">${data.seller.api_key}</div>
                    <button class="btn btn-primary" style="padding:10px 14px" onclick="copyApiKey('${data.seller.api_key}')">
                        <i class="fas fa-copy"></i>
                    </button>
                </div>
                <p style="margin-top:10px;font-size:12px;color:var(--warning)">⚠️ Lưu API Key này! Bạn sẽ không thể xem lại sau.</p>
            </div>
        `;
        
        loadSellers(); // Reload list
    } catch (error) {
        alert('Lỗi: ' + error.message);
    }
}

// View seller detail
async function viewSellerDetail(sellerId) {
    document.getElementById('sellerDetailModal').classList.add('active');
    document.getElementById('sellerDetailContent').innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Đang tải...</div>';
    
    const seller = allSellers.find(s => s.id === sellerId);
    if (!seller) {
        document.getElementById('sellerDetailContent').innerHTML = '<p style="color:var(--danger)">Không tìm thấy seller</p>';
        return;
    }
    
    const statusBadge = seller.is_active 
        ? '<span class="badge badge-success"><i class="fas fa-check"></i> Active</span>'
        : '<span class="badge badge-danger"><i class="fas fa-times"></i> Inactive</span>';
    
    let html = `
        <div class="user-detail-grid">
            <div class="detail-item">
                <label>ID</label>
                <span>${seller.id}</span>
            </div>
            <div class="detail-item">
                <label>Tên</label>
                <span>${seller.name || '-'}</span>
            </div>
            <div class="detail-item">
                <label>Telegram ID</label>
                <span>${seller.telegram_id || '<em style="color:var(--text-muted)">Chưa liên kết</em>'}</span>
            </div>
            <div class="detail-item">
                <label>Email</label>
                <span>${seller.email || '-'}</span>
            </div>
            <div class="detail-item">
                <label>Trạng thái</label>
                <span>${statusBadge}</span>
            </div>
        </div>
        
        <div class="mini-stats">
            <div class="mini-stat">
                <div class="value" style="color:var(--warning)">${formatNumber(seller.credits || 0)}</div>
                <div class="label">Credits còn lại</div>
            </div>
            <div class="mini-stat">
                <div class="value" style="color:var(--success)">${formatNumber(seller.total_used || 0)}</div>
                <div class="label">Đã sử dụng</div>
            </div>
            <div class="mini-stat">
                <div class="value" style="color:var(--primary)">${seller.rate_limit || 10}</div>
                <div class="label">Rate limit/phút</div>
            </div>
        </div>
        
        <div class="detail-item" style="margin-bottom:16px">
            <label>API KEY</label>
            <div class="api-key-container" style="display:flex;gap:8px;align-items:stretch;margin-top:8px">
                <div class="api-key-box" style="flex:1;padding:12px;background:var(--darker);border-radius:6px;font-family:monospace;font-size:13px;overflow-x:auto;white-space:nowrap;border:1px solid var(--border)">${seller.api_key}</div>
                <button class="btn btn-primary" style="padding:12px 16px" onclick="copyApiKey('${seller.api_key}')">
                    <i class="fas fa-copy"></i>
                </button>
            </div>
        </div>
        
        <div class="detail-item" style="margin-bottom:16px">
            <label>Webhook URL</label>
            <span>${seller.webhook_url || '<em style="color:var(--text-muted)">Chưa cấu hình</em>'}</span>
        </div>
        
        <div class="detail-item">
            <label>Ngày tạo</label>
            <span>${seller.created_at ? new Date(seller.created_at).toLocaleString('vi-VN') : '-'}</span>
        </div>
        
        <div class="action-buttons" style="margin-top:20px">
            <button class="btn btn-warning" onclick="showAddCreditsModal(${seller.id}, '${seller.name}')">
                <i class="fas fa-coins"></i> Thêm Credits
            </button>
            <button class="btn ${seller.is_active ? 'btn-danger' : 'btn-success'}" onclick="toggleSellerStatus(${seller.id}, ${!seller.is_active}); closeSellerDetailModal();">
                <i class="fas fa-${seller.is_active ? 'ban' : 'check'}"></i> ${seller.is_active ? 'Tắt Seller' : 'Bật Seller'}
            </button>
            <button class="btn btn-danger" onclick="deleteSeller(${seller.id})">
                <i class="fas fa-trash"></i> Xóa Seller
            </button>
        </div>
    `;
    
    document.getElementById('sellerDetailContent').innerHTML = html;
}

function closeSellerDetailModal() {
    document.getElementById('sellerDetailModal').classList.remove('active');
}

// Show add credits modal
function showAddCreditsModal(sellerId, sellerName) {
    document.getElementById('addCreditsModal').classList.add('active');
    document.getElementById('addCreditSellerName').textContent = sellerName;
    document.getElementById('addCreditSellerId').value = sellerId;
    document.getElementById('addCreditsAmount').value = '';
}

function closeAddCreditsModal() {
    document.getElementById('addCreditsModal').classList.remove('active');
}

// Add credits to seller
async function addCreditsToSeller() {
    const sellerId = document.getElementById('addCreditSellerId').value;
    const credits = parseInt(document.getElementById('addCreditsAmount').value);
    
    if (!credits || credits < 1) {
        alert('Vui lòng nhập số credits hợp lệ!');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/admin/sellers/${sellerId}/credits`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ credits })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể thêm credits'));
            return;
        }
        
        alert(`✅ Đã thêm ${credits} credits! Số dư mới: ${data.new_balance}`);
        closeAddCreditsModal();
        loadSellers(); // Reload
    } catch (error) {
        alert('Lỗi: ' + error.message);
    }
}

// Update seller exchange rate
async function updateSellerRate(sellerId) {
    const rateInput = document.getElementById(`rate_${sellerId}`);
    const newRate = parseInt(rateInput.value);
    
    if (!newRate || newRate < 1) {
        alert('Tỉ giá phải >= 1');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/admin/sellers/${sellerId}/exchange-rate`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ exchange_rate: newRate })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể cập nhật'));
            return;
        }
        
        alert(`✅ Đã cập nhật tỉ giá: ${formatNumber(newRate)} VND/credit`);
    } catch (error) {
        alert('Lỗi: ' + error.message);
    }
}

// Toggle seller status
async function toggleSellerStatus(sellerId, isActive) {
    const action = isActive ? 'bật' : 'tắt';
    if (!confirm(`Bạn có chắc muốn ${action} seller này?`)) return;
    
    try {
        const response = await fetch(`${API_BASE}/admin/sellers/${sellerId}/toggle`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ is_active: isActive })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể cập nhật'));
            return;
        }
        
        alert(`✅ Đã ${action} seller!`);
        loadSellers(); // Reload
    } catch (error) {
        alert('Lỗi: ' + error.message);
    }
}

// Delete seller
async function deleteSeller(sellerId) {
    if (!confirm('⚠️ Bạn có chắc muốn XÓA seller này? Hành động này không thể hoàn tác!')) return;
    if (!confirm('Xác nhận lần cuối: XÓA seller?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/admin/sellers/${sellerId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            alert('Lỗi: ' + (data.error || 'Không thể xóa'));
            return;
        }
        
        alert('✅ Đã xóa seller!');
        closeSellerDetailModal();
        loadSellers(); // Reload
    } catch (error) {
        alert('Lỗi: ' + error.message);
    }
}

// Helper function to format numbers
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}



// ==================== PROXY FUNCTIONS ====================

// Load proxy status
async function loadProxyStatus() {
    try {
        const response = await fetch(`${API_BASE}/admin/proxy/status`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            document.getElementById('proxyStatus').textContent = data.status || 'Active';
            document.getElementById('proxyStatus').style.color = data.status === 'Active' ? 'var(--success)' : 'var(--danger)';
            document.getElementById('proxyIP').textContent = data.ip || '-';
            document.getElementById('proxyLatency').textContent = data.latency ? data.latency + 'ms' : '-';
            if (data.host) document.getElementById('proxyHost').textContent = data.host;
            if (data.port) document.getElementById('proxyPort').textContent = data.port;
            if (data.user) document.getElementById('proxyUser').textContent = data.user;
        }
    } catch (error) {
        console.error('Error loading proxy status:', error);
    }
}

// Test proxy connection
async function testProxyConnection() {
    const logEl = document.getElementById('proxyTestLog');
    const statusEl = document.getElementById('proxyStatus');
    const ipEl = document.getElementById('proxyIP');
    const latencyEl = document.getElementById('proxyLatency');
    
    logEl.innerHTML = '<div style="color:var(--warning)">🔄 Đang test proxy connection...</div>';
    statusEl.textContent = 'Testing...';
    statusEl.style.color = 'var(--warning)';
    
    const startTime = Date.now();
    
    try {
        const response = await fetch(`${API_BASE}/admin/proxy/test`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        const latency = Date.now() - startTime;
        
        if (data.success) {
            statusEl.textContent = '✅ Active';
            statusEl.style.color = 'var(--success)';
            ipEl.textContent = data.ip || 'Unknown';
            latencyEl.textContent = latency + 'ms';
            
            logEl.innerHTML = `
                <div style="color:var(--success)">✅ [${new Date().toLocaleTimeString()}] Proxy connection successful!</div>
                <div style="color:var(--text)">📍 IP: ${data.ip}</div>
                <div style="color:var(--text)">🌍 Location: ${data.location || 'Unknown'}</div>
                <div style="color:var(--text)">⏱️ Latency: ${latency}ms</div>
                <div style="color:var(--text-muted);margin-top:8px">Protocol: SOCKS5 | Rotation: Per Request</div>
            `;
        } else {
            statusEl.textContent = '❌ Failed';
            statusEl.style.color = 'var(--danger)';
            logEl.innerHTML = `<div style="color:var(--danger)">❌ [${new Date().toLocaleTimeString()}] Proxy test failed: ${data.error || 'Unknown error'}</div>`;
        }
    } catch (error) {
        statusEl.textContent = '❌ Error';
        statusEl.style.color = 'var(--danger)';
        logEl.innerHTML = `<div style="color:var(--danger)">❌ [${new Date().toLocaleTimeString()}] Error: ${error.message}</div>`;
    }
}

// Test proxy with SheerID link
async function testSheeridProxy() {
    const linkInput = document.getElementById('testSheeridLink');
    const resultEl = document.getElementById('sheeridTestResult');
    const logEl = document.getElementById('proxyTestLog');
    const link = linkInput.value.trim();
    
    if (!link) {
        alert('Vui lòng nhập SheerID link để test');
        return;
    }
    
    // Validate SheerID link format
    if (!link.includes('sheerid.com') && !link.includes('verificationId=')) {
        alert('Link không hợp lệ. Vui lòng nhập link SheerID đúng định dạng.');
        return;
    }
    
    resultEl.style.display = 'block';
    resultEl.style.background = 'rgba(245,158,11,0.1)';
    resultEl.style.border = '1px solid var(--warning)';
    resultEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang test với SheerID...';
    
    const startTime = Date.now();
    
    try {
        const response = await fetch(`${API_BASE}/admin/proxy/test-sheerid`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: link })
        });
        
        const data = await response.json();
        const latency = Date.now() - startTime;
        
        if (data.success) {
            resultEl.style.background = 'rgba(16,185,129,0.1)';
            resultEl.style.border = '1px solid var(--success)';
            resultEl.innerHTML = `
                <div style="color:var(--success);font-weight:600;margin-bottom:8px">✅ Test thành công!</div>
                <div style="font-size:13px">
                    <div>📍 Proxy IP: <strong>${data.proxy_ip || 'Unknown'}</strong></div>
                    <div>🔗 Verification ID: <code>${data.verification_id || 'N/A'}</code></div>
                    <div>📊 Status: ${data.current_step || 'Unknown'}</div>
                    <div>⏱️ Response time: ${latency}ms</div>
                </div>
            `;
            
            // Add to log
            const logEntry = `<div style="color:var(--success);margin-top:8px">✅ [${new Date().toLocaleTimeString()}] SheerID test successful - IP: ${data.proxy_ip}, Step: ${data.current_step}</div>`;
            logEl.innerHTML = logEntry + logEl.innerHTML;
        } else {
            resultEl.style.background = 'rgba(239,68,68,0.1)';
            resultEl.style.border = '1px solid var(--danger)';
            resultEl.innerHTML = `
                <div style="color:var(--danger);font-weight:600;margin-bottom:8px">❌ Test thất bại</div>
                <div style="font-size:13px">
                    <div>Lỗi: ${data.error || 'Unknown error'}</div>
                    <div>⏱️ Response time: ${latency}ms</div>
                </div>
            `;
            
            const logEntry = `<div style="color:var(--danger);margin-top:8px">❌ [${new Date().toLocaleTimeString()}] SheerID test failed: ${data.error}</div>`;
            logEl.innerHTML = logEntry + logEl.innerHTML;
        }
    } catch (error) {
        resultEl.style.background = 'rgba(239,68,68,0.1)';
        resultEl.style.border = '1px solid var(--danger)';
        resultEl.innerHTML = `<div style="color:var(--danger)">❌ Error: ${error.message}</div>`;
        
        const logEntry = `<div style="color:var(--danger);margin-top:8px">❌ [${new Date().toLocaleTimeString()}] Error: ${error.message}</div>`;
        logEl.innerHTML = logEntry + logEl.innerHTML;
    }
}


// Save proxy settings
async function saveProxySettings() {
    const settings = {
        enabled: document.getElementById('proxyEnabled').checked,
        autoHealthChecks: document.getElementById('proxyAutoHealth').checked,
        checkInterval: parseInt(document.getElementById('proxyCheckInterval').value) || 120,
        usageLimit: parseInt(document.getElementById('proxyUsageLimit').value) || 50,
        cooldownPeriod: parseInt(document.getElementById('proxyCooldown').value) || 30,
        fallbackRetryLimit: parseInt(document.getElementById('proxyFallbackRetry').value) || 3,
        concurrentChecks: parseInt(document.getElementById('proxyConcurrent').value) || 200,
        testTimeout: parseInt(document.getElementById('proxyTestTimeout').value) || 15,
        maxRetries: parseInt(document.getElementById('proxyMaxRetries').value) || 3,
        retryDelay: parseInt(document.getElementById('proxyRetryDelay').value) || 1
    };
    
    try {
        const response = await fetch(`${API_BASE}/admin/proxy/settings`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('✅ Đã lưu cài đặt Proxy!');
            // Add to log
            const logEl = document.getElementById('proxyTestLog');
            const logEntry = `<div style="color:var(--success);margin-top:8px">✅ [${new Date().toLocaleTimeString()}] Settings saved successfully</div>`;
            logEl.innerHTML = logEntry + logEl.innerHTML;
        } else {
            alert('❌ Lỗi: ' + (data.error || 'Không thể lưu cài đặt'));
        }
    } catch (error) {
        alert('❌ Lỗi: ' + error.message);
    }
}

// Load proxy settings on tab switch
async function loadProxySettings() {
    try {
        const response = await fetch(`${API_BASE}/admin/proxy/settings`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.settings) {
                document.getElementById('proxyEnabled').checked = data.settings.enabled !== false;
                document.getElementById('proxyAutoHealth').checked = data.settings.autoHealthChecks !== false;
                document.getElementById('proxyCheckInterval').value = data.settings.checkInterval || 120;
                document.getElementById('proxyUsageLimit').value = data.settings.usageLimit || 50;
                document.getElementById('proxyCooldown').value = data.settings.cooldownPeriod || 30;
                document.getElementById('proxyFallbackRetry').value = data.settings.fallbackRetryLimit || 3;
                document.getElementById('proxyConcurrent').value = data.settings.concurrentChecks || 200;
                document.getElementById('proxyTestTimeout').value = data.settings.testTimeout || 15;
                document.getElementById('proxyMaxRetries').value = data.settings.maxRetries || 3;
                document.getElementById('proxyRetryDelay').value = data.settings.retryDelay || 1;
            }
        }
    } catch (error) {
        console.error('Error loading proxy settings:', error);
    }
}

// Update loadProxyStatus to also load settings
const originalLoadProxyStatus = loadProxyStatus;
loadProxyStatus = async function() {
    await loadProxySettings();
    await originalLoadProxyStatus();
};

// ============================================
// FRAUD TRACKING FUNCTIONS
// ============================================

// Load University Fraud data
async function loadUniversityFraud() {
    try {
        const response = await fetch(`${API_BASE}/admin/university-fraud`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            displayUniversityFraud(data.universities || []);
            document.getElementById('totalUniFraud').textContent = data.total || 0;
            document.getElementById('blockedUniCount').textContent = data.blocked_count || 0;
        } else {
            document.getElementById('universityFraudContent').innerHTML = '<p style="color:var(--danger)">Lỗi tải dữ liệu</p>';
        }
    } catch (error) {
        console.error('Error loading university fraud:', error);
        document.getElementById('universityFraudContent').innerHTML = '<p style="color:var(--danger)">Lỗi: ' + error.message + '</p>';
    }
}

function displayUniversityFraud(universities) {
    if (!universities || universities.length === 0) {
        document.getElementById('universityFraudContent').innerHTML = '<p style="text-align:center;color:var(--text-muted)">Chưa có dữ liệu fraud</p>';
        return;
    }
    
    const html = `<table>
        <thead><tr>
            <th>University ID</th>
            <th>Tên trường</th>
            <th>Fraud liên tiếp</th>
            <th>Tổng Fraud</th>
            <th>Trạng thái</th>
            <th>Lần cuối</th>
            <th>Actions</th>
        </tr></thead>
        <tbody>${universities.map(u => `<tr>
            <td><code style="font-size:11px">${u.university_id}</code></td>
            <td>${u.university_name || '-'}</td>
            <td style="text-align:center"><strong style="color:${u.consecutive_fraud_count >= 3 ? 'var(--danger)' : 'var(--warning)'}">${u.consecutive_fraud_count || 0}</strong></td>
            <td style="text-align:center">${u.total_fraud_count || 0}</td>
            <td>${u.is_blocked ? '<span class="badge badge-danger"><i class="fas fa-ban"></i> Blocked</span>' : '<span class="badge badge-success"><i class="fas fa-check"></i> Active</span>'}</td>
            <td style="font-size:11px">${u.last_fraud_at ? new Date(u.last_fraud_at).toLocaleString('vi-VN') : '-'}</td>
            <td style="display:flex;gap:4px">
                ${u.is_blocked ? `<button class="btn btn-sm btn-success" onclick="unblockUniversity('${u.university_id}')" title="Unblock"><i class="fas fa-unlock"></i></button>` : ''}
                <button class="btn btn-sm btn-warning" onclick="resetUniversityFraud('${u.university_id}')" title="Reset"><i class="fas fa-redo"></i></button>
            </td>
        </tr>`).join('')}</tbody>
    </table>`;
    
    document.getElementById('universityFraudContent').innerHTML = html;
}

async function unblockUniversity(universityId) {
    if (!confirm(`Unblock university ${universityId}?`)) return;
    
    try {
        const response = await fetch(`${API_BASE}/admin/university-fraud/${universityId}/unblock`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (response.ok) {
            alert('✅ Đã unblock university!');
            loadUniversityFraud();
        } else {
            alert('❌ Lỗi: ' + (data.error || 'Không thể unblock'));
        }
    } catch (error) {
        alert('❌ Lỗi: ' + error.message);
    }
}

async function resetUniversityFraud(universityId) {
    if (!confirm(`Reset fraud count cho university ${universityId}?`)) return;
    
    try {
        const response = await fetch(`${API_BASE}/admin/university-fraud/${universityId}/reset`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (response.ok) {
            alert('✅ Đã reset fraud count!');
            loadUniversityFraud();
        } else {
            alert('❌ Lỗi: ' + (data.error || 'Không thể reset'));
        }
    } catch (error) {
        alert('❌ Lỗi: ' + error.message);
    }
}

// Load Fraud IPs
async function loadFraudIPs() {
    try {
        const response = await fetch(`${API_BASE}/admin/fraud-ips`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            displayFraudIPs(data.ips || []);
            document.getElementById('totalFraudIPs').textContent = data.total || 0;
            document.getElementById('activeFraudIPs').textContent = data.active_count || 0;
        } else {
            document.getElementById('fraudIPsContent').innerHTML = '<p style="color:var(--danger)">Lỗi tải dữ liệu</p>';
        }
    } catch (error) {
        console.error('Error loading fraud IPs:', error);
        document.getElementById('fraudIPsContent').innerHTML = '<p style="color:var(--danger)">Lỗi: ' + error.message + '</p>';
    }
}

function displayFraudIPs(ips) {
    if (!ips || ips.length === 0) {
        document.getElementById('fraudIPsContent').innerHTML = '<p style="text-align:center;color:var(--text-muted)">Chưa có IP fraud nào</p>';
        return;
    }
    
    const now = new Date();
    
    const html = `<table>
        <thead><tr>
            <th>IP Address</th>
            <th>Fraud Count</th>
            <th>Cooldown Until</th>
            <th>Trạng thái</th>
            <th>Lần cuối</th>
            <th>Actions</th>
        </tr></thead>
        <tbody>${ips.map(ip => {
            const cooldownUntil = ip.cooldown_until ? new Date(ip.cooldown_until) : null;
            const isActive = cooldownUntil && cooldownUntil > now;
            return `<tr>
                <td><code style="font-size:12px">${ip.ip_address}</code></td>
                <td style="text-align:center"><strong style="color:var(--danger)">${ip.fraud_count || 1}</strong></td>
                <td style="font-size:11px">${cooldownUntil ? cooldownUntil.toLocaleString('vi-VN') : '-'}</td>
                <td>${isActive ? '<span class="badge badge-danger"><i class="fas fa-clock"></i> Cooldown</span>' : '<span class="badge badge-success"><i class="fas fa-check"></i> Expired</span>'}</td>
                <td style="font-size:11px">${ip.last_fraud_at ? new Date(ip.last_fraud_at).toLocaleString('vi-VN') : '-'}</td>
                <td><button class="btn btn-sm btn-danger" onclick="removeFraudIP('${ip.ip_address}')" title="Remove"><i class="fas fa-trash"></i></button></td>
            </tr>`;
        }).join('')}</tbody>
    </table>`;
    
    document.getElementById('fraudIPsContent').innerHTML = html;
}

async function removeFraudIP(ipAddress) {
    if (!confirm(`Xóa IP ${ipAddress} khỏi danh sách fraud?`)) return;
    
    try {
        const response = await fetch(`${API_BASE}/admin/fraud-ips/${encodeURIComponent(ipAddress)}/remove`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (response.ok) {
            alert('✅ Đã xóa IP!');
            loadFraudIPs();
        } else {
            alert('❌ Lỗi: ' + (data.error || 'Không thể xóa'));
        }
    } catch (error) {
        alert('❌ Lỗi: ' + error.message);
    }
}

async function clearExpiredFraudIPs() {
    if (!confirm('Xóa tất cả IP đã hết cooldown?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/admin/fraud-ips/clear-expired`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (response.ok) {
            alert(`✅ Đã xóa ${data.deleted_count || 0} IP hết hạn!`);
            loadFraudIPs();
        } else {
            alert('❌ Lỗi: ' + (data.error || 'Không thể xóa'));
        }
    } catch (error) {
        alert('❌ Lỗi: ' + error.message);
    }
}

// Load fraud data when switching to fraud tab
function loadFraudData() {
    loadUniversityFraud();
    loadFraudIPs();
}


// ============================================
// CONFIG MANAGEMENT FUNCTIONS
// ============================================

async function loadVerificationPrices() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/config/verification-prices`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await response.json();
        
        const grid = document.getElementById('priceConfigGrid');
        if (!grid) return;
        
        grid.innerHTML = '';
        
        const types = {
            'gemini': { name: 'Gemini', icon: 'fa-gem', color: '#6366f1' },
            'perplexity': { name: 'Perplexity', icon: 'fa-brain', color: '#8b5cf6' },
            'teacher': { name: 'Teacher', icon: 'fa-chalkboard-teacher', color: '#10b981' },
            'spotify': { name: 'Spotify', icon: 'fa-spotify', color: '#1db954' }
        };
        
        for (const [key, info] of Object.entries(types)) {
            grid.innerHTML += `
                <div class="stat-card">
                    <div class="stat-icon" style="background:${info.color}20;color:${info.color}">
                        <i class="fas ${info.icon}"></i>
                    </div>
                    <div class="stat-label">${info.name}</div>
                    <input type="number" id="price_${key}" value="${data.prices[key] || 0}" 
                           min="0" class="form-control" style="margin-top:10px;text-align:center;font-size:18px;font-weight:600">
                    <div style="text-align:center;margin-top:5px;color:var(--text-muted)">cash</div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading verification prices:', error);
        showNotification('Lỗi tải giá verify: ' + error.message, 'error');
    }
}

async function saveVerificationPrices() {
    try {
        const prices = {
            gemini: parseInt(document.getElementById('price_gemini').value),
            perplexity: parseInt(document.getElementById('price_perplexity').value),
            teacher: parseInt(document.getElementById('price_teacher').value),
            spotify: parseInt(document.getElementById('price_spotify').value)
        };
        
        const response = await fetch(`${API_BASE}/api/admin/config/verification-prices`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ prices })
        });
        
        if (response.ok) {
            showNotification('✅ Đã lưu giá verify thành công!', 'success');
        } else {
            const data = await response.json();
            showNotification('❌ Lỗi: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('Error saving verification prices:', error);
        showNotification('❌ Lỗi lưu giá: ' + error.message, 'error');
    }
}

async function loadShopProducts() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/config/shop-products`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await response.json();
        
        const table = document.getElementById('shopProductsTable');
        if (!table) return;
        
        table.innerHTML = '';
        
        for (const [id, product] of Object.entries(data.products)) {
            table.innerHTML += `
                <tr data-product-id="${id}">
                    <td><code>${id}</code></td>
                    <td><input type="text" value="${product.name}" data-field="name" class="form-control"></td>
                    <td><input type="number" value="${product.price}" data-field="price" class="form-control" min="0"></td>
                    <td><input type="number" value="${product.stock}" data-field="stock" class="form-control" min="0"></td>
                    <td>
                        <select data-field="enabled" class="form-control">
                            <option value="true" ${product.enabled ? 'selected' : ''}>Bật</option>
                            <option value="false" ${!product.enabled ? 'selected' : ''}>Tắt</option>
                        </select>
                    </td>
                    <td>
                        <button class="btn btn-danger btn-sm" onclick="deleteShopProduct('${id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error loading shop products:', error);
        showNotification('Lỗi tải sản phẩm: ' + error.message, 'error');
    }
}

function addNewShopProduct() {
    const table = document.getElementById('shopProductsTable');
    if (!table) return;
    
    const newId = 'product_' + Date.now();
    table.innerHTML += `
        <tr data-product-id="${newId}">
            <td><code>${newId}</code></td>
            <td><input type="text" value="Sản phẩm mới" data-field="name" class="form-control"></td>
            <td><input type="number" value="0" data-field="price" class="form-control" min="0"></td>
            <td><input type="number" value="0" data-field="stock" class="form-control" min="0"></td>
            <td>
                <select data-field="enabled" class="form-control">
                    <option value="true" selected>Bật</option>
                    <option value="false">Tắt</option>
                </select>
            </td>
            <td>
                <button class="btn btn-danger btn-sm" onclick="deleteShopProduct('${newId}')">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `;
}

async function deleteShopProduct(productId) {
    if (!confirm('Xóa sản phẩm này?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/config/shop-products/${productId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            showNotification('✅ Đã xóa sản phẩm!', 'success');
            loadShopProducts();
        } else {
            const data = await response.json();
            showNotification('❌ Lỗi: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('Error deleting shop product:', error);
        showNotification('❌ Lỗi xóa: ' + error.message, 'error');
    }
}

async function saveShopProducts() {
    try {
        const products = {};
        document.querySelectorAll('#shopProductsTable tr').forEach(row => {
            const id = row.dataset.productId;
            if (id) {
                products[id] = {
                    name: row.querySelector('[data-field="name"]').value,
                    price: parseInt(row.querySelector('[data-field="price"]').value),
                    stock: parseInt(row.querySelector('[data-field="stock"]').value),
                    enabled: row.querySelector('[data-field="enabled"]').value === 'true'
                };
            }
        });
        
        const response = await fetch(`${API_BASE}/api/admin/config/shop-products`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ products })
        });
        
        if (response.ok) {
            showNotification('✅ Đã lưu sản phẩm thành công!', 'success');
        } else {
            const data = await response.json();
            showNotification('❌ Lỗi: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('Error saving shop products:', error);
        showNotification('❌ Lỗi lưu: ' + error.message, 'error');
    }
}

// ===== STATUS ANNOUNCEMENT MANAGEMENT =====

async function loadAnnouncements() {
    try {
        console.log('[DEBUG] Loading announcements...');
        const response = await fetch(`${API_BASE}/admin/status-announcement`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        console.log('[DEBUG] Response status:', response.status);
        
        if (!response.ok) {
            throw new Error('Failed to load announcements: ' + response.status);
        }
        
        const data = await response.json();
        console.log('[DEBUG] Announcements data:', data);
        const announcements = data.announcements || [];
        
        const container = document.getElementById('announcementsContent');
        
        if (!container) {
            console.error('[ERROR] announcementsContent container not found!');
            return;
        }
        
        if (announcements.length === 0) {
            container.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:40px">Chưa có thông báo nào</p>';
            return;
        }
        
        let html = '<div style="display:flex;flex-direction:column;gap:16px">';
        
        announcements.forEach(ann => {
            const typeColors = {
                'info': { bg: 'rgba(96, 165, 250, 0.2)', border: '#60a5fa', icon: 'ℹ️' },
                'warning': { bg: 'rgba(245, 158, 11, 0.2)', border: '#f59e0b', icon: '⚠️' },
                'success': { bg: 'rgba(16, 185, 129, 0.2)', border: '#10b981', icon: '✅' },
                'error': { bg: 'rgba(239, 68, 68, 0.2)', border: '#ef4444', icon: '❌' }
            };
            
            const colors = typeColors[ann.type] || typeColors.info;
            const createdDate = new Date(ann.created_at).toLocaleString('vi-VN');
            
            html += `
                <div style="background:${colors.bg};border-left:4px solid ${colors.border};padding:16px;border-radius:8px">
                    <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:12px">
                        <div style="flex:1">
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                                <span style="font-size:20px">${colors.icon}</span>
                                <span class="badge" style="background:${colors.bg};color:${colors.border};border:1px solid ${colors.border}">${ann.type.toUpperCase()}</span>
                                ${ann.is_active ? '<span class="badge badge-success"><i class="fas fa-eye"></i> Đang hiển thị</span>' : '<span class="badge" style="background:rgba(148,163,184,0.2);color:#94a3b8"><i class="fas fa-eye-slash"></i> Ẩn</span>'}
                            </div>
                            <p style="margin:0;color:var(--text);font-size:15px;line-height:1.6">${ann.message}</p>
                            <p style="margin:8px 0 0 0;color:var(--text-muted);font-size:12px">
                                <i class="fas fa-clock"></i> ${createdDate}
                            </p>
                        </div>
                        <div style="display:flex;gap:8px;margin-left:16px">
                            <button class="btn btn-sm btn-primary" 
                                    onclick="editAnnouncement(${ann.id}, '${ann.message.replace(/'/g, "\\'")}', '${ann.type}', ${ann.is_active})"
                                    title="Chỉnh sửa thông báo">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-sm ${ann.is_active ? 'btn-warning' : 'btn-success'}" 
                                    onclick="toggleAnnouncementStatus(${ann.id}, ${!ann.is_active})"
                                    title="${ann.is_active ? 'Ẩn thông báo' : 'Hiển thị thông báo'}">
                                <i class="fas fa-${ann.is_active ? 'eye-slash' : 'eye'}"></i>
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deleteAnnouncement(${ann.id})" title="Xóa">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        container.innerHTML = html;
        
        console.log('[DEBUG] Announcements loaded successfully');
        
    } catch (error) {
        console.error('[ERROR] Error loading announcements:', error);
        const container = document.getElementById('announcementsContent');
        if (container) {
            container.innerHTML = 
                '<p style="color:var(--danger);text-align:center;padding:40px">Lỗi tải thông báo: ' + error.message + '</p>';
        }
    }
}

async function saveAnnouncement(event) {
    event.preventDefault();
    
    const message = document.getElementById('announcementMessage').value.trim();
    const type = document.getElementById('announcementType').value;
    const isActive = document.getElementById('announcementActiveToggle').checked;
    
    if (!message) {
        alert('Vui lòng nhập nội dung thông báo');
        return;
    }
    
    try {
        let response;
        
        // Check if we're in edit mode
        if (editingAnnouncementId) {
            // UPDATE existing announcement
            console.log('[DEBUG] Updating announcement:', editingAnnouncementId);
            response = await fetch(`${API_BASE}/admin/status-announcement/${editingAnnouncementId}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${authToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    type: type,
                    is_active: isActive
                })
            });
        } else {
            // CREATE new announcement
            console.log('[DEBUG] Creating new announcement');
            response = await fetch(`${API_BASE}/admin/status-announcement`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${authToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    type: type,
                    is_active: isActive
                })
            });
        }
        
        console.log('[DEBUG] Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[ERROR] Response error:', errorText);
            let errorData;
            try {
                errorData = JSON.parse(errorText);
            } catch (e) {
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            throw new Error(errorData.error || 'Failed to save announcement');
        }
        
        // Reset form and edit mode
        cancelEditAnnouncement();
        
        // Reload list
        loadAnnouncements();
        
        alert(editingAnnouncementId ? '✅ Đã cập nhật thông báo thành công!' : '✅ Đã lưu thông báo thành công!');
        
    } catch (error) {
        console.error('[ERROR] Error saving announcement:', error);
        alert('❌ Lỗi: ' + error.message);
    }
}

async function toggleAnnouncementStatus(announcementId, newStatus) {
    try {
        const response = await fetch(`${API_BASE}/admin/status-announcement/${announcementId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                is_active: newStatus
            })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to update announcement');
        }
        
        loadAnnouncements();
        
    } catch (error) {
        console.error('Error toggling announcement:', error);
        alert('❌ Lỗi: ' + error.message);
    }
}

async function deleteAnnouncement(announcementId) {
    if (!confirm('Bạn có chắc muốn xóa thông báo này?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/admin/status-announcement/${announcementId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to delete announcement');
        }
        
        loadAnnouncements();
        alert('✅ Đã xóa thông báo!');
        
    } catch (error) {
        console.error('Error deleting announcement:', error);
        alert('❌ Lỗi: ' + error.message);
    }
}

// Global variable to track edit mode
let editingAnnouncementId = null;

async function editAnnouncement(announcementId, message, type, isActive) {
    // Set edit mode
    editingAnnouncementId = announcementId;
    
    // Populate form with existing data
    document.getElementById('announcementMessage').value = message;
    document.getElementById('announcementType').value = type;
    document.getElementById('announcementActiveToggle').checked = isActive;
    
    // Change form title and button text
    const formTitle = document.getElementById('announcementFormTitle');
    formTitle.innerHTML = '<i class="fas fa-edit"></i> Chỉnh sửa thông báo';
    
    const submitBtn = document.querySelector('#announcementForm button[type="submit"]');
    submitBtn.innerHTML = '<i class="fas fa-save"></i> Cập nhật thông báo';
    submitBtn.classList.remove('btn-primary');
    submitBtn.classList.add('btn-warning');
    
    // Add cancel button if not exists
    if (!document.getElementById('cancelEditBtn')) {
        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.id = 'cancelEditBtn';
        cancelBtn.className = 'btn btn-ghost';
        cancelBtn.style.minWidth = '150px';
        cancelBtn.innerHTML = '<i class="fas fa-times"></i> Hủy';
        cancelBtn.onclick = cancelEditAnnouncement;
        submitBtn.parentNode.appendChild(cancelBtn);
    }
    
    // Scroll to form - with offset for header
    const formElement = document.getElementById('announcementForm');
    const yOffset = -100; // Offset for header/padding
    const y = formElement.getBoundingClientRect().top + window.pageYOffset + yOffset;
    window.scrollTo({ top: y, behavior: 'smooth' });
}

function cancelEditAnnouncement() {
    // Reset edit mode
    editingAnnouncementId = null;
    
    // Clear form
    document.getElementById('announcementMessage').value = '';
    document.getElementById('announcementType').value = 'info';
    document.getElementById('announcementActiveToggle').checked = true;
    
    // Reset form title and button
    const formTitle = document.getElementById('announcementFormTitle');
    formTitle.innerHTML = '<i class="fas fa-plus-circle"></i> Tạo thông báo mới';
    
    const submitBtn = document.querySelector('#announcementForm button[type="submit"]');
    submitBtn.innerHTML = '<i class="fas fa-save"></i> Lưu thông báo';
    submitBtn.classList.remove('btn-warning');
    submitBtn.classList.add('btn-primary');
    
    // Remove cancel button
    const cancelBtn = document.getElementById('cancelEditBtn');
    if (cancelBtn) {
        cancelBtn.remove();
    }
}


// Edit announcement function
async function editAnnouncement(id, message, type, isActive) {
    // Populate form with existing data
    document.getElementById('announcementMessage').value = message;
    document.getElementById('announcementType').value = type;
    document.getElementById('announcementActiveToggle').checked = isActive;
    
    // Change form title
    const formTitle = document.querySelector('#announcementTab h3');
    if (formTitle) {
        formTitle.innerHTML = '<i class="fas fa-edit"></i> Chỉnh sửa thông báo #' + id;
    }
    
    // Change button text and add data attribute
    const submitBtn = document.querySelector('#announcementForm button[type="submit"]');
    if (submitBtn) {
        submitBtn.innerHTML = '<i class="fas fa-save"></i> Cập nhật thông báo';
        submitBtn.dataset.editId = id;
    }
    
    // Scroll to form
    document.querySelector('#announcementTab').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Update saveAnnouncement to handle both create and edit
async function saveAnnouncement(event) {
    event.preventDefault();
    
    const message = document.getElementById('announcementMessage').value.trim();
    const type = document.getElementById('announcementType').value;
    const isActive = document.getElementById('announcementActiveToggle').checked;
    
    if (!message) {
        alert('Vui lòng nhập nội dung thông báo');
        return;
    }
    
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const editId = submitBtn.dataset.editId;
    
    try {
        let response;
        
        if (editId) {
            // Update existing announcement
            console.log('[DEBUG] Updating announcement:', editId);
            response = await fetch(`${API_BASE}/api/admin/status-announcement/${editId}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${authToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    type: type,
                    is_active: isActive
                })
            });
        } else {
            // Create new announcement
            console.log('[DEBUG] Creating new announcement');
            response = await fetch(`${API_BASE}/api/admin/status-announcement`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${authToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    type: type,
                    is_active: isActive
                })
            });
        }
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to save announcement');
        }
        
        // Reset form
        document.getElementById('announcementMessage').value = '';
        document.getElementById('announcementType').value = 'info';
        document.getElementById('announcementActiveToggle').checked = true;
        
        // Reset form title and button
        const formTitle = document.querySelector('#announcementTab h3');
        if (formTitle) {
            formTitle.innerHTML = '<i class="fas fa-plus-circle"></i> Tạo thông báo mới';
        }
        
        if (submitBtn) {
            submitBtn.innerHTML = '<i class="fas fa-save"></i> Lưu thông báo';
            delete submitBtn.dataset.editId;
        }
        
        // Reload list
        loadAnnouncements();
        
        alert(editId ? '✅ Đã cập nhật thông báo!' : '✅ Đã tạo thông báo mới!');
        
    } catch (error) {
        console.error('[ERROR] Error saving announcement:', error);
        alert('❌ Lỗi: ' + error.message);
    }
}
