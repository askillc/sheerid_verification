/**
 * Utility Functions Module
 * Provides helper functions for the admin dashboard
 * Requirements: 10.2
 */

/**
 * Format a date according to the specified format
 * @param {Date|string|number} date - Date to format
 * @param {string} format - Format string (default: 'YYYY-MM-DD HH:mm:ss')
 * @returns {string} Formatted date string
 */
function formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
  const d = new Date(date);
  
  if (isNaN(d.getTime())) {
    return 'Invalid Date';
  }

  const pad = (num, size = 2) => String(num).padStart(size, '0');

  const year = d.getFullYear();
  const month = pad(d.getMonth() + 1);
  const day = pad(d.getDate());
  const hours = pad(d.getHours());
  const minutes = pad(d.getMinutes());
  const seconds = pad(d.getSeconds());
  const hours12 = pad(d.getHours() % 12 || 12);
  const ampm = d.getHours() >= 12 ? 'PM' : 'AM';

  const replacements = {
    'YYYY': year,
    'YY': String(year).slice(-2),
    'MM': month,
    'M': d.getMonth() + 1,
    'DD': day,
    'D': d.getDate(),
    'HH': hours,
    'H': d.getHours(),
    'hh': hours12,
    'h': parseInt(hours12),
    'mm': minutes,
    'm': d.getMinutes(),
    'ss': seconds,
    's': d.getSeconds(),
    'A': ampm,
    'a': ampm.toLowerCase()
  };

  let result = format;
  for (const [key, value] of Object.entries(replacements)) {
    result = result.replace(new RegExp(key, 'g'), value);
  }

  return result;
}

/**
 * Format a date as relative time (e.g., "2 hours ago")
 * @param {Date|string|number} date - Date to format
 * @returns {string} Relative time string
 */
function formatRelativeTime(date) {
  const d = new Date(date);
  const now = new Date();
  const diffMs = now - d;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  const diffWeek = Math.floor(diffDay / 7);
  const diffMonth = Math.floor(diffDay / 30);
  const diffYear = Math.floor(diffDay / 365);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin} minute${diffMin !== 1 ? 's' : ''} ago`;
  if (diffHour < 24) return `${diffHour} hour${diffHour !== 1 ? 's' : ''} ago`;
  if (diffDay < 7) return `${diffDay} day${diffDay !== 1 ? 's' : ''} ago`;
  if (diffWeek < 4) return `${diffWeek} week${diffWeek !== 1 ? 's' : ''} ago`;
  if (diffMonth < 12) return `${diffMonth} month${diffMonth !== 1 ? 's' : ''} ago`;
  return `${diffYear} year${diffYear !== 1 ? 's' : ''} ago`;
}

/**
 * Format a number with specified decimal places
 * @param {number} number - Number to format
 * @param {number} decimals - Number of decimal places (default: 2)
 * @param {string} decimalSeparator - Decimal separator (default: '.')
 * @param {string} thousandsSeparator - Thousands separator (default: ',')
 * @returns {string} Formatted number string
 */
function formatNumber(number, decimals = 2, decimalSeparator = '.', thousandsSeparator = ',') {
  if (typeof number !== 'number' || isNaN(number)) {
    return '0';
  }

  const fixed = number.toFixed(decimals);
  const parts = fixed.split('.');
  
  // Add thousands separator
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, thousandsSeparator);
  
  return parts.join(decimalSeparator);
}

/**
 * Format a number as currency
 * @param {number} amount - Amount to format
 * @param {string} currency - Currency code (default: 'USD')
 * @param {string} locale - Locale for formatting (default: 'en-US')
 * @returns {string} Formatted currency string
 */
function formatCurrency(amount, currency = 'USD', locale = 'en-US') {
  if (typeof amount !== 'number' || isNaN(amount)) {
    amount = 0;
  }

  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currency
    }).format(amount);
  } catch (error) {
    // Fallback if Intl is not supported or currency is invalid
    const symbol = currency === 'USD' ? '$' : currency;
    return `${symbol}${formatNumber(amount, 2)}`;
  }
}

/**
 * Format a number as percentage
 * @param {number} value - Value to format (0-1 or 0-100)
 * @param {number} decimals - Number of decimal places (default: 1)
 * @param {boolean} isDecimal - Whether value is in decimal form (0-1) or percentage form (0-100)
 * @returns {string} Formatted percentage string
 */
function formatPercentage(value, decimals = 1, isDecimal = true) {
  if (typeof value !== 'number' || isNaN(value)) {
    return '0%';
  }

  const percentage = isDecimal ? value * 100 : value;
  return `${formatNumber(percentage, decimals)}%`;
}

/**
 * Format file size in human-readable format
 * @param {number} bytes - Size in bytes
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted size string
 */
function formatFileSize(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes';
  if (typeof bytes !== 'number' || isNaN(bytes)) return 'Invalid';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${formatNumber(bytes / Math.pow(k, i), decimals)} ${sizes[i]}`;
}

