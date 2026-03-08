/**
 * Transaction Management Module
 * Handles transaction-related operations including listing, filtering, viewing details, and CSV export
 * Requirements: 4.1, 4.2, 4.3, 4.4
 */

// Module state
let apiClient = null;
let currentPage = 1;
let currentFilters = {};

/**
 * Initialize the transaction management module
 * @param {APIClient} api - API client instance
 */
function initTransactionManagement(api) {
  apiClient = api;
  setupTransactionFilters();
  
  // Load initial transaction list
  loadTransactions();
}

/**
 * Fetch transactions from API with pagination and filters
 * @param {number} page - Page number (1-indexed)
 * @param {object} filters - Filter options (type, startDate, endDate, etc.)
 * @returns {Promise<object>} Transaction list data
 * Requirements: 4.1, 4.2
 */
async function fetchTransactions(page = 1, filters = {}) {
  try {
    LoadingSpinner.show('#transaction-list-container');
    
    // Build filter parameters
    const params = {
      page,
      pageSize: 50, // Requirement 4.1: 50 transactions per page
      ...filters
    };
    
    // Remove empty filters
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key];
      }
    });
    
    const data = await apiClient.getTransactions(page, params);
    
    return data;
  } catch (error) {
    Notification.error(`Failed to load transactions: ${error.message}`);
    throw error;
  } finally {
    LoadingSpinner.hide();
  }
}

/**
 * Render transaction list in the table
 * @param {Array} transactions - Array of transaction objects
 * Requirements: 4.1, 4.3
 */
