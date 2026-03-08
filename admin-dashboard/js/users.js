/**
 * User Management Module
 * Handles user-related operations including listing, searching, filtering, and user actions
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9
 */

// Module state
let apiClient = null;
let currentPage = 1;
let currentFilters = {};
let searchDebounceTimer = null;

/**
 * Initialize the user management module
 * @param {APIClient} api - API client instance
 */
function initUserManagement(api) {
  apiClient = api;
  setupUserSearch();
  setupUserFilters();
  
  // Load initial user list
  loadUsers();
}

/**
 * Fetch users from API with pagination and filters
 * @param {number} page - Page number (1-indexed)
 * @param {object} filters - Filter options (status, search, etc.)
 * @returns {Promise<object>} User list data
 * Requirements: 2.1, 2.2, 2.3
 */
async function fetchUsers(page = 1, filters = {}) {
  try {
    LoadingSpinner.show('#user-list-container');
    
    // Build filter parameters
    const params = {
      page,
      pageSize: 20, // Requirement 2.1: 20 users per page
      ...filters
    };
    
    // Remove empty filters
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key];
      }
    });
    
    const data = await apiClient.getUsers(page, params);
    
    return data;
  } catch (error) {
    Notification.error(`Failed to load users: ${error.message}`);
    throw error;
  } finally {
    LoadingSpinner.hide();
  }
}

/**
 * Render user list in the table
 * @param {Array} users - Array of user objects
 * Requirements: 2.1, 2.4
 */