/**
 * Debounce a function - delays execution until after wait time has elapsed
 * @param {Function} func - Function to debounce
 * @param {number} delay - Delay in milliseconds (default: 300)
 * @returns {Function} Debounced function
 */
function debounce(func, delay = 300) {
  let timeoutId;
  
  return function debounced(...args) {
    const context = this;
    
    clearTimeout(timeoutId);
    
    timeoutId = setTimeout(() => {
      func.apply(context, args);
    }, delay);
  };
}

/**
 * Throttle a function - limits execution to once per wait time
 * @param {Function} func - Function to throttle
 * @param {number} delay - Delay in milliseconds (default: 300)
 * @returns {Function} Throttled function
 */
function throttle(func, delay = 300) {
  let lastCall = 0;
  let timeoutId;
  
  return function throttled(...args) {
    const context = this;
    const now = Date.now();
    const timeSinceLastCall = now - lastCall;
    
    if (timeSinceLastCall >= delay) {
      lastCall = now;
      func.apply(context, args);
    } else {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        lastCall = Date.now();
        func.apply(context, args);
      }, delay - timeSinceLastCall);
    }
  };
}

/**
 * Validate email address
 * @param {string} email - Email address to validate
 * @returns {boolean} True if valid, false otherwise
 */
function validateEmail(email) {
  if (typeof email !== 'string') {
    return false;
  }

  // RFC 5322 compliant email regex (simplified)
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Validate URL
 * @param {string} url - URL to validate
 * @returns {boolean} True if valid, false otherwise
 */
function validateURL(url) {
  if (typeof url !== 'string') {
    return false;
  }

  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

/**
 * Validate phone number (basic validation)
 * @param {string} phone - Phone number to validate
 * @returns {boolean} True if valid, false otherwise
 */
function validatePhone(phone) {
  if (typeof phone !== 'string') {
    return false;
  }

  // Remove common formatting characters
  const cleaned = phone.replace(/[\s\-\(\)\.]/g, '');
  
  // Check if it's a valid number with 10-15 digits
  const phoneRegex = /^\+?[0-9]{10,15}$/;
  return phoneRegex.test(cleaned);
}

/**
 * Sanitize HTML to prevent XSS attacks
 * @param {string} html - HTML string to sanitize
 * @returns {string} Sanitized HTML string
 */
function sanitizeHTML(html) {
  if (typeof html !== 'string') {
    return '';
  }

  const div = document.createElement('div');
  div.textContent = html;
  return div.innerHTML;
}

/**
 * Escape HTML special characters
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHTML(text) {
  if (typeof text !== 'string') {
    return '';
  }

  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };

  return text.replace(/[&<>"']/g, char => map[char]);
}

/**
 * Truncate text to specified length
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @param {string} suffix - Suffix to add (default: '...')
 * @returns {string} Truncated text
 */
function truncateText(text, maxLength, suffix = '...') {
  if (typeof text !== 'string') {
    return '';
  }

  if (text.length <= maxLength) {
    return text;
  }

  return text.substring(0, maxLength - suffix.length) + suffix;
}

/**
 * Deep clone an object
 * @param {*} obj - Object to clone
 * @returns {*} Cloned object
 */
function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }

  if (obj instanceof Date) {
    return new Date(obj.getTime());
  }

  if (obj instanceof Array) {
    return obj.map(item => deepClone(item));
  }

  if (obj instanceof Object) {
    const cloned = {};
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        cloned[key] = deepClone(obj[key]);
      }
    }
    return cloned;
  }

  return obj;
}

/**
 * Generate a random ID
 * @param {number} length - Length of ID (default: 16)
 * @returns {string} Random ID
 */
function generateId(length = 16) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  
  return result;
}