function renderTransactionList(transactions) {
  const tbody = document.getElementById('transaction-table-body');
  
  if (!tbody) {
    console.error('Transaction table body element not found');
    return;
  }
  
  // Clear existing rows
  tbody.innerHTML = '';
  
  // Handle empty list
  if (!transactions || transactions.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="empty-state">
          <i class="fas fa-dollar-sign"></i>
          <p>No transactions found</p>
        </td>
      </tr>
    `;
    return;
  }
  
  // Render transaction rows
  transactions.forEach(transaction => {
    const row = document.createElement('tr');
    row.dataset.transactionId = transaction.id;
    
    // Format type badge
    let typeBadge = '';
    switch (transaction.type) {
      case 'deposit':
        typeBadge = '<span class="badge badge-success">Deposit</span>';
        break;
      case 'verify':
        typeBadge = '<span class="badge badge-primary">Verification</span>';
        break;
      case 'shop':
        typeBadge = '<span class="badge badge-info">Shop Purchase</span>';
        break;
      case 'vip_purchase':
        typeBadge = '<span class="badge badge-vip">VIP Purchase</span>';
        break;
      case 'refund':
        typeBadge = '<span class="badge badge-warning">Refund</span>';
        break;
      default:
        typeBadge = `<span class="badge badge-default">${escapeHTML(transaction.type)}</span>`;
    }
    
    // Format status badge
    let statusBadge = '';
    switch (transaction.status) {
      case 'completed':
        statusBadge = '<span class="badge badge-success">Completed</span>';
        break;
      case 'pending':
        statusBadge = '<span class="badge badge-warning">Pending</span>';
        break;
      case 'failed':
        statusBadge = '<span class="badge badge-danger">Failed</span>';
        break;
      default:
        statusBadge = `<span class="badge badge-default">${escapeHTML(transaction.status)}</span>`;
    }
    
    // Format amount with currency
    const amount = formatCurrency(transaction.amount || 0, transaction.currency || 'USD');
    
    // Format created date
    const createdAt = formatDate(transaction.createdAt, 'YYYY-MM-DD HH:mm');
    
    row.innerHTML = `
      <td data-label="Transaction ID">${escapeHTML(String(transaction.id))}</td>
      <td data-label="User">${escapeHTML(transaction.username || 'N/A')}</td>
      <td data-label="Type">${typeBadge}</td>
      <td data-label="Amount">${amount}</td>
      <td data-label="Status">${statusBadge}</td>
      <td data-label="Date">${createdAt}</td>
      <td class="actions" data-label="Actions">
        <button class="btn btn-sm btn-primary" onclick="showTransactionDetails('${escapeHTML(String(transaction.id))}')" title="View Details">
          <i class="fas fa-eye"></i>
        </button>
      </td>
    `;
    
    tbody.appendChild(row);
  });
}

/**
 * Setup transaction filters for type and date filtering
 * Requirements: 4.2 (type filtering)
 */
function setupTransactionFilters() {
  const typeFilter = document.getElementById('transaction-type-filter');
  const startDateFilter = document.getElementById('transaction-start-date');
  const endDateFilter = document.getElementById('transaction-end-date');
  const clearFiltersBtn = document.getElementById('clear-transaction-filters');
  const exportBtn = document.getElementById('export-transactions-btn');
  
  // Type filter
  if (typeFilter) {
    typeFilter.addEventListener('change', (e) => {
      const type = e.target.value;
      
      if (type === 'all') {
        delete currentFilters.type;
      } else {
        currentFilters.type = type;
      }
      
      currentPage = 1; // Reset to first page on filter change
      loadTransactions();
    });
  } else {
    console.warn('Transaction type filter not found');
  }
  
  // Start date filter
  if (startDateFilter) {
    startDateFilter.addEventListener('change', (e) => {
      const startDate = e.target.value;
      
      if (startDate) {
        currentFilters.startDate = startDate;
      } else {
        delete currentFilters.startDate;
      }
      
      currentPage = 1; // Reset to first page on filter change
      loadTransactions();
    });
  } else {
    console.warn('Transaction start date filter not found');
  }
  
  // End date filter
  if (endDateFilter) {
    endDateFilter.addEventListener('change', (e) => {
      const endDate = e.target.value;
      
      if (endDate) {
        currentFilters.endDate = endDate;
      } else {
        delete currentFilters.endDate;
      }
      
      currentPage = 1; // Reset to first page on filter change
      loadTransactions();
    });
  } else {
    console.warn('Transaction end date filter not found');
  }
  
  // Clear filters button
  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener('click', () => {
      // Reset all filters
      currentFilters = {};
      currentPage = 1;
      
      // Reset filter UI elements
      if (typeFilter) typeFilter.value = 'all';
      if (startDateFilter) startDateFilter.value = '';
      if (endDateFilter) endDateFilter.value = '';
      
      // Reload transactions
      loadTransactions();
    });
  } else {
    console.warn('Clear transaction filters button not found');
  }
  
  // Export CSV button
  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      handleExportCSV(currentFilters);
    });
  } else {
    console.warn('Export transactions button not found');
  }
}

/**
 * Load transactions with current page and filters
 */
async function loadTransactions() {
  try {
    const data = await fetchTransactions(currentPage, currentFilters);
    
    // Render transaction list
    renderTransactionList(data.transactions || []);
    
    // Update pagination
    updateTransactionPagination(data.total || 0, data.pageSize || 50);
  } catch (error) {
    console.error('Failed to load transactions:', error);
  }
}

/**
 * Update pagination controls
 * @param {number} total - Total number of transactions
 * @param {number} pageSize - Number of transactions per page
 */
function updateTransactionPagination(total, pageSize) {
  const paginationContainer = document.getElementById('transaction-pagination');
  
  if (!paginationContainer) {
    console.warn('Transaction pagination container not found');
    return;
  }
  
  const totalPages = Math.ceil(total / pageSize);
  
  // Create or update pagination component
  if (!window.transactionPagination) {
    window.transactionPagination = new Pagination(paginationContainer, {
      totalPages,
      currentPage
    });
    
    window.transactionPagination.onPageChange((page) => {
      currentPage = page;
      loadTransactions();
    });
  } else {
    window.transactionPagination.setTotalPages(totalPages);
    window.transactionPagination.setCurrentPage(currentPage);
  }
  
  window.transactionPagination.render();
}

/**
 * Show transaction details in a modal
 * @param {string} transactionId - Transaction ID
 * Requirements: 4.3
 */
async function showTransactionDetails(transactionId) {
  try {
    LoadingSpinner.show();
    
    // Fetch transaction details from API
    const transaction = await apiClient.getTransactionDetails(transactionId);
    
    LoadingSpinner.hide();
    
    // Format type badge
    let typeBadge = '';
    switch (transaction.type) {
      case 'deposit':
        typeBadge = '<span class="badge badge-success">Deposit</span>';
        break;
      case 'verify':
        typeBadge = '<span class="badge badge-primary">Verification</span>';
        break;
      case 'shop':
        typeBadge = '<span class="badge badge-info">Shop Purchase</span>';
        break;
      case 'vip_purchase':
        typeBadge = '<span class="badge badge-vip">VIP Purchase</span>';
        break;
      case 'refund':
        typeBadge = '<span class="badge badge-warning">Refund</span>';
        break;
      default:
        typeBadge = `<span class="badge badge-default">${escapeHTML(transaction.type)}</span>`;
    }
    
    // Format status badge
    let statusBadge = '';
    switch (transaction.status) {
      case 'completed':
        statusBadge = '<span class="badge badge-success">Completed</span>';
        break;
      case 'pending':
        statusBadge = '<span class="badge badge-warning">Pending</span>';
        break;
      case 'failed':
        statusBadge = '<span class="badge badge-danger">Failed</span>';
        break;
      default:
        statusBadge = `<span class="badge badge-default">${escapeHTML(transaction.status)}</span>`;
    }
    
    // Format amount with currency
    const amount = formatCurrency(transaction.amount || 0, transaction.currency || 'USD');
    
    // Format created date
    const createdAt = formatDate(transaction.createdAt, 'YYYY-MM-DD HH:mm:ss');
    
    // Format metadata
    let metadataHTML = '';
    if (transaction.metadata && Object.keys(transaction.metadata).length > 0) {
      const metadataEntries = Object.entries(transaction.metadata)
        .map(([key, value]) => `
          <div class="info-item">
            <label>${escapeHTML(key)}:</label>
            <span>${escapeHTML(String(value))}</span>
          </div>
        `).join('');
      
      metadataHTML = `
        <div class="transaction-metadata">
          <h3>Additional Information</h3>
          <div class="user-info-grid">
            ${metadataEntries}
          </div>
        </div>
      `;
    }
    
    // Create modal content
    const content = `
      <div class="transaction-details">
        <div class="user-info-grid">
          <div class="info-item">
            <label>Transaction ID:</label>
            <span>${escapeHTML(String(transaction.id))}</span>
          </div>
          <div class="info-item">
            <label>User ID:</label>
            <span>${escapeHTML(String(transaction.userId))}</span>
          </div>
          <div class="info-item">
            <label>Username:</label>
            <span>${escapeHTML(transaction.username || 'N/A')}</span>
          </div>
          <div class="info-item">
            <label>Type:</label>
            <span>${typeBadge}</span>
          </div>
          <div class="info-item">
            <label>Amount:</label>
            <span>${amount}</span>
          </div>
          <div class="info-item">
            <label>Currency:</label>
            <span>${escapeHTML(transaction.currency || 'USD')}</span>
          </div>
          <div class="info-item">
            <label>Status:</label>
            <span>${statusBadge}</span>
          </div>
          <div class="info-item">
            <label>Description:</label>
            <span>${escapeHTML(transaction.description || 'N/A')}</span>
          </div>
          <div class="info-item">
            <label>Created:</label>
            <span>${createdAt}</span>
          </div>
        </div>
        
        ${metadataHTML}
      </div>
    `;
    
    // Show modal
    const modal = new Modal(`Transaction Details - ${transaction.id}`, content, {
      width: '800px'
    });
    modal.show();
    
  } catch (error) {
    LoadingSpinner.hide();
    Notification.error(`Failed to load transaction details: ${error.message}`);
  }
}

/**
 * Handle CSV export of transactions
 * @param {object} filters - Current filter options
 * Requirements: 4.4, 12.1, 12.2, 12.3, 12.4, 12.5
 */
async function handleExportCSV(filters = {}) {
  try {
    LoadingSpinner.show();
    
    // Fetch all transactions with current filters (no pagination)
    const exportFilters = {
      ...filters,
      export: true // Signal to API to return all results
    };
    
    const data = await apiClient.exportTransactions(exportFilters);
    
    // Check if data exceeds 10,000 rows (Requirement 12.5)
    if (data.transactions && data.transactions.length > 10000) {
      const confirmed = await ConfirmDialog.show(
        `This export contains ${data.transactions.length.toLocaleString()} rows, which may result in a large file. Do you want to continue?`,
        {
          title: 'Large Export Warning',
          confirmText: 'Continue Export',
          confirmClass: 'btn-warning'
        }
      );
      
      if (!confirmed) {
        LoadingSpinner.hide();
        return;
      }
    }
    
    // Generate CSV
    const csvString = generateCSV(data.transactions || []);
    
    // Download CSV
    const filename = `transactions_${formatDate(new Date(), 'YYYY-MM-DD_HHmmss')}.csv`;
    downloadCSV(csvString, filename);
    
    LoadingSpinner.hide();
    Notification.success(`Exported ${data.transactions.length} transactions successfully`);
    
  } catch (error) {
    LoadingSpinner.hide();
    Notification.error(`Failed to export transactions: ${error.message}`);
  }
}

/**
 * Generate CSV string from transaction data
 * @param {Array} transactions - Array of transaction objects
 * @returns {string} CSV string
 * Requirements: 12.1, 12.2, 12.3
 */
function generateCSV(transactions) {
  if (!transactions || transactions.length === 0) {
    return 'No data to export';
  }
  
  // Define CSV headers (Requirement 12.3)
  const headers = [
    'Transaction ID',
    'User ID',
    'Username',
    'Type',
    'Amount',
    'Currency',
    'Status',
    'Description',
    'Created At'
  ];
  
  // Helper function to escape CSV values
  const escapeCSV = (value) => {
    if (value === null || value === undefined) {
      return '';
    }
    
    const stringValue = String(value);
    
    // If value contains comma, quote, or newline, wrap in quotes and escape quotes
    if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
      return `"${stringValue.replace(/"/g, '""')}"`;
    }
    
    return stringValue;
  };
  
  // Build CSV rows
  const rows = [headers.join(',')];
  
  transactions.forEach(transaction => {
    const row = [
      escapeCSV(transaction.id),
      escapeCSV(transaction.userId),
      escapeCSV(transaction.username),
      escapeCSV(transaction.type),
      escapeCSV(transaction.amount),
      escapeCSV(transaction.currency || 'USD'),
      escapeCSV(transaction.status),
      escapeCSV(transaction.description),
      escapeCSV(formatDate(transaction.createdAt, 'YYYY-MM-DD HH:mm:ss'))
    ];
    
    rows.push(row.join(','));
  });
  
  return rows.join('\n');
}

/**
 * Download CSV file
 * @param {string} csvString - CSV content
 * @param {string} filename - Filename for download
 * Requirements: 12.4
 */
function downloadCSV(csvString, filename) {
  // Create blob with CSV content
  const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
  
  // Create download link
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  
  // Append to body, click, and remove
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  // Clean up URL object
  URL.revokeObjectURL(url);
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

// Export functions for global access
if (typeof window !== 'undefined') {
  window.initTransactionManagement = initTransactionManagement;
  window.fetchTransactions = fetchTransactions;
  window.renderTransactionList = renderTransactionList;
  window.setupTransactionFilters = setupTransactionFilters;
  window.showTransactionDetails = showTransactionDetails;
  window.handleExportCSV = handleExportCSV;
  window.generateCSV = generateCSV;
  window.downloadCSV = downloadCSV;
  window.loadTransactions = loadTransactions;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    initTransactionManagement,
    fetchTransactions,
    renderTransactionList,
    setupTransactionFilters,
    showTransactionDetails,
    handleExportCSV,
    generateCSV,
    downloadCSV,
    loadTransactions
  };
}
