/**
 * API Client Module
 * Centralized HTTP communication with error handling and JWT authentication
 * Requirements: 8.1, 8.2, 8.3, 9.1, 9.6
 */

class APIClient {
  /**
   * Create an API client instance
   * @param {string} baseURL - Base URL for API endpoints
   * @param {AuthManager} authManager - Authentication manager instance
   */
  constructor(baseURL, authManager) {
    this.baseURL = baseURL || '/api';
    this.authManager = authManager;
    this.timeout = 30000; // 30 seconds timeout
    this.cache = new Map(); // Cache for API responses
    this.cacheExpiration = 5 * 60 * 1000; // 5 minutes in milliseconds
  }

  /**
   * Get authorization headers with JWT token
   * @returns {object} Headers object with Authorization
   * @private
   */
  _getAuthHeaders() {
    const token = this.authManager.getToken();
    const headers = {
      'Content-Type': 'application/json'
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  /**
   * Create a fetch request with timeout
   * @param {string} url - Request URL
   * @param {object} options - Fetch options
   * @returns {Promise<Response>} Fetch response
   * @private
   */
  async _fetchWithTimeout(url, options) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('Request timeout. Please try again.');
      }
      throw error;
    }
  }

  /**
   * Handle API errors and display appropriate messages
   * @param {Error} error - Error object
   * @param {Response} response - Fetch response (if available)
   * @throws {Error} Processed error
   * @private
   */
  async _handleError(error, response) {
    // Network error (no response)
    if (!response) {
      if (error.message.includes('timeout')) {
        throw new Error('Request timeout. Please try again.');
      }
      throw new Error('Unable to connect to server. Please check your internet connection.');
    }

    // Handle HTTP status codes
    switch (response.status) {
      case 401:
        // Unauthorized - trigger logout and redirect
        this.authManager.logout();
        throw new Error('Session expired. Please login again.');

      case 403:
        throw new Error('You do not have permission to perform this action.');

      case 404:
        throw new Error('The requested resource was not found.');

      case 422:
        // Validation error - extract field errors
        try {
          const data = await response.json();
          if (data.errors) {
            const errorMessages = Object.entries(data.errors)
              .map(([field, messages]) => `${field}: ${messages.join(', ')}`)
              .join('\n');
            throw new Error(errorMessages);
          }
          throw new Error(data.message || 'Validation failed.');
        } catch (parseError) {
          throw new Error('Validation failed.');
        }

      case 500:
      case 502:
      case 503:
        throw new Error('Server error occurred. Please try again later.');

      default:
        // Try to extract error message from response
        try {
          const data = await response.json();
          throw new Error(data.message || data.error || 'An unexpected error occurred.');
        } catch (parseError) {
          throw new Error('An unexpected error occurred.');
        }
    }
  }

  /**
   * Parse API response
   * @param {Response} response - Fetch response
   * @returns {Promise<any>} Parsed response data
   * @private
   */
  async _parseResponse(response) {
    const contentType = response.headers.get('content-type');
    
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }
    
    return await response.text();
  }

  /**
   * Get cache key for request
   * @param {string} endpoint - API endpoint
   * @param {object} params - Query parameters
   * @returns {string} Cache key
   * @private
   */
  _getCacheKey(endpoint, params) {
    const paramString = params ? JSON.stringify(params) : '';
    return `${endpoint}:${paramString}`;
  }

  /**
   * Get cached response if available and not expired
   * @param {string} cacheKey - Cache key
   * @returns {any|null} Cached data or null
   * @private
   */
  _getCachedResponse(cacheKey) {
    const cached = this.cache.get(cacheKey);
    
    if (!cached) {
      return null;
    }

    const now = Date.now();
    if (now - cached.timestamp > this.cacheExpiration) {
      // Cache expired
      this.cache.delete(cacheKey);
      return null;
    }

    return cached.data;
  }

  /**
   * Store response in cache
   * @param {string} cacheKey - Cache key
   * @param {any} data - Data to cache
   * @private
   */
  _setCachedResponse(cacheKey, data) {
    this.cache.set(cacheKey, {
      data,
      timestamp: Date.now()
    });
  }

  /**
   * Clear cache (e.g., after mutations)
   * @param {string} pattern - Optional pattern to match cache keys
   */
  clearCache(pattern) {
    if (!pattern) {
      this.cache.clear();
      return;
    }

    // Clear cache entries matching pattern
    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        this.cache.delete(key);
      }
    }
  }

  /**
   * Make GET request
   * @param {string} endpoint - API endpoint
   * @param {object} params - Query parameters
   * @param {object} options - Additional options (useCache, etc.)
   * @returns {Promise<any>} Response data
   */
  async get(endpoint, params = null, options = {}) {
    const { useCache = false } = options;
    
    // Check cache if enabled
    if (useCache) {
      const cacheKey = this._getCacheKey(endpoint, params);
      const cached = this._getCachedResponse(cacheKey);
      if (cached) {
        return cached;
      }
    }

    // Build URL with query parameters
    let url = `${this.baseURL}${endpoint}`;
    if (params) {
      const queryString = new URLSearchParams(params).toString();
      url += `?${queryString}`;
    }

    try {
      const response = await this._fetchWithTimeout(url, {
        method: 'GET',
        headers: this._getAuthHeaders()
      });

      if (!response.ok) {
        await this._handleError(null, response);
      }

      const data = await this._parseResponse(response);

      // Cache response if enabled
      if (useCache) {
        const cacheKey = this._getCacheKey(endpoint, params);
        this._setCachedResponse(cacheKey, data);
      }

      return data;
    } catch (error) {
      if (error.message.includes('fetch')) {
        await this._handleError(error, null);
      }
      throw error;
    }
  }

  /**
   * Make POST request
   * @param {string} endpoint - API endpoint
   * @param {object} data - Request body data
   * @returns {Promise<any>} Response data
   */
  async post(endpoint, data = null) {
    const url = `${this.baseURL}${endpoint}`;

    try {
      const response = await this._fetchWithTimeout(url, {
        method: 'POST',
        headers: this._getAuthHeaders(),
        body: data ? JSON.stringify(data) : null
      });

      if (!response.ok) {
        await this._handleError(null, response);
      }

      return await this._parseResponse(response);
    } catch (error) {
      if (error.message.includes('fetch')) {
        await this._handleError(error, null);
      }
      throw error;
    }
  }

  /**
   * Make PUT request
   * @param {string} endpoint - API endpoint
   * @param {object} data - Request body data
   * @returns {Promise<any>} Response data
   */
  async put(endpoint, data = null) {
    const url = `${this.baseURL}${endpoint}`;

    try {
      const response = await this._fetchWithTimeout(url, {
        method: 'PUT',
        headers: this._getAuthHeaders(),
        body: data ? JSON.stringify(data) : null
      });

      if (!response.ok) {
        await this._handleError(null, response);
      }

      return await this._parseResponse(response);
    } catch (error) {
      if (error.message.includes('fetch')) {
        await this._handleError(error, null);
      }
      throw error;
    }
  }

  /**
   * Make DELETE request
   * @param {string} endpoint - API endpoint
   * @returns {Promise<any>} Response data
   */
  async delete(endpoint) {
    const url = `${this.baseURL}${endpoint}`;

    try {
      const response = await this._fetchWithTimeout(url, {
        method: 'DELETE',
        headers: this._getAuthHeaders()
      });

      if (!response.ok) {
        await this._handleError(null, response);
      }

      return await this._parseResponse(response);
    } catch (error) {
      if (error.message.includes('fetch')) {
        await this._handleError(error, null);
      }
      throw error;
    }
  }

  // ============================================================================
  // User Management API Methods
  // Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9
  // ============================================================================

  /**
   * Get paginated list of users with optional filters
   * @param {number} page - Page number (1-indexed)
   * @param {object} filters - Filter options (status, search, etc.)
   * @returns {Promise<{users: Array, total: number, page: number, pageSize: number}>}
   */
  async getUsers(page = 1, filters = {}) {
    const params = {
      page,
      ...filters
    };

    const data = await this.get('/admin/users', params);
    return data;
  }

  /**
   * Get detailed information for a specific user
   * @param {number} userId - User ID
   * @returns {Promise<object>} User details
   */
  async getUserDetails(userId) {
    const data = await this.get(`/admin/users/${userId}`);
    return data;
  }

  /**
   * Update user's coin balance
   * @param {number} userId - User ID
   * @param {number} amount - Amount to add (positive) or subtract (negative)
   * @returns {Promise<object>} Updated user data
   */
  async updateUserCoins(userId, amount) {
    const data = await this.post(`/admin/users/${userId}/coins`, { amount });
    
    // Clear user cache after mutation
    this.clearCache('/admin/users');
    
    return data;
  }

  /**
   * Update user's cash balance
   * @param {number} userId - User ID
   * @param {number} amount - Amount to add (positive) or subtract (negative)
   * @returns {Promise<object>} Updated user data
   */
  async updateUserCash(userId, amount) {
    const data = await this.post(`/admin/users/${userId}/cash`, { amount });
    
    // Clear user cache after mutation
    this.clearCache('/admin/users');
    
    return data;
  }

  /**
   * Set or update user's VIP status
   * @param {number} userId - User ID
   * @param {string} tier - VIP tier ('basic', 'pro', 'business', or 'none')
   * @param {number} duration - Duration in days (optional, for new VIP grants)
   * @returns {Promise<object>} Updated user data
   */
  async setUserVIP(userId, tier, duration = null) {
    const data = await this.post(`/admin/users/${userId}/vip`, { 
      tier,
      duration 
    });
    
    // Clear user cache after mutation
    this.clearCache('/admin/users');
    
    return data;
  }

  /**
   * Block a user account
   * @param {number} userId - User ID
   * @param {string} reason - Reason for blocking
   * @returns {Promise<object>} Updated user data
   */
  async blockUser(userId, reason) {
    const data = await this.post(`/admin/users/${userId}/block`, { reason });
    
    // Clear user cache after mutation
    this.clearCache('/admin/users');
    
    return data;
  }

  /**
   * Unblock a user account
   * @param {number} userId - User ID
   * @returns {Promise<object>} Updated user data
   */
  async unblockUser(userId) {
    const data = await this.post(`/admin/users/${userId}/unblock`);
    
    // Clear user cache after mutation
    this.clearCache('/admin/users');
    
    return data;
  }

  /**
   * Send a direct message to a user
   * @param {number} userId - User ID
   * @param {string} message - Message text
   * @returns {Promise<void>}
   */
  async sendMessage(userId, message) {
    await this.post(`/admin/users/${userId}/message`, { message });
  }

  /**
   * Set daily verification limit for a user
   * @param {number} userId - User ID
   * @param {number} limit - Daily verification limit
   * @returns {Promise<object>} Updated user data
   */
  async setUserLimit(userId, limit) {
    const data = await this.post(`/admin/users/${userId}/limit`, { limit });
    
    // Clear user cache after mutation
    this.clearCache('/admin/users');
    
    return data;
  }

  // ============================================================================
  // Job Management API Methods
  // Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
  // ============================================================================

  /**
   * Get paginated list of jobs with optional filters
   * @param {number} page - Page number (1-indexed)
   * @param {object} filters - Filter options (status, startDate, endDate, etc.)
   * @returns {Promise<{jobs: Array, total: number, page: number, pageSize: number}>}
   */
  async getJobs(page = 1, filters = {}) {
    const params = {
      page,
      ...filters
    };

    const data = await this.get('/admin/jobs', params);
    return data;
  }

  /**
   * Get detailed information for a specific job
   * @param {string} jobId - Job ID
   * @returns {Promise<object>} Job details
   */
  async getJobDetails(jobId) {
    const data = await this.get(`/admin/jobs/${jobId}`);
    return data;
  }

  /**
   * Retry a failed job
   * @param {string} jobId - Job ID
   * @returns {Promise<object>} Updated job data
   */
  async retryJob(jobId) {
    const data = await this.post(`/admin/jobs/${jobId}/retry`);
    
    // Clear job cache after mutation
    this.clearCache('/admin/jobs');
    
    return data;
  }

  /**
   * Delete a job
   * @param {string} jobId - Job ID
   * @returns {Promise<void>}
   */
  async deleteJob(jobId) {
    await this.delete(`/admin/jobs/${jobId}`);
    
    // Clear job cache after mutation
    this.clearCache('/admin/jobs');
  }

  // ============================================================================
  // Transaction Management API Methods
  // Requirements: 4.1, 4.2, 4.3, 4.4
  // ============================================================================

  /**
   * Get paginated list of transactions with optional filters
   * @param {number} page - Page number (1-indexed)
   * @param {object} filters - Filter options (type, startDate, endDate, etc.)
   * @returns {Promise<{transactions: Array, total: number, page: number, pageSize: number}>}
   */
  async getTransactions(page = 1, filters = {}) {
    const params = {
      page,
      ...filters
    };

    const data = await this.get('/admin/transactions', params);
    return data;
  }

  /**
   * Get detailed information for a specific transaction
   * @param {string} transactionId - Transaction ID
   * @returns {Promise<object>} Transaction details
   */
  async getTransactionDetails(transactionId) {
    const data = await this.get(`/admin/transactions/${transactionId}`);
    return data;
  }

  /**
   * Export transactions to CSV format
   * @param {object} filters - Filter options (type, startDate, endDate, etc.)
   * @returns {Promise<Blob>} CSV file as Blob
   */
  async exportTransactions(filters = {}) {
    const params = {
      format: 'csv',
      ...filters
    };

    const url = `${this.baseURL}/admin/transactions/export`;
    const queryString = new URLSearchParams(params).toString();
    const fullUrl = `${url}?${queryString}`;

    try {
      const response = await this._fetchWithTimeout(fullUrl, {
        method: 'GET',
        headers: this._getAuthHeaders()
      });

      if (!response.ok) {
        await this._handleError(null, response);
      }

      // Return response as Blob for CSV download
      return await response.blob();
    } catch (error) {
      if (error.message.includes('fetch')) {
        await this._handleError(error, null);
      }
      throw error;
    }
  }

  // ============================================================================
  // Statistics API Methods
  // Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7
  // ============================================================================

  /**
   * Get dashboard statistics
   * @returns {Promise<object>} Statistics data
   */
  async getStatistics() {
    const data = await this.get('/admin/stats', null, { useCache: true });
    return data;
  }

  // ============================================================================
  // Settings Management API Methods
  // Requirements: 5.1, 5.2, 5.7
  // ============================================================================

  /**
   * Get current system settings
   * @returns {Promise<object>} Settings data
   */
  async getSettings() {
    const data = await this.get('/admin/settings', null, { useCache: true });
    return data;
  }

  /**
   * Update system settings
   * @param {object} settings - Settings object to update
   * @returns {Promise<object>} Updated settings data
   */
  async updateSettings(settings) {
    const data = await this.put('/admin/settings', settings);
    
    // Clear settings cache after mutation
    this.clearCache('/admin/settings');
    
    return data;
  }

  /**
   * Set maintenance mode
   * @param {boolean} enabled - Enable or disable maintenance mode
   * @returns {Promise<void>}
   */
  async setMaintenanceMode(enabled) {
    await this.post('/admin/settings/maintenance', { enabled });
    
    // Clear settings cache after mutation
    this.clearCache('/admin/settings');
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = APIClient;
}