/**
 * Parse query string to object
 * @param {string} queryString - Query string (with or without leading '?')
 * @returns {Object} Parsed query parameters
 */
function parseQueryString(queryString) {
  const params = {};
  const query = queryString.startsWith('?') ? queryString.slice(1) : queryString;
  
  if (!query) {
    return params;
  }

  query.split('&').forEach(param => {
    const [key, value] = param.split('=');
    if (key) {
      params[decodeURIComponent(key)] = value ? decodeURIComponent(value) : '';
    }
  });

  return params;
}

/**
 * Build query string from object
 * @param {Object} params - Parameters object
 * @returns {string} Query string (without leading '?')
 */
function buildQueryString(params) {
  if (!params || typeof params !== 'object') {
    return '';
  }

  return Object.entries(params)
    .filter(([_, value]) => value !== null && value !== undefined)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join('&');
}

/**
 * Check if value is empty (null, undefined, empty string, empty array, empty object)
 * @param {*} value - Value to check
 * @returns {boolean} True if empty, false otherwise
 */
function isEmpty(value) {
  if (value === null || value === undefined) {
    return true;
  }

  if (typeof value === 'string' || Array.isArray(value)) {
    return value.length === 0;
  }

  if (typeof value === 'object') {
    return Object.keys(value).length === 0;
  }

  return false;
}

/**
 * Sleep for specified duration
 * @param {number} ms - Duration in milliseconds
 * @returns {Promise} Promise that resolves after duration
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Retry a function with exponential backoff
 * @param {Function} func - Async function to retry
 * @param {number} maxRetries - Maximum number of retries (default: 3)
 * @param {number} baseDelay - Base delay in milliseconds (default: 1000)
 * @returns {Promise} Promise that resolves with function result
 */
async function retry(func, maxRetries = 3, baseDelay = 1000) {
  let lastError;
  
  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await func();
    } catch (error) {
      lastError = error;
      
      if (i < maxRetries) {
        const delay = baseDelay * Math.pow(2, i);
        await sleep(delay);
      }
    }
  }
  
  throw lastError;
}

/**
 * Group array items by key
 * @param {Array} array - Array to group
 * @param {string|Function} key - Key to group by (property name or function)
 * @returns {Object} Grouped object
 */
function groupBy(array, key) {
  if (!Array.isArray(array)) {
    return {};
  }

  const keyFunc = typeof key === 'function' ? key : item => item[key];

  return array.reduce((result, item) => {
    const groupKey = keyFunc(item);
    if (!result[groupKey]) {
      result[groupKey] = [];
    }
    result[groupKey].push(item);
    return result;
  }, {});
}

/**
 * Sort array of objects by key
 * @param {Array} array - Array to sort
 * @param {string} key - Key to sort by
 * @param {string} order - Sort order ('asc' or 'desc')
 * @returns {Array} Sorted array
 */
function sortBy(array, key, order = 'asc') {
  if (!Array.isArray(array)) {
    return [];
  }

  const sorted = [...array].sort((a, b) => {
    const aVal = a[key];
    const bVal = b[key];

    if (aVal < bVal) return order === 'asc' ? -1 : 1;
    if (aVal > bVal) return order === 'asc' ? 1 : -1;
    return 0;
  });

  return sorted;
}

/**
 * Remove duplicates from array
 * @param {Array} array - Array to deduplicate
 * @param {string|Function} key - Optional key for object arrays
 * @returns {Array} Deduplicated array
 */
function unique(array, key = null) {
  if (!Array.isArray(array)) {
    return [];
  }

  if (!key) {
    return [...new Set(array)];
  }

  const keyFunc = typeof key === 'function' ? key : item => item[key];
  const seen = new Set();
  
  return array.filter(item => {
    const k = keyFunc(item);
    if (seen.has(k)) {
      return false;
    }
    seen.add(k);
    return true;
  });
}

// Export functions
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    formatDate,
    formatRelativeTime,
    formatNumber,
    formatCurrency,
    formatPercentage,
    formatFileSize,
    debounce,
    throttle,
    validateEmail,
    validateURL,
    validatePhone,
    sanitizeHTML,
    escapeHTML,
    truncateText,
    deepClone,
    generateId,
    parseQueryString,
    buildQueryString,
    isEmpty,
    sleep,
    retry,
    groupBy,
    sortBy,
    unique
  };
}
