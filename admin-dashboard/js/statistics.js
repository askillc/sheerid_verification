/**
 * Statistics Module
 * Handles dashboard statistics display, charts, and auto-refresh
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7
 */

/**
 * Statistics Manager
 * Manages fetching, rendering, and auto-refreshing of dashboard statistics
 */
class StatisticsManager {
  constructor(apiClient) {
    this.apiClient = apiClient;
    this.refreshInterval = null;
    this.refreshRate = 30000; // 30 seconds
    this.charts = {
      userGrowth: null,
      revenue: null
    };
  }

  /**
   * Initialize statistics section
   * Fetches initial data and sets up auto-refresh
   */
  async init() {
    try {
      await this.fetchAndRender();
      this.startAutoRefresh();
    } catch (error) {
      console.error('Failed to initialize statistics:', error);
      Notification.error('Failed to load dashboard statistics: ' + error.message);
    }
  }

  /**
   * Fetch statistics from API and render
   */
  async fetchAndRender() {
    try {
      LoadingSpinner.show('#dashboard-section');
      const data = await this.fetchStatistics();
      this.renderStatistics(data);
      LoadingSpinner.hide();
    } catch (error) {
      LoadingSpinner.hide();
      throw error;
    }
  }

  /**
   * Fetch statistics data from API
   * @returns {Promise<object>} Statistics data
   */
  async fetchStatistics() {
    return await this.apiClient.getStatistics();
  }

  /**
   * Render all statistics components
   * @param {object} data - Statistics data from API
   */
  renderStatistics(data) {
    this.renderStatCards(data);
    this.renderUserGrowthChart(data.charts?.userGrowth || []);
    this.renderRevenueChart(data.charts?.revenueByDay || []);
  }

  /**
   * Render statistics cards
   * @param {object} data - Statistics data
   */
  renderStatCards(data) {
    // Total Users
    const totalUsersEl = document.getElementById('stat-total-users');
    if (totalUsersEl) {
      totalUsersEl.textContent = this.formatNumber(data.users?.total || 0);
    }

    // VIP Users
    const vipUsersEl = document.getElementById('stat-vip-users');
    if (vipUsersEl) {
      vipUsersEl.textContent = this.formatNumber(data.users?.vip || 0);
    }

    // Blocked Users
    const blockedUsersEl = document.getElementById('stat-blocked-users');
    if (blockedUsersEl) {
      blockedUsersEl.textContent = this.formatNumber(data.users?.blocked || 0);
    }

    // New Users Today
    const newUsersEl = document.getElementById('stat-new-users');
    if (newUsersEl) {
      newUsersEl.textContent = this.formatNumber(data.users?.newToday || 0);
    }

    // Total Jobs
    const totalJobsEl = document.getElementById('stat-total-jobs');
    if (totalJobsEl) {
      totalJobsEl.textContent = this.formatNumber(data.jobs?.total || 0);
    }

    // Pending Jobs
    const pendingJobsEl = document.getElementById('stat-pending-jobs');
    if (pendingJobsEl) {
      pendingJobsEl.textContent = this.formatNumber(data.jobs?.pending || 0);
    }

    // Completed Jobs
    const completedJobsEl = document.getElementById('stat-completed-jobs');
    if (completedJobsEl) {
      completedJobsEl.textContent = this.formatNumber(data.jobs?.completed || 0);
    }

    // Failed Jobs
    const failedJobsEl = document.getElementById('stat-failed-jobs');
    if (failedJobsEl) {
      failedJobsEl.textContent = this.formatNumber(data.jobs?.failed || 0);
    }

    // Success Rate
    const successRateEl = document.getElementById('stat-success-rate');
    if (successRateEl) {
      const successRate = this.calculateSuccessRate(
        data.jobs?.completed || 0,
        data.jobs?.failed || 0
      );
      successRateEl.textContent = successRate.toFixed(1) + '%';
    }

    // Today's Revenue
    const todayRevenueEl = document.getElementById('stat-today-revenue');
    if (todayRevenueEl) {
      const currency = data.revenue?.currency || 'USD';
      todayRevenueEl.textContent = this.formatCurrency(
        data.revenue?.today || 0,
        currency
      );
    }

    // This Week's Revenue
    const weekRevenueEl = document.getElementById('stat-week-revenue');
    if (weekRevenueEl) {
      const currency = data.revenue?.currency || 'USD';
      weekRevenueEl.textContent = this.formatCurrency(
        data.revenue?.thisWeek || 0,
        currency
      );
    }

    // This Month's Revenue
    const monthRevenueEl = document.getElementById('stat-month-revenue');
    if (monthRevenueEl) {
      const currency = data.revenue?.currency || 'USD';
      monthRevenueEl.textContent = this.formatCurrency(
        data.revenue?.thisMonth || 0,
        currency
      );
    }

    // Update last refresh time
    const lastUpdateEl = document.getElementById('stats-last-update');
    if (lastUpdateEl) {
      lastUpdateEl.textContent = 'Last updated: ' + new Date().toLocaleTimeString();
    }
  }

