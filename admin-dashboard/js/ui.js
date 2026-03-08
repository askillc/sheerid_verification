/**
 * UI Components Module
 * Provides reusable UI components for the admin dashboard
 * Requirements: 9.2, 9.3, 9.4, 9.5
 */

/**
 * Modal Component
 * Displays a modal dialog with customizable content
 */
class Modal {
  constructor(title, content, options = {}) {
    this.title = title;
    this.content = content;
    this.options = {
      closeOnOverlay: options.closeOnOverlay !== false,
      closeButton: options.closeButton !== false,
      width: options.width || '600px',
      ...options
    };
    this.element = null;
    this.closeCallback = null;
  }

  /**
   * Show the modal
   */
  show() {
    // Remove any existing modal
    this.hide();

    // Create modal structure
    this.element = document.createElement('div');
    this.element.className = 'modal-overlay';
    this.element.innerHTML = `
      <div class="modal-container" style="max-width: ${this.options.width}">
        <div class="modal-header">
          <h2 class="modal-title">${this.title}</h2>
          ${this.options.closeButton ? '<button class="modal-close" aria-label="Close">&times;</button>' : ''}
        </div>
        <div class="modal-body">
          ${this.content}
        </div>
      </div>
    `;

    // Add to DOM
    document.body.appendChild(this.element);
    document.body.style.overflow = 'hidden';

    // Add event listeners
    if (this.options.closeButton) {
      const closeBtn = this.element.querySelector('.modal-close');
      closeBtn.addEventListener('click', () => this.hide());
    }

    if (this.options.closeOnOverlay) {
      this.element.addEventListener('click', (e) => {
        if (e.target === this.element) {
          this.hide();
        }
      });
    }

    // Trigger animation
    requestAnimationFrame(() => {
      this.element.classList.add('modal-visible');
    });
  }

  /**
   * Hide the modal
   */
  hide() {
    if (this.element) {
      this.element.classList.remove('modal-visible');
      
      // Wait for animation to complete
      setTimeout(() => {
        if (this.element && this.element.parentNode) {
          this.element.parentNode.removeChild(this.element);
          document.body.style.overflow = '';
          
          // Call close callback if set
          if (this.closeCallback) {
            this.closeCallback();
          }
        }
      }, 300);
    }
  }

  /**
   * Update modal content
   * @param {string} html - New HTML content
   */
  setContent(html) {
    if (this.element) {
      const body = this.element.querySelector('.modal-body');
      if (body) {
        body.innerHTML = html;
      }
    }
  }

  /**
   * Register callback for when modal closes
   * @param {Function} callback - Function to call on close
   */
  onClose(callback) {
    this.closeCallback = callback;
  }
}

/**
 * Notification Component
 * Displays toast notifications with auto-dismiss
 */
class Notification {
  static container = null;
  static notifications = [];

