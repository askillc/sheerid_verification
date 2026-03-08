/**
 * Authentication Module
 * Handles JWT token management, login/logout, and authentication state
 * Requirements: 8.1, 8.2, 8.4, 8.5
 */

class AuthManager {
  constructor() {
    this.tokenKey = 'admin_jwt_token';
    this.userKey = 'admin_user';
    this.tokenExpirationCallbacks = [];
  }

  /**
   * Authenticate user with username and password
   * @param {string} username - Admin username
   * @param {string} password - Admin password
   * @returns {Promise<{token: string, user: object}>} Authentication result
   * @throws {Error} If authentication fails
   */
  async login(username, password) {
    try {
      const response = await fetch('/api/admin/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Invalid username or password');
        } else if (response.status === 403) {
          throw new Error('Access denied');
        } else {
          throw new Error('Login failed. Please try again.');
        }
      }

      const data = await response.json();
      
      if (!data.token) {
        throw new Error('Invalid response from server');
      }

      // Store token and user data in localStorage (Requirement 8.4)
      localStorage.setItem(this.tokenKey, data.token);
      if (data.user) {
        localStorage.setItem(this.userKey, JSON.stringify(data.user));
      }

      return data;
    } catch (error) {
      // Re-throw with appropriate error message
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Unable to connect to server. Please check your internet connection.');
      }
      throw error;
    }
  }

  /**
   * Log out the current user
   * Clears stored token and redirects to login page
   * Requirements: 8.5
   */
  logout() {
    // Clear token and user data from localStorage (Requirement 8.5)
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);

    // Trigger token expiration callbacks
    this.tokenExpirationCallbacks.forEach(callback => {
      try {
        callback();
      } catch (error) {
        console.error('Error in token expiration callback:', error);
      }
    });

    // Reload current page to show login form
    window.location.reload();
  }

  /**
   * Get the stored JWT token
   * @returns {string|null} JWT token or null if not authenticated
   */
  getToken() {
    return localStorage.getItem(this.tokenKey);
  }

  /**
   * Check if user is authenticated
   * @returns {boolean} True if valid token exists
   */
  isAuthenticated() {
    const token = this.getToken();
    
    if (!token) {
      return false;
    }

    // Basic validation: check if token is not empty
    // More sophisticated validation (JWT expiration check) could be added here
    return token.length > 0;
  }

  /**
   * Get stored user data
   * @returns {object|null} User object or null if not available
   */
  getUser() {
    const userJson = localStorage.getItem(this.userKey);
    if (!userJson) {
      return null;
    }

    try {
      return JSON.parse(userJson);
    } catch (error) {
      console.error('Error parsing user data:', error);
      return null;
    }
  }

  /**
   * Register a callback to be called when token expires
   * @param {Function} callback - Function to call on token expiration
   */
  onTokenExpired(callback) {
    if (typeof callback === 'function') {
      this.tokenExpirationCallbacks.push(callback);
    }
  }

  /**
   * Refresh the JWT token
   * @returns {Promise<string>} New JWT token
   * @throws {Error} If refresh fails
   */
  async refreshToken() {
    const currentToken = this.getToken();
    
    if (!currentToken) {
      throw new Error('No token to refresh');
    }

    try {
      const response = await fetch('/api/admin/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${currentToken}`
        }
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Token is invalid or expired, logout
          this.logout();
          throw new Error('Session expired. Please login again.');
        }
        throw new Error('Failed to refresh token');
      }

      const data = await response.json();
      
      if (!data.token) {
        throw new Error('Invalid response from server');
      }

      // Update stored token
      localStorage.setItem(this.tokenKey, data.token);

      return data.token;
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Unable to connect to server. Please check your internet connection.');
      }
      throw error;
    }
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AuthManager;
}