function renderUserList(users) {
  const tbody = document.getElementById('user-table-body');
  
  if (!tbody) {
    console.error('User table body element not found');
    return;
  }
  
  // Clear existing rows
  tbody.innerHTML = '';
  
  // Handle empty list
  if (!users || users.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="empty-state">
          <i class="fas fa-users"></i>
          <p>No users found</p>
        </td>
      </tr>
    `;
    return;
  }
  
  // Render user rows
  users.forEach(user => {
    const row = document.createElement('tr');
    row.dataset.userId = user.id;
    
    // Format VIP status
    const vipStatus = user.vipStatus && user.vipStatus.tier !== 'none' 
      ? `<span class="badge badge-vip">${user.vipStatus.tier}</span>`
      : '<span class="badge badge-default">None</span>';
    
    // Format user status
    const statusBadge = user.blocked 
      ? '<span class="badge badge-danger">Blocked</span>'
      : '<span class="badge badge-success">Active</span>';
    
    row.innerHTML = `
      <td>${escapeHTML(String(user.id))}</td>
      <td>${escapeHTML(user.username || 'N/A')}</td>
      <td>${formatNumber(user.coins || 0, 0)}</td>
      <td>${formatNumber(user.cash || 0, 2)}</td>
      <td>${vipStatus}</td>
      <td>${statusBadge}</td>
      <td class="actions">
        <button class="btn btn-sm btn-primary" onclick="showUserDetails(${user.id})" title="View Details">
          <i class="fas fa-eye"></i>
        </button>
        <button class="btn btn-sm btn-secondary" onclick="showUserActionsMenu(${user.id})" title="Actions">
          <i class="fas fa-ellipsis-v"></i>
        </button>
      </td>
    `;
    
    tbody.appendChild(row);
  });
}

/**
 * Setup user search with debounced input
 * Requirements: 2.2, 10.2 (300ms debounce)
 */
function setupUserSearch() {
  const searchInput = document.getElementById('user-search-input');
  
  if (!searchInput) {
    console.warn('User search input not found');
    return;
  }
  
  // Create debounced search function (300ms delay per requirement 10.2)
  const debouncedSearch = debounce((searchTerm) => {
    currentFilters.search = searchTerm;
    currentPage = 1; // Reset to first page on new search
    loadUsers();
  }, 300);
  
  // Add input event listener
  searchInput.addEventListener('input', (e) => {
    const searchTerm = e.target.value.trim();
    debouncedSearch(searchTerm);
  });
}

/**
 * Setup user filters for status filtering
 * Requirements: 2.3 (VIP, blocked, active filters)
 */
function setupUserFilters() {
  const statusFilter = document.getElementById('user-status-filter');
  
  if (!statusFilter) {
    console.warn('User status filter not found');
    return;
  }
  
  // Add change event listener
  statusFilter.addEventListener('change', (e) => {
    const status = e.target.value;
    
    // Update filters based on selection
    if (status === 'all') {
      delete currentFilters.vip;
      delete currentFilters.blocked;
      delete currentFilters.active;
    } else if (status === 'vip') {
      currentFilters.vip = true;
      delete currentFilters.blocked;
      delete currentFilters.active;
    } else if (status === 'blocked') {
      currentFilters.blocked = true;
      delete currentFilters.vip;
      delete currentFilters.active;
    } else if (status === 'active') {
      currentFilters.active = true;
      delete currentFilters.vip;
      delete currentFilters.blocked;
    }
    
    currentPage = 1; // Reset to first page on filter change
    loadUsers();
  });
}

/**
 * Load users with current page and filters
 */
async function loadUsers() {
  try {
    const data = await fetchUsers(currentPage, currentFilters);
    
    // Render user list
    renderUserList(data.users || []);
    
    // Update pagination
    updateUserPagination(data.total || 0, data.pageSize || 20);
  } catch (error) {
    console.error('Failed to load users:', error);
  }
}

/**
 * Update pagination controls
 * @param {number} total - Total number of users
 * @param {number} pageSize - Number of users per page
 */
function updateUserPagination(total, pageSize) {
  const paginationContainer = document.getElementById('user-pagination');
  
  if (!paginationContainer) {
    console.warn('User pagination container not found');
    return;
  }
  
  const totalPages = Math.ceil(total / pageSize);
  
  // Create or update pagination component
  if (!window.userPagination) {
    window.userPagination = new Pagination(paginationContainer, {
      totalPages,
      currentPage
    });
    
    window.userPagination.onPageChange((page) => {
      currentPage = page;
      loadUsers();
    });
  } else {
    window.userPagination.setTotalPages(totalPages);
    window.userPagination.setCurrentPage(currentPage);
  }
  
  window.userPagination.render();
}

/**
 * Show user details in a modal
 * @param {number} userId - User ID
 * Requirements: 2.4
 */
async function showUserDetails(userId) {
  try {
    LoadingSpinner.show();
    
    // Fetch user details from API
    const user = await apiClient.getUserDetails(userId);
    
    LoadingSpinner.hide();
    
    // Format VIP expiration
    let vipInfo = 'None';
    if (user.vipStatus && user.vipStatus.tier !== 'none') {
      const expiresAt = user.vipStatus.expiresAt 
        ? formatDate(user.vipStatus.expiresAt, 'YYYY-MM-DD HH:mm')
        : 'Never';
      vipInfo = `${user.vipStatus.tier} (Expires: ${expiresAt})`;
    }
    
    // Format blocked status
    const blockedInfo = user.blocked 
      ? `Yes - ${escapeHTML(user.blockedReason || 'No reason provided')}`
      : 'No';
    
    // Format dates
    const createdAt = formatDate(user.createdAt, 'YYYY-MM-DD HH:mm');
    const lastActive = user.lastActive 
      ? formatRelativeTime(user.lastActive)
      : 'Never';
    
    // Build statistics section
    let statsHTML = '';
    if (user.statistics) {
      statsHTML = `
        <div class="user-stats">
          <h3>Statistics</h3>
          <div class="stats-grid">
            <div class="stat-item">
              <label>Total Verifications:</label>
              <span>${user.statistics.totalVerifications || 0}</span>
            </div>
            <div class="stat-item">
              <label>Total Spent:</label>
              <span>${formatCurrency(user.statistics.totalSpent || 0)}</span>
            </div>
            <div class="stat-item">
              <label>Success Rate:</label>
              <span>${formatPercentage(user.statistics.successRate || 0, 1, false)}%</span>
            </div>
          </div>
        </div>
      `;
    }
    
    // Build recent transactions section
    let transactionsHTML = '';
    if (user.recentTransactions && user.recentTransactions.length > 0) {
      const transactionRows = user.recentTransactions.map(tx => `
        <tr>
          <td>${escapeHTML(tx.type)}</td>
          <td>${formatCurrency(tx.amount)}</td>
          <td>${formatDate(tx.createdAt, 'YYYY-MM-DD HH:mm')}</td>
        </tr>
      `).join('');
      
      transactionsHTML = `
        <div class="user-transactions">
          <h3>Recent Transactions</h3>
          <table class="data-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Amount</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              ${transactionRows}
            </tbody>
          </table>
        </div>
      `;
    }
    
    // Create modal content
    const content = `
      <div class="user-details">
        <div class="user-info-grid">
          <div class="info-item">
            <label>User ID:</label>
            <span>${escapeHTML(String(user.id))}</span>
          </div>
          <div class="info-item">
            <label>Username:</label>
            <span>${escapeHTML(user.username || 'N/A')}</span>
          </div>
          <div class="info-item">
            <label>First Name:</label>
            <span>${escapeHTML(user.firstName || 'N/A')}</span>
          </div>
          <div class="info-item">
            <label>Last Name:</label>
            <span>${escapeHTML(user.lastName || 'N/A')}</span>
          </div>
          <div class="info-item">
            <label>Coins:</label>
            <span>${formatNumber(user.coins || 0, 0)}</span>
          </div>
          <div class="info-item">
            <label>Cash:</label>
            <span>${formatCurrency(user.cash || 0)}</span>
          </div>
          <div class="info-item">
            <label>VIP Status:</label>
            <span>${vipInfo}</span>
          </div>
          <div class="info-item">
            <label>Blocked:</label>
            <span>${blockedInfo}</span>
          </div>
          <div class="info-item">
            <label>Daily Verify Limit:</label>
            <span>${user.dailyVerifyLimit || 'Unlimited'}</span>
          </div>
          <div class="info-item">
            <label>Created:</label>
            <span>${createdAt}</span>
          </div>
          <div class="info-item">
            <label>Last Active:</label>
            <span>${lastActive}</span>
          </div>
        </div>
        
        ${statsHTML}
        ${transactionsHTML}
        
        <div class="user-actions-buttons">
          <button class="btn btn-primary" onclick="handleEditCoins(${userId})">
            <i class="fas fa-coins"></i> Edit Coins
          </button>
          <button class="btn btn-primary" onclick="handleEditCash(${userId})">
            <i class="fas fa-dollar-sign"></i> Edit Cash
          </button>
          <button class="btn btn-secondary" onclick="handleManageVIP(${userId})">
            <i class="fas fa-crown"></i> Manage VIP
          </button>
          ${user.blocked 
            ? `<button class="btn btn-success" onclick="handleUnblockUser(${userId})">
                <i class="fas fa-unlock"></i> Unblock User
              </button>`
            : `<button class="btn btn-danger" onclick="handleBlockUser(${userId})">
                <i class="fas fa-ban"></i> Block User
              </button>`
          }
          <button class="btn btn-secondary" onclick="handleSendMessage(${userId})">
            <i class="fas fa-envelope"></i> Send Message
          </button>
          <button class="btn btn-secondary" onclick="handleSetLimit(${userId})">
            <i class="fas fa-limit"></i> Set Limit
          </button>
        </div>
      </div>
    `;
    
    // Show modal
    const modal = new Modal(`User Details - ${user.username}`, content, {
      width: '800px'
    });
    modal.show();
    
  } catch (error) {
    LoadingSpinner.hide();
    Notification.error(`Failed to load user details: ${error.message}`);
  }
}

/**
 * Show user actions menu (alternative to detail view)
 * @param {number} userId - User ID
 */
function showUserActionsMenu(userId) {
  const content = `
    <div class="user-actions-menu">
      <button class="btn btn-block btn-primary" onclick="showUserDetails(${userId})">
        <i class="fas fa-eye"></i> View Details
      </button>
      <button class="btn btn-block btn-primary" onclick="handleEditCoins(${userId})">
        <i class="fas fa-coins"></i> Edit Coins
      </button>
      <button class="btn btn-block btn-primary" onclick="handleEditCash(${userId})">
        <i class="fas fa-dollar-sign"></i> Edit Cash
      </button>
      <button class="btn btn-block btn-secondary" onclick="handleManageVIP(${userId})">
        <i class="fas fa-crown"></i> Manage VIP
      </button>
      <button class="btn btn-block btn-danger" onclick="handleBlockUser(${userId})">
        <i class="fas fa-ban"></i> Block User
      </button>
      <button class="btn btn-block btn-secondary" onclick="handleSendMessage(${userId})">
        <i class="fas fa-envelope"></i> Send Message
      </button>
      <button class="btn btn-block btn-secondary" onclick="handleSetLimit(${userId})">
        <i class="fas fa-limit"></i> Set Limit
      </button>
    </div>
  `;
  
  const modal = new Modal('User Actions', content, {
    width: '400px'
  });
  modal.show();
}

// Export functions for global access
if (typeof window !== 'undefined') {
  window.initUserManagement = initUserManagement;
  window.fetchUsers = fetchUsers;
  window.renderUserList = renderUserList;
  window.setupUserSearch = setupUserSearch;
  window.setupUserFilters = setupUserFilters;
  window.showUserDetails = showUserDetails;
  window.showUserActionsMenu = showUserActionsMenu;
  window.loadUsers = loadUsers;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    initUserManagement,
    fetchUsers,
    renderUserList,
    setupUserSearch,
    setupUserFilters,
    showUserDetails,
    showUserActionsMenu,
    loadUsers
  };
}

/**
 * Handle editing user coins
 * @param {number} userId - User ID
 * Requirements: 2.5
 */
async function handleEditCoins(userId) {
  const content = `
    <div class="edit-coins-form">
      <p>Enter the amount to add or subtract from the user's coin balance.</p>
      <p>Use positive numbers to add coins, negative numbers to subtract.</p>
      <div class="form-group">
        <label for="coins-amount">Amount:</label>
        <input type="number" id="coins-amount" class="form-control" placeholder="e.g., 100 or -50" step="1">
      </div>
      <div class="form-actions">
        <button class="btn btn-secondary" onclick="closeCurrentModal()">Cancel</button>
        <button class="btn btn-primary" onclick="submitEditCoins(${userId})">Update Coins</button>
      </div>
    </div>
  `;
  
  const modal = new Modal('Edit User Coins', content, {
    width: '500px'
  });
  
  // Store modal reference for closing
  window.currentModal = modal;
  modal.show();
}

/**
 * Submit coin edit
 * @param {number} userId - User ID
 */
async function submitEditCoins(userId) {
  const amountInput = document.getElementById('coins-amount');
  const amount = parseInt(amountInput.value);
  
  if (isNaN(amount) || amount === 0) {
    Notification.error('Please enter a valid amount');
    return;
  }
  
  try {
    LoadingSpinner.show();
    
    await apiClient.updateUserCoins(userId, amount);
    
    LoadingSpinner.hide();
    Notification.success('User coins updated successfully');
    
    // Close modal and reload users
    closeCurrentModal();
    loadUsers();
  } catch (error) {
    LoadingSpinner.hide();
    Notification.error(`Failed to update coins: ${error.message}`);
  }
}

/**
 * Handle editing user cash
 * @param {number} userId - User ID
 * Requirements: 2.5
 */
async function handleEditCash(userId) {
  const content = `
    <div class="edit-cash-form">
      <p>Enter the amount to add or subtract from the user's cash balance.</p>
      <p>Use positive numbers to add cash, negative numbers to subtract.</p>
      <div class="form-group">
        <label for="cash-amount">Amount:</label>
        <input type="number" id="cash-amount" class="form-control" placeholder="e.g., 10.50 or -5.00" step="0.01">
      </div>
      <div class="form-actions">
        <button class="btn btn-secondary" onclick="closeCurrentModal()">Cancel</button>
        <button class="btn btn-primary" onclick="submitEditCash(${userId})">Update Cash</button>
      </div>
    </div>
  `;
  
  const modal = new Modal('Edit User Cash', content, {
    width: '500px'
  });
  
  window.currentModal = modal;
  modal.show();
}

/**
 * Submit cash edit
 * @param {number} userId - User ID
 */
async function submitEditCash(userId) {
  const amountInput = document.getElementById('cash-amount');
  const amount = parseFloat(amountInput.value);
  
  if (isNaN(amount) || amount === 0) {
    Notification.error('Please enter a valid amount');
    return;
  }
  
  try {
    LoadingSpinner.show();
    
    await apiClient.updateUserCash(userId, amount);
    
    LoadingSpinner.hide();
    Notification.success('User cash updated successfully');
    
    closeCurrentModal();
    loadUsers();
  } catch (error) {
    LoadingSpinner.hide();
    Notification.error(`Failed to update cash: ${error.message}`);
  }
}

/**
 * Handle managing user VIP status
 * @param {number} userId - User ID
 * Requirements: 2.6
 */
async function handleManageVIP(userId) {
  const content = `
    <div class="manage-vip-form">
      <p>Select VIP tier and duration for the user.</p>
      <div class="form-group">
        <label for="vip-tier">VIP Tier:</label>
        <select id="vip-tier" class="form-control">
          <option value="none">None (Remove VIP)</option>
          <option value="basic">Basic</option>
          <option value="pro">Pro</option>
          <option value="business">Business</option>
        </select>
      </div>
      <div class="form-group" id="vip-duration-group">
        <label for="vip-duration">Duration (days):</label>
        <input type="number" id="vip-duration" class="form-control" placeholder="e.g., 30" min="1" value="30">
      </div>
      <div class="form-actions">
        <button class="btn btn-secondary" onclick="closeCurrentModal()">Cancel</button>
        <button class="btn btn-primary" onclick="submitManageVIP(${userId})">Update VIP Status</button>
      </div>
    </div>
  `;
  
  const modal = new Modal('Manage VIP Status', content, {
    width: '500px'
  });
  
  window.currentModal = modal;
  modal.show();
  
  // Add event listener to hide duration field when "none" is selected
  setTimeout(() => {
    const tierSelect = document.getElementById('vip-tier');
    const durationGroup = document.getElementById('vip-duration-group');
    
    if (tierSelect && durationGroup) {
      tierSelect.addEventListener('change', (e) => {
        if (e.target.value === 'none') {
          durationGroup.style.display = 'none';
        } else {
          durationGroup.style.display = 'block';
        }
      });
    }
  }, 100);
}

/**
 * Submit VIP status update
 * @param {number} userId - User ID
 */
async function submitManageVIP(userId) {
  const tierSelect = document.getElementById('vip-tier');
  const durationInput = document.getElementById('vip-duration');
  
  const tier = tierSelect.value;
  const duration = tier !== 'none' ? parseInt(durationInput.value) : null;
  
  if (tier !== 'none' && (isNaN(duration) || duration < 1)) {
    Notification.error('Please enter a valid duration');
    return;
  }
  
  try {
    LoadingSpinner.show();
    
    await apiClient.setUserVIP(userId, tier, duration);
    
    LoadingSpinner.hide();
    Notification.success('VIP status updated successfully');
    
    closeCurrentModal();
    loadUsers();
  } catch (error) {
    LoadingSpinner.hide();
    Notification.error(`Failed to update VIP status: ${error.message}`);
  }
}

/**
 * Handle blocking a user
 * @param {number} userId - User ID
 * Requirements: 2.7
 */
async function handleBlockUser(userId) {
  const confirmed = await ConfirmDialog.show(
    'Are you sure you want to block this user? They will not be able to use the bot.',
    {
      title: 'Block User',
      confirmText: 'Block',
      confirmClass: 'btn-danger'
    }
  );
  
  if (!confirmed) {
    return;
  }
  
  // Show reason input
  const content = `
    <div class="block-user-form">
      <p>Please provide a reason for blocking this user:</p>
      <div class="form-group">
        <label for="block-reason">Reason:</label>
        <textarea id="block-reason" class="form-control" rows="3" placeholder="e.g., Spam, Abuse, Fraud"></textarea>
      </div>
      <div class="form-actions">
        <button class="btn btn-secondary" onclick="closeCurrentModal()">Cancel</button>
        <button class="btn btn-danger" onclick="submitBlockUser(${userId})">Block User</button>
      </div>
    </div>
  `;
  
  const modal = new Modal('Block User - Reason', content, {
    width: '500px'
  });
  
  window.currentModal = modal;
  modal.show();
}

/**
 * Submit user block
 * @param {number} userId - User ID
 */
async function submitBlockUser(userId) {
  const reasonInput = document.getElementById('block-reason');
  const reason = reasonInput.value.trim();
  
  if (!reason) {
    Notification.error('Please provide a reason for blocking');
    return;
  }
  
  try {
    LoadingSpinner.show();
    
    await apiClient.blockUser(userId, reason);
    
    LoadingSpinner.hide();
    Notification.success('User blocked successfully');
    
    closeCurrentModal();
    loadUsers();
  } catch (error) {
    LoadingSpinner.hide();
    Notification.error(`Failed to block user: ${error.message}`);
  }
}

/**
 * Handle unblocking a user
 * @param {number} userId - User ID
 * Requirements: 2.7
 */
async function handleUnblockUser(userId) {
  const confirmed = await ConfirmDialog.show(
    'Are you sure you want to unblock this user? They will be able to use the bot again.',
    {
      title: 'Unblock User',
      confirmText: 'Unblock',
      confirmClass: 'btn-success'
    }
  );
  
  if (!confirmed) {
    return;
  }
  
  try {
    LoadingSpinner.show();
    
    await apiClient.unblockUser(userId);
    
    LoadingSpinner.hide();
    Notification.success('User unblocked successfully');
    
    loadUsers();
  } catch (error) {
    LoadingSpinner.hide();
    Notification.error(`Failed to unblock user: ${error.message}`);
  }
}

/**
 * Handle sending a message to a user
 * @param {number} userId - User ID
 * Requirements: 2.8
 */
async function handleSendMessage(userId) {
  const content = `
    <div class="send-message-form">
      <p>Compose a message to send directly to this user via the bot:</p>
      <div class="form-group">
        <label for="message-text">Message:</label>
        <textarea id="message-text" class="form-control" rows="5" placeholder="Enter your message here..."></textarea>
      </div>
      <div class="form-actions">
        <button class="btn btn-secondary" onclick="closeCurrentModal()">Cancel</button>
        <button class="btn btn-primary" onclick="submitSendMessage(${userId})">Send Message</button>
      </div>
    </div>
  `;
  
  const modal = new Modal('Send Message to User', content, {
    width: '600px'
  });
  
  window.currentModal = modal;
  modal.show();
}

/**
 * Submit send message
 * @param {number} userId - User ID
 */
async function submitSendMessage(userId) {
  const messageInput = document.getElementById('message-text');
  const message = messageInput.value.trim();
  
  if (!message) {
    Notification.error('Please enter a message');
    return;
  }
  
  try {
    LoadingSpinner.show();
    
    await apiClient.sendMessage(userId, message);
    
    LoadingSpinner.hide();
    Notification.success('Message sent successfully');
    
    closeCurrentModal();
  } catch (error) {
    LoadingSpinner.hide();
    Notification.error(`Failed to send message: ${error.message}`);
  }
}

/**
 * Handle setting daily verification limit
 * @param {number} userId - User ID
 * Requirements: 2.9
 */
async function handleSetLimit(userId) {
  const content = `
    <div class="set-limit-form">
      <p>Set the daily verification limit for this user:</p>
      <div class="form-group">
        <label for="verify-limit">Daily Verification Limit:</label>
        <input type="number" id="verify-limit" class="form-control" placeholder="e.g., 10" min="0">
        <small class="form-text">Set to 0 for unlimited verifications</small>
      </div>
      <div class="form-actions">
        <button class="btn btn-secondary" onclick="closeCurrentModal()">Cancel</button>
        <button class="btn btn-primary" onclick="submitSetLimit(${userId})">Set Limit</button>
      </div>
    </div>
  `;
  
  const modal = new Modal('Set Daily Verification Limit', content, {
    width: '500px'
  });
  
  window.currentModal = modal;
  modal.show();
}

/**
 * Submit verification limit
 * @param {number} userId - User ID
 */
async function submitSetLimit(userId) {
  const limitInput = document.getElementById('verify-limit');
  const limit = parseInt(limitInput.value);
  
  if (isNaN(limit) || limit < 0) {
    Notification.error('Please enter a valid limit (0 or greater)');
    return;
  }
  
  try {
    LoadingSpinner.show();
    
    await apiClient.setUserLimit(userId, limit);
    
    LoadingSpinner.hide();
    Notification.success('Verification limit updated successfully');
    
    closeCurrentModal();
    loadUsers();
  } catch (error) {
    LoadingSpinner.hide();
    Notification.error(`Failed to set limit: ${error.message}`);
  }
}

/**
 * Close the current modal
 */
function closeCurrentModal() {
  if (window.currentModal) {
    window.currentModal.hide();
    window.currentModal = null;
  }
}

// Export additional functions for global access
if (typeof window !== 'undefined') {
  window.handleEditCoins = handleEditCoins;
  window.submitEditCoins = submitEditCoins;
  window.handleEditCash = handleEditCash;
  window.submitEditCash = submitEditCash;
  window.handleManageVIP = handleManageVIP;
  window.submitManageVIP = submitManageVIP;
  window.handleBlockUser = handleBlockUser;
  window.submitBlockUser = submitBlockUser;
  window.handleUnblockUser = handleUnblockUser;
  window.handleSendMessage = handleSendMessage;
  window.submitSendMessage = submitSendMessage;
  window.handleSetLimit = handleSetLimit;
  window.submitSetLimit = submitSetLimit;
  window.closeCurrentModal = closeCurrentModal;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    ...module.exports,
    handleEditCoins,
    submitEditCoins,
    handleEditCash,
    submitEditCash,
    handleManageVIP,
    submitManageVIP,
    handleBlockUser,
    submitBlockUser,
    handleUnblockUser,
    handleSendMessage,
    submitSendMessage,
    handleSetLimit,
    submitSetLimit,
    closeCurrentModal
  };
}