  /**
   * Calculate success rate percentage
   * @param {number} completed - Number of completed jobs
   * @param {number} failed - Number of failed jobs
   * @returns {number} Success rate as percentage
   */
  calculateSuccessRate(completed, failed) {
    const total = completed + failed;
    if (total === 0) {
      return 0;
    }
    return (completed / total) * 100;
  }

  /**
   * Render user growth chart
   * @param {Array} data - Array of {date, count} objects
   */
  renderUserGrowthChart(data) {
    const canvas = document.getElementById('user-growth-chart');
    if (!canvas) return;

    // Destroy existing chart if present
    if (this.charts.userGrowth) {
      this.charts.userGrowth.destroy();
    }

    // Prepare data for Chart.js
    const labels = data.map(item => this.formatDate(item.date));
    const values = data.map(item => item.count);

    // Create chart
    const ctx = canvas.getContext('2d');
    this.charts.userGrowth = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'User Growth',
          data: values,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointHoverRadius: 5
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            padding: 12,
            titleColor: '#fff',
            bodyColor: '#fff',
            borderColor: '#3b82f6',
            borderWidth: 1
          }
        },
        scales: {
          x: {
            grid: {
              display: false
            },
            ticks: {
              color: '#9ca3af'
            }
          },
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(156, 163, 175, 0.1)'
            },
            ticks: {
              color: '#9ca3af',
              precision: 0
            }
          }
        },
        interaction: {
          mode: 'nearest',
          axis: 'x',
          intersect: false
        }
      }
    });
  }

  /**
   * Render revenue chart
   * @param {Array} data - Array of {date, amount} objects
   */
  renderRevenueChart(data) {
    const canvas = document.getElementById('revenue-chart');
    if (!canvas) return;

    // Destroy existing chart if present
    if (this.charts.revenue) {
      this.charts.revenue.destroy();
    }

    // Prepare data for Chart.js
    const labels = data.map(item => this.formatDate(item.date));
    const values = data.map(item => item.amount);

    // Create chart
    const ctx = canvas.getContext('2d');
    this.charts.revenue = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Revenue',
          data: values,
          backgroundColor: '#10b981',
          borderColor: '#059669',
          borderWidth: 1,
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            padding: 12,
            titleColor: '#fff',
            bodyColor: '#fff',
            borderColor: '#10b981',
            borderWidth: 1,
            callbacks: {
              label: function(context) {
                return 'Revenue: $' + context.parsed.y.toFixed(2);
              }
            }
          }
        },
        scales: {
          x: {
            grid: {
              display: false
            },
            ticks: {
              color: '#9ca3af'
            }
          },
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(156, 163, 175, 0.1)'
            },
            ticks: {
              color: '#9ca3af',
              callback: function(value) {
                return '$' + value.toFixed(0);
              }
            }
          }
        }
      }
    });
  }

  /**
   * Start auto-refresh timer
   */
  startAutoRefresh() {
    // Clear any existing interval
    this.stopAutoRefresh();

    // Set up new interval
    this.refreshInterval = setInterval(async () => {
      try {
        const data = await this.fetchStatistics();
        this.renderStatistics(data);
      } catch (error) {
        console.error('Failed to refresh statistics:', error);
        // Don't show error notification for background refresh failures
      }
    }, this.refreshRate);
  }

  /**
   * Stop auto-refresh timer
   */
  stopAutoRefresh() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  /**
   * Manually refresh statistics
   */
  async refresh() {
    try {
      await this.fetchAndRender();
      Notification.success('Statistics refreshed successfully');
    } catch (error) {
      Notification.error('Failed to refresh statistics: ' + error.message);
    }
  }

  /**
   * Clean up resources
   */
  destroy() {
    this.stopAutoRefresh();
    
    // Destroy charts
    if (this.charts.userGrowth) {
      this.charts.userGrowth.destroy();
      this.charts.userGrowth = null;
    }
    
    if (this.charts.revenue) {
      this.charts.revenue.destroy();
      this.charts.revenue = null;
    }
  }

  /**
   * Format number with thousands separator
   * @param {number} num - Number to format
   * @returns {string} Formatted number
   */
  formatNumber(num) {
    return num.toLocaleString('en-US');
  }

  /**
   * Format currency value
   * @param {number} amount - Amount to format
   * @param {string} currency - Currency code (default: USD)
   * @returns {string} Formatted currency
   */
  formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  }

  /**
   * Format date for display
   * @param {string} dateString - ISO date string
   * @returns {string} Formatted date
   */
  formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = StatisticsManager;
}
