/**
 * Job Management Module
 * Handles job-related operations including listing, filtering, viewing details, retry, and deletion
 * Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
 */

// Module state
let apiClient = null;
let currentPage = 1;
let currentFilters = {};

/**
 * Initialize the job management module
 * @param {APIClient} api - API client instance
 */
function initJobManagement(api) {
  apiClient = api;
  setupJobFilters();
  
  // Load initial job list
  loadJobs();
}

/**
 * Fetch jobs from API with pagination and filters
 * @param {number} page - Page number (1-indexed)
 * @param {object} filters - Filter options (status, startDate, endDate, etc.)
 * @returns {Promise<object>} Job list data
 * Requirements: 3.1, 3.2
 */
async function fetchJobs(page = 1, filters = {}) {
  try {
    LoadingSpinner.show('#job-list-container');
    
    // Build filter parameters
    const params = {
      page,
      pageSize: 50, // Requirement 3.1: 50 jobs per page
      ...filters
    };
    
    // Remove empty filters
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key];
      }
    });
    
    const data = await apiClient.getJobs(page, params);
    
    return data;
  } catch (error) {
    Notification.error(`Failed to load jobs: ${error.message}`);
    throw error;
  } finally {
    LoadingSpinner.hide();
  }
}

/**
 * Render job list in the table
 * @param {Array} jobs - Array of job objects
 * Requirements: 3.1, 3.3
 */