  /**
   * Initialize notification container
   */
  static init() {
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.className = 'notification-container';
      document.body.appendChild(this.container);
    }
  }

  /**
   * Show a notification
   * @param {string} message - Notification message
   * @param {string} type - Notification type (success, error, info, warning)
   * @param {number|null} duration - Auto-dismiss duration in ms (null for manual dismiss)
   */
  static show(message, type = 'info', duration = 3000) {
    this.init();

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    
    // Add icon based on type
    const icons = {
      success: '✓',
      error: '✕',
      info: 'ℹ',
      warning: '⚠'
    };
    
    notification.innerHTML = `
      <span class="notification-icon">${icons[type] || icons.info}</span>
      <span class="notification-message">${message}</span>
      <button class="notification-close" aria-label="Close">&times;</button>
    `;

    // Add to container
    this.container.appendChild(notification);
    this.notifications.push(notification);

    // Trigger animation
    requestAnimationFrame(() => {
      notification.classList.add('notification-visible');
    });

    // Add close button handler
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
      this.dismiss(notification);
    });

    // Auto-dismiss if duration is set
    if (duration !== null && duration > 0) {
      setTimeout(() => {
        this.dismiss(notification);
      }, duration);
    }

    return notification;
  }

  /**
   * Dismiss a notification
   * @param {HTMLElement} notification - Notification element to dismiss
   */
  static dismiss(notification) {
    if (notification && notification.parentNode) {
      notification.classList.remove('notification-visible');
      
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
          
          // Remove from tracking array
          const index = this.notifications.indexOf(notification);
          if (index > -1) {
            this.notifications.splice(index, 1);
          }
        }
      }, 300);
    }
  }

  /**
   * Show success notification
   * @param {string} message - Success message
   * @param {number} duration - Auto-dismiss duration (default: 3000ms)
   */
  static success(message, duration = 3000) {
    return this.show(message, 'success', duration);
  }

  /**
   * Show error notification
   * @param {string} message - Error message
   * @param {number|null} duration - Auto-dismiss duration (default: null for manual dismiss)
   */
  static error(message, duration = null) {
    return this.show(message, 'error', duration);
  }

  /**
   * Show info notification
   * @param {string} message - Info message
   * @param {number} duration - Auto-dismiss duration (default: 3000ms)
   */
  static info(message, duration = 3000) {
    return this.show(message, 'info', duration);
  }

  /**
   * Show warning notification
   * @param {string} message - Warning message
   * @param {number} duration - Auto-dismiss duration (default: 5000ms)
   */
  static warning(message, duration = 5000) {
    return this.show(message, 'warning', duration);
  }

  /**
   * Clear all notifications
   */
  static clearAll() {
    this.notifications.forEach(notification => {
      this.dismiss(notification);
    });
  }
}

/**
 * Loading Spinner Component
 * Displays a loading indicator
 */
class LoadingSpinner {
  static spinner = null;

  /**
   * Show loading spinner
   * @param {string} target - CSS selector for target element (default: 'body')
   */
  static show(target = 'body') {
    // Remove existing spinner
    this.hide();

    // Create spinner element
    this.spinner = document.createElement('div');
    this.spinner.className = 'loading-spinner-overlay';
    this.spinner.innerHTML = `
      <div class="loading-spinner">
        <div class="spinner-circle"></div>
        <div class="spinner-text">Loading...</div>
      </div>
    `;

    // Add to target element
    const targetElement = typeof target === 'string' 
      ? document.querySelector(target) 
      : target;
    
    if (targetElement) {
      targetElement.appendChild(this.spinner);
      
      // Trigger animation
      requestAnimationFrame(() => {
        this.spinner.classList.add('spinner-visible');
      });
    }
  }

  /**
   * Hide loading spinner
   */
  static hide() {
    if (this.spinner) {
      this.spinner.classList.remove('spinner-visible');
      
      setTimeout(() => {
        if (this.spinner && this.spinner.parentNode) {
          this.spinner.parentNode.removeChild(this.spinner);
          this.spinner = null;
        }
      }, 300);
    }
  }
}

/**
 * Pagination Component
 * Handles pagination controls and page navigation
 */
class Pagination {
  constructor(container, options = {}) {
    this.container = typeof container === 'string' 
      ? document.querySelector(container) 
      : container;
    
    this.options = {
      totalPages: options.totalPages || 1,
      currentPage: options.currentPage || 1,
      maxButtons: options.maxButtons || 5,
      showFirstLast: options.showFirstLast !== false,
      showPrevNext: options.showPrevNext !== false,
      ...options
    };
    
    this.totalPages = this.options.totalPages;
    this.currentPage = this.options.currentPage;
    this.changeCallback = null;
  }

  /**
   * Set total number of pages
   * @param {number} total - Total page count
   */
  setTotalPages(total) {
    this.totalPages = Math.max(1, total);
    this.render();
  }

  /**
   * Set current page
   * @param {number} page - Page number
   */
  setCurrentPage(page) {
    this.currentPage = Math.max(1, Math.min(page, this.totalPages));
    this.render();
  }

  /**
   * Register callback for page changes
   * @param {Function} callback - Function to call with new page number
   */
  onPageChange(callback) {
    this.changeCallback = callback;
  }

  /**
   * Handle page change
   * @param {number} page - New page number
   */
  changePage(page) {
    if (page < 1 || page > this.totalPages || page === this.currentPage) {
      return;
    }
    
    this.currentPage = page;
    this.render();
    
    if (this.changeCallback) {
      this.changeCallback(page);
    }
  }

  /**
   * Calculate which page buttons to show
   * @returns {Array<number>} Array of page numbers to display
   */
  getPageNumbers() {
    const pages = [];
    const maxButtons = this.options.maxButtons;
    const current = this.currentPage;
    const total = this.totalPages;

    if (total <= maxButtons) {
      // Show all pages
      for (let i = 1; i <= total; i++) {
        pages.push(i);
      }
    } else {
      // Calculate range around current page
      let start = Math.max(1, current - Math.floor(maxButtons / 2));
      let end = Math.min(total, start + maxButtons - 1);
      
      // Adjust start if we're near the end
      if (end - start < maxButtons - 1) {
        start = Math.max(1, end - maxButtons + 1);
      }
      
      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
    }

    return pages;
  }

  /**
   * Render pagination controls
   */
  render() {
    if (!this.container) return;

    const pages = this.getPageNumbers();
    const current = this.currentPage;
    const total = this.totalPages;

    let html = '<div class="pagination">';

    // First button
    if (this.options.showFirstLast && current > 1) {
      html += `<button class="pagination-btn" data-page="1" aria-label="First page">«</button>`;
    }

    // Previous button
    if (this.options.showPrevNext && current > 1) {
      html += `<button class="pagination-btn" data-page="${current - 1}" aria-label="Previous page">‹</button>`;
    }

    // Page number buttons
    pages.forEach(page => {
      const isActive = page === current;
      html += `<button class="pagination-btn ${isActive ? 'active' : ''}" 
                       data-page="${page}" 
                       ${isActive ? 'aria-current="page"' : ''}>${page}</button>`;
    });

    // Next button
    if (this.options.showPrevNext && current < total) {
      html += `<button class="pagination-btn" data-page="${current + 1}" aria-label="Next page">›</button>`;
    }

    // Last button
    if (this.options.showFirstLast && current < total) {
      html += `<button class="pagination-btn" data-page="${total}" aria-label="Last page">»</button>`;
    }

    html += '</div>';

    this.container.innerHTML = html;

    // Add click handlers
    this.container.querySelectorAll('.pagination-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const page = parseInt(btn.dataset.page);
        this.changePage(page);
      });
    });
  }
}

/**
 * Confirmation Dialog Component
 * Shows a confirmation dialog and returns a promise
 */
class ConfirmDialog {
  /**
   * Show confirmation dialog
   * @param {string} message - Confirmation message
   * @param {Object} options - Dialog options
   * @returns {Promise<boolean>} Resolves to true if confirmed, false if cancelled
   */
  static show(message, options = {}) {
    return new Promise((resolve) => {
      const opts = {
        title: options.title || 'Confirm',
        confirmText: options.confirmText || 'Confirm',
        cancelText: options.cancelText || 'Cancel',
        confirmClass: options.confirmClass || 'btn-primary',
        cancelClass: options.cancelClass || 'btn-secondary',
        ...options
      };

      const content = `
        <div class="confirm-dialog">
          <p class="confirm-message">${message}</p>
          <div class="confirm-actions">
            <button class="btn ${opts.cancelClass}" data-action="cancel">${opts.cancelText}</button>
            <button class="btn ${opts.confirmClass}" data-action="confirm">${opts.confirmText}</button>
          </div>
        </div>
      `;

      const modal = new Modal(opts.title, content, {
        closeOnOverlay: false,
        width: '400px'
      });

      modal.show();

      // Add button handlers
      const confirmBtn = modal.element.querySelector('[data-action="confirm"]');
      const cancelBtn = modal.element.querySelector('[data-action="cancel"]');

      confirmBtn.addEventListener('click', () => {
        modal.hide();
        resolve(true);
      });

      cancelBtn.addEventListener('click', () => {
        modal.hide();
        resolve(false);
      });

      // Handle modal close
      modal.onClose(() => {
        resolve(false);
      });
    });
  }
}

// Export components
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    Modal,
    Notification,
    LoadingSpinner,
    Pagination,
    ConfirmDialog
  };
}