function renderJobList(jobs) {
  const tbody = document.getElementById('job-table-body');
  
  if (!tbody) {
    console.error('Job table body element not found');
    return;
  }
  
  // Clear existing rows
  tbody.innerHTML = '';
  
  // Handle empty list
  if (!jobs || jobs.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="empty-state">
          <i class="fas fa-tasks"></i>
          <p>No jobs found</p>
        </td>
      </tr>
    `;
    return;
  }
  
  // Render job rows
  jobs.forEach(job => {
    const row = document.createElement('tr');
    row.dataset.jobId = job.id;
    
    // Format status badge
    let statusBadge = '';
    switch (job.status) {
      case 'pending':
        statusBadge = '<span class="badge badge-warning">Pending</span>';
        break;
      case 'completed':
        statusBadge = '<span class="badge badge-success">Completed</span>';
        break;
      case 'failed':
        statusBadge = '<span class="badge badge-danger">Failed</span>';
        break;
      case 'cancelled':
        statusBadge = '<span class="badge badge-secondary">Cancelled</span>';
        break;
      default:
        statusBadge = `<span class="badge badge-default">${escapeHTML(job.status)}</span>`;
    }
    
    // Format created date
    const createdAt = formatDate(job.createdAt, 'YYYY-MM-DD HH:mm');
    
    row.innerHTML = `
      <td data-label="Job ID">${escapeHTML(String(job.id))}</td>
      <td data-label="User">${escapeHTML(job.username || 'N/A')}</td>
      <td data-label="Type">${escapeHTML(job.type || 'N/A')}</td>
      <td data-label="Status">${statusBadge}</td>
      <td data-label="Created">${createdAt}</td>
      <td class="actions" data-label="Actions">
        <button class="btn btn-sm btn-primary" onclick="showJobDetails('${escapeHTML(String(job.id))}')" title="View Details">
          <i class="fas fa-eye"></i>
        </button>
        ${job.status === 'failed' ? `
          <button class="btn btn-sm btn-warning" onclick="handleRetryJob('${escapeHTML(String(job.id))}')" title="Retry Job">
            <i class="fas fa-redo"></i>
          </button>
        ` : ''}
        <button class="btn btn-sm btn-danger" onclick="handleDeleteJob('${escapeHTML(String(job.id))}')" title="Delete Job">
          <i class="fas fa-trash"></i>
        </button>
      </td>
    `;
    
    tbody.appendChild(row);
  });
}

/**
 * Setup job filters for status and date filtering
 * Requirements: 3.2 (status filtering)
 */
function setupJobFilters() {
  const statusFilter = document.getElementById('job-status-filter');
  const startDateFilter = document.getElementById('job-start-date');
  const endDateFilter = document.getElementById('job-end-date');
  const clearFiltersBtn = document.getElementById('clear-job-filters');
  
  // Status filter
  if (statusFilter) {
    statusFilter.addEventListener('change', (e) => {
      const status = e.target.value;
      
      if (status === 'all') {
        delete currentFilters.status;
      } else {
        currentFilters.status = status;
      }
      
      currentPage = 1; // Reset to first page on filter change
      loadJobs();
    });
  } else {
    console.warn('Job status filter not found');
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
      loadJobs();
    });
  } else {
    console.warn('Job start date filter not found');
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
      loadJobs();
    });
  } else {
    console.warn('Job end date filter not found');
  }
  
  // Clear filters button
  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener('click', () => {
      // Reset all filters
      currentFilters = {};
      currentPage = 1;
      
      // Reset filter UI elements
      if (statusFilter) statusFilter.value = 'all';
      if (startDateFilter) startDateFilter.value = '';
      if (endDateFilter) endDateFilter.value = '';
      
      // Reload jobs
      loadJobs();
    });
  } else {
    console.warn('Clear job filters button not found');
  }
}

/**
 * Load jobs with current page and filters
 */
async function loadJobs() {
  try {
    const data = await fetchJobs(currentPage, currentFilters);
    
    // Render job list
    renderJobList(data.jobs || []);
    
    // Update pagination
    updateJobPagination(data.total || 0, data.pageSize || 50);
  } catch (error) {
    console.error('Failed to load jobs:', error);
  }
}

/**
 * Update pagination controls
 * @param {number} total - Total number of jobs
 * @param {number} pageSize - Number of jobs per page
 */
function updateJobPagination(total, pageSize) {
  const paginationContainer = document.getElementById('job-pagination');
  
  if (!paginationContainer) {
    console.warn('Job pagination container not found');
    return;
  }
  
  const totalPages = Math.ceil(total / pageSize);
  
  // Create or update pagination component
  if (!window.jobPagination) {
    window.jobPagination = new Pagination(paginationContainer, {
      totalPages,
      currentPage
    });
    
    window.jobPagination.onPageChange((page) => {
      currentPage = page;
      loadJobs();
    });
  } else {
    window.jobPagination.setTotalPages(totalPages);
    window.jobPagination.setCurrentPage(currentPage);
  }
  
  window.jobPagination.render();
}

/**
 * Show job details in a modal
 * @param {string} jobId - Job ID
 * Requirements: 3.3
 */
async function showJobDetails(jobId) {
  try {
    LoadingSpinner.show();
    
    // Fetch job details from API
    const job = await apiClient.getJobDetails(jobId);
    
    LoadingSpinner.hide();
    
    // Format status badge
    let statusBadge = '';
    switch (job.status) {
      case 'pending':
        statusBadge = '<span class="badge badge-warning">Pending</span>';
        break;
      case 'completed':
        statusBadge = '<span class="badge badge-success">Completed</span>';
        break;
      case 'failed':
        statusBadge = '<span class="badge badge-danger">Failed</span>';
        break;
      case 'cancelled':
        statusBadge = '<span class="badge badge-secondary">Cancelled</span>';
        break;
      default:
        statusBadge = `<span class="badge badge-default">${escapeHTML(job.status)}</span>`;
    }
    
    // Format dates
    const createdAt = formatDate(job.createdAt, 'YYYY-MM-DD HH:mm:ss');
    const completedAt = job.completedAt 
      ? formatDate(job.completedAt, 'YYYY-MM-DD HH:mm:ss')
      : 'N/A';
    
    // Format error message
    const errorMessage = job.errorMessage 
      ? `<div class="error-message">
          <strong>Error:</strong>
          <pre>${escapeHTML(job.errorMessage)}</pre>
        </div>`
      : '';
    
    // Format metadata
    let metadataHTML = '';
    if (job.metadata && Object.keys(job.metadata).length > 0) {
      const metadataEntries = Object.entries(job.metadata)
        .map(([key, value]) => `
          <div class="info-item">
            <label>${escapeHTML(key)}:</label>
            <span>${escapeHTML(String(value))}</span>
          </div>
        `).join('');
      
      metadataHTML = `
        <div class="job-metadata">
          <h3>Additional Information</h3>
          <div class="user-info-grid">
            ${metadataEntries}
          </div>
        </div>
      `;
    }
    
    // Create modal content
    const content = `
      <div class="job-details">
        <div class="user-info-grid">
          <div class="info-item">
            <label>Job ID:</label>
            <span>${escapeHTML(String(job.id))}</span>
          </div>
          <div class="info-item">
            <label>User ID:</label>
            <span>${escapeHTML(String(job.userId))}</span>
          </div>
          <div class="info-item">
            <label>Username:</label>
            <span>${escapeHTML(job.username || 'N/A')}</span>
          </div>
          <div class="info-item">
            <label>Type:</label>
            <span>${escapeHTML(job.type || 'N/A')}</span>
          </div>
          <div class="info-item">
            <label>Status:</label>
            <span>${statusBadge}</span>
          </div>
          <div class="info-item">
            <label>Email:</label>
            <span>${escapeHTML(job.email || 'N/A')}</span>
          </div>
          <div class="info-item">
            <label>First Name:</label>
            <span>${escapeHTML(job.firstName || 'N/A')}</span>
          </div>
          <div class="info-item">
            <label>Last Name:</label>
            <span>${escapeHTML(job.lastName || 'N/A')}</span>
          </div>
          <div class="info-item">
            <label>Organization:</label>
            <span>${escapeHTML(job.organization || 'N/A')}</span>
          </div>
          <div class="info-item">
            <label>Created:</label>
            <span>${createdAt}</span>
          </div>
          <div class="info-item">
            <label>Completed:</label>
            <span>${completedAt}</span>
          </div>
          <div class="info-item">
            <label>Retry Count:</label>
            <span>${job.retryCount || 0}</span>
          </div>
        </div>
        
        ${errorMessage}
        ${metadataHTML}
        
        <div class="user-actions-buttons">
          ${job.status === 'failed' ? `
            <button class="btn btn-warning" onclick="handleRetryJob('${escapeHTML(String(job.id))}')">
              <i class="fas fa-redo"></i> Retry Job
            </button>
          ` : ''}
          <button class="btn btn-danger" onclick="handleDeleteJob('${escapeHTML(String(job.id))}')">
            <i class="fas fa-trash"></i> Delete Job
          </button>
        </div>
      </div>
    `;
    
    // Show modal
    const modal = new Modal(`Job Details - ${job.id}`, content, {
      width: '800px'
    });
    modal.show();
    
  } catch (error) {
    LoadingSpinner.hide();
    Notification.error(`Failed to load job details: ${error.message}`);
  }
}

/**
 * Handle retrying a failed job
 * @param {string} jobId - Job ID
 * Requirements: 3.4
 */
async function handleRetryJob(jobId) {
  const confirmed = await ConfirmDialog.show(
    'Are you sure you want to retry this job? This will resubmit the verification request.',
    {
      title: 'Retry Job',
      confirmText: 'Retry',
      confirmClass: 'btn-warning'
    }
  );
  
  if (!confirmed) {
    return;
  }
  
  try {
    LoadingSpinner.show();
    
    await apiClient.retryJob(jobId);
    
    LoadingSpinner.hide();
    Notification.success('Job retry initiated successfully');
    
    // Close modal if open
    closeCurrentModal();
    
    // Reload jobs list
    loadJobs();
  } catch (error) {
    LoadingSpinner.hide();
    Notification.error(`Failed to retry job: ${error.message}`);
  }
}

/**
 * Handle deleting a job
 * @param {string} jobId - Job ID
 * Requirements: 3.5
 */
async function handleDeleteJob(jobId) {
  const confirmed = await ConfirmDialog.show(
    'Are you sure you want to delete this job? This action cannot be undone.',
    {
      title: 'Delete Job',
      confirmText: 'Delete',
      confirmClass: 'btn-danger'
    }
  );
  
  if (!confirmed) {
    return;
  }
  
  try {
    LoadingSpinner.show();
    
    await apiClient.deleteJob(jobId);
    
    LoadingSpinner.hide();
    Notification.success('Job deleted successfully');
    
    // Close modal if open
    closeCurrentModal();
    
    // Reload jobs list
    loadJobs();
  } catch (error) {
    LoadingSpinner.hide();
    Notification.error(`Failed to delete job: ${error.message}`);
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

// Export functions for global access
if (typeof window !== 'undefined') {
  window.initJobManagement = initJobManagement;
  window.fetchJobs = fetchJobs;
  window.renderJobList = renderJobList;
  window.setupJobFilters = setupJobFilters;
  window.showJobDetails = showJobDetails;
  window.handleRetryJob = handleRetryJob;
  window.handleDeleteJob = handleDeleteJob;
  window.loadJobs = loadJobs;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    initJobManagement,
    fetchJobs,
    renderJobList,
    setupJobFilters,
    showJobDetails,
    handleRetryJob,
    handleDeleteJob,
    loadJobs
  };
}
