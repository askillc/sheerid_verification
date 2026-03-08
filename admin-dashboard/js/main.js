/**
 * Main Application Entry Point
 * Initializes the admin dashboard and handles sidebar navigation
 * Requirements: 1.1, 10.1
 */

// Import AuthManager (will be loaded as module)
// Note: In production, use proper ES6 imports. For now, AuthManager is loaded globally.

// Application state
const AppState = {
  currentSection: 'dashboard',
  loadedSections: new Set(),
  authManager: null,
  apiClient: null,
  statisticsManager: null
};

/**
 * Initialize the application
 */
function initializeApp() {
  console.log('Initializing Admin Dashboard...');
  
  // Initialize authentication manager
  AppState.authManager = new AuthManager();
  
  // Get containers
  const loginContainer = document.getElementById('login-container');
  const dashboardContainer = document.getElementById('dashboard-container');
  
  // Check if user is authenticated
  if (!AppState.authManager.isAuthenticated()) {
    console.log('User not authenticated, showing login form...');
    loginContainer.style.display = 'flex';
    dashboardContainer.style.display = 'none';
    
    // Setup login form handler
    setupLoginForm();
    return; // Don't initialize dashboard
  }
  
  // User is authenticated, show dashboard
  console.log('User authenticated, showing dashboard...');
  loginContainer.style.display = 'none';
  dashboardContainer.style.display = 'block';
  
  // Initialize API client
  AppState.apiClient = new APIClient('/api', AppState.authManager);
  
  // Initialize statistics manager
  AppState.statisticsManager = new StatisticsManager(AppState.apiClient);
  
  // Initialize module managers
  initUserManagement(AppState.apiClient);
  initJobManagement(AppState.apiClient);
  initTransactionManagement(AppState.apiClient);
  initSettingsManagement(AppState.apiClient);
  
  // Initialize sidebar navigation
  initializeSidebarNavigation();
  
  // Initialize logout button
  initializeLogoutButton();
  
  // Initialize mobile navigation
  initializeMobileNavigation();
  
  // Initialize refresh button
  initializeRefreshButton();
  
  // Load the initial section (dashboard)
  loadSection('dashboard');
  
  console.log('Admin Dashboard initialized successfully');
}

/**
 * Initialize sidebar navigation
 * Adds click handlers to menu items for section switching
 * Requirement: 1.1
 */
function initializeSidebarNavigation() {
  const menuItems = document.querySelectorAll('.menu-item');
  
  menuItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      
      const section = item.dataset.section;
      
      if (section && section !== AppState.currentSection) {
        // Update active state
        setActiveMenuItem(item);
        
        // Load the selected section
        loadSection(section);
      }
    });
  });
}

/**
 * Set active state for menu item
 * @param {HTMLElement} activeItem - The menu item to set as active
 */
function setActiveMenuItem(activeItem) {
  // Remove active class from all menu items
  document.querySelectorAll('.menu-item').forEach(item => {
    item.classList.remove('active');
  });
  
  // Add active class to selected item
  activeItem.classList.add('active');
}

/**
 * Load a section with lazy loading
 * Only loads section data when first accessed
 * Requirement: 10.1 - Lazy loading behavior
 * @param {string} sectionName - Name of the section to load
 */
function loadSection(sectionName) {
  console.log(`Loading section: ${sectionName}`);
  
  // Hide all sections
  document.querySelectorAll('.content-section').forEach(section => {
    section.classList.remove('active');
  });
  
  // Show the selected section
  const sectionElement = document.getElementById(`${sectionName}-section`);
  if (sectionElement) {
    sectionElement.classList.add('active');
    
    // Update section title in header
    updateSectionTitle(sectionName);
    
    // Update URL hash for deep linking
    updateURLHash(sectionName);
    
    // Lazy load section data if not already loaded
    if (!AppState.loadedSections.has(sectionName)) {
      loadSectionData(sectionName);
      AppState.loadedSections.add(sectionName);
    }
    
    // Update current section
    AppState.currentSection = sectionName;
    
    // Close mobile sidebar if open
    closeMobileSidebar();
  } else {
    console.error(`Section not found: ${sectionName}`);
  }
}

/**
 * Update the section title in the header
 * @param {string} sectionName - Name of the section
 */
function updateSectionTitle(sectionName) {
  const titleElement = document.getElementById('section-title');
  if (titleElement) {
    // Capitalize first letter
    const title = sectionName.charAt(0).toUpperCase() + sectionName.slice(1);
    titleElement.textContent = title;
  }
}

/**
 * Load data for a specific section (lazy loading)
 * This function will be expanded in later tasks to load actual data
 * Requirement: 10.1 - Lazy loading for sections not immediately visible
 * @param {string} sectionName - Name of the section to load data for
 */
function loadSectionData(sectionName) {
  console.log(`Lazy loading data for section: ${sectionName}`);
  
  // Load data for each section
  switch (sectionName) {
    case 'dashboard':
      console.log('Loading dashboard statistics...');
      if (AppState.statisticsManager) {
        AppState.statisticsManager.init();
      }
      break;
    case 'users':
      console.log('Loading user list...');
      if (typeof loadUsers === 'function') {
        loadUsers();
      }
      break;
    case 'jobs':
      console.log('Loading job list...');
      if (typeof loadJobs === 'function') {
        loadJobs();
      }
      break;
    case 'transactions':
      console.log('Loading transaction list...');
      if (typeof loadTransactions === 'function') {
        loadTransactions();
      }
      break;
    case 'settings':
      console.log('Loading settings...');
      if (typeof loadSettings === 'function') {
        loadSettings();
      }
      break;
    default:
      console.warn(`Unknown section: ${sectionName}`);
  }
}

/**
 * Initialize logout button
 * Requirement: 8.5 - Logout functionality
 */
function initializeLogoutButton() {
  const logoutBtn = document.getElementById('logout-btn');
  
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      
      // Show confirmation dialog
      const confirmed = await ConfirmDialog.show(
        'Are you sure you want to logout?',
        {
          title: 'Confirm Logout',
          confirmText: 'Logout',
          confirmClass: 'btn-danger'
        }
      );
      
      if (confirmed) {
        console.log('Logging out...');
        
        // Show notification
        Notification.info('Logging out...');
        
        // Perform logout
        if (AppState.authManager) {
          AppState.authManager.logout();
        } else {
          // Fallback if authManager not available
          window.location.href = '/login.html';
        }
      }
    });
  }
}

/**
 * Initialize refresh button for statistics
 * Requirement: 6.1-6.7 - Manual refresh of statistics
 */
function initializeRefreshButton() {
  const refreshBtn = document.getElementById('refresh-stats-btn');
  
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      
      if (AppState.statisticsManager) {
        await AppState.statisticsManager.refresh();
      }
    });
  }
}

/**
 * Initialize mobile navigation (hamburger menu)
 * Requirement: 11.1 - Mobile responsive navigation
 */
function initializeMobileNavigation() {
  const hamburgerBtn = document.getElementById('hamburger-menu');
  const sidebar = document.getElementById('sidebar');
  
  if (hamburgerBtn && sidebar) {
    // Toggle sidebar on hamburger click
    hamburgerBtn.addEventListener('click', (e) => {
      e.preventDefault();
      toggleMobileSidebar();
    });
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
      const isClickInsideSidebar = sidebar.contains(e.target);
      const isClickOnHamburger = hamburgerBtn.contains(e.target);
      
      if (!isClickInsideSidebar && !isClickOnHamburger && sidebar.classList.contains('sidebar-open')) {
        closeMobileSidebar();
      }
    });
  }
}

/**
 * Toggle mobile sidebar open/closed
 */
function toggleMobileSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) {
    sidebar.classList.toggle('sidebar-open');
  }
}

/**
 * Close mobile sidebar
 */
function closeMobileSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) {
    sidebar.classList.remove('sidebar-open');
  }
}

/**
 * Handle browser back/forward navigation
 * Allows deep linking to specific sections
 * Requirement: 1.1 - Deep linking support
 */
function initializeRouting() {
  // Parse URL hash to determine initial section
  const hash = window.location.hash.substring(1); // Remove '#'
  if (hash) {
    const menuItem = document.querySelector(`.menu-item[data-section="${hash}"]`);
    if (menuItem) {
      setActiveMenuItem(menuItem);
      loadSection(hash);
    }
  }
  
  // Listen for hash changes
  window.addEventListener('hashchange', () => {
    const newHash = window.location.hash.substring(1);
    if (newHash) {
      const menuItem = document.querySelector(`.menu-item[data-section="${newHash}"]`);
      if (menuItem) {
        setActiveMenuItem(menuItem);
        loadSection(newHash);
      }
    }
  });
}

/**
 * Navigate to a section programmatically
 * Updates URL hash and loads the section
 * @param {string} sectionName - Name of the section to navigate to
 */
function navigateToSection(sectionName) {
  window.location.hash = sectionName;
}

/**
 * Initialize keyboard shortcuts for common actions
 * Requirement: 1.1 - Keyboard shortcuts for navigation
 */
function initializeKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Only handle shortcuts when not typing in an input field
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
      return;
    }
    
    // Check for Ctrl/Cmd key combinations
    const isCtrlOrCmd = e.ctrlKey || e.metaKey;
    
    // Navigation shortcuts (Alt + Number)
    if (e.altKey && !isCtrlOrCmd) {
      switch (e.key) {
        case '1':
          e.preventDefault();
          navigateToSection('dashboard');
          break;
        case '2':
          e.preventDefault();
          navigateToSection('users');
          break;
        case '3':
          e.preventDefault();
          navigateToSection('jobs');
          break;
        case '4':
          e.preventDefault();
          navigateToSection('transactions');
          break;
        case '5':
          e.preventDefault();
          navigateToSection('settings');
          break;
      }
    }
    
    // Refresh shortcut (Ctrl/Cmd + R for current section)
    if (isCtrlOrCmd && e.key === 'r' && AppState.currentSection === 'dashboard') {
      e.preventDefault();
      if (AppState.statisticsManager) {
        AppState.statisticsManager.refresh();
      }
    }
    
    // Search shortcut (Ctrl/Cmd + K)
    if (isCtrlOrCmd && e.key === 'k') {
      e.preventDefault();
      const searchInput = document.getElementById('user-search');
      if (searchInput && AppState.currentSection === 'users') {
        searchInput.focus();
      }
    }
    
    // Help shortcut (Ctrl/Cmd + /)
    if (isCtrlOrCmd && e.key === '/') {
      e.preventDefault();
      showKeyboardShortcutsHelp();
    }
    
    // Escape key to close modals
    if (e.key === 'Escape') {
      const visibleModal = document.querySelector('.modal-overlay.modal-visible');
      if (visibleModal) {
        const modal = Modal.getInstance();
        if (modal) {
          modal.hide();
        }
      }
    }
  });
  
  console.log('Keyboard shortcuts initialized:');
  console.log('  Alt+1: Dashboard');
  console.log('  Alt+2: Users');
  console.log('  Alt+3: Jobs');
  console.log('  Alt+4: Transactions');
  console.log('  Alt+5: Settings');
  console.log('  Ctrl/Cmd+R: Refresh (Dashboard)');
  console.log('  Ctrl/Cmd+K: Focus Search (Users)');
  console.log('  Ctrl/Cmd+/: Show Keyboard Shortcuts');
  console.log('  Escape: Close Modal');
}

/**
 * Show keyboard shortcuts help modal
 */
function showKeyboardShortcutsHelp() {
  const shortcuts = [
    { keys: 'Alt + 1', description: 'Navigate to Dashboard' },
    { keys: 'Alt + 2', description: 'Navigate to Users' },
    { keys: 'Alt + 3', description: 'Navigate to Jobs' },
    { keys: 'Alt + 4', description: 'Navigate to Transactions' },
    { keys: 'Alt + 5', description: 'Navigate to Settings' },
    { keys: 'Ctrl/Cmd + R', description: 'Refresh Dashboard Statistics' },
    { keys: 'Ctrl/Cmd + K', description: 'Focus Search (Users section)' },
    { keys: 'Ctrl/Cmd + /', description: 'Show Keyboard Shortcuts' },
    { keys: 'Escape', description: 'Close Modal' }
  ];
  
  const shortcutsHTML = `
    <div class="keyboard-shortcuts-help">
      <p style="margin-bottom: var(--spacing-lg); color: var(--color-text-secondary);">
        Use these keyboard shortcuts to navigate and perform actions quickly.
      </p>
      <table class="shortcuts-table">
        <thead>
          <tr>
            <th>Shortcut</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${shortcuts.map(s => `
            <tr>
              <td><kbd>${s.keys}</kbd></td>
              <td>${s.description}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
  
  const modal = new Modal('Keyboard Shortcuts', shortcutsHTML, {
    size: 'medium',
    showFooter: false
  });
  
  modal.show();
}

/**
 * Update URL hash when navigating to a section
 * Enables deep linking and browser history
 * @param {string} sectionName - Name of the section
 */
function updateURLHash(sectionName) {
  // Update URL hash without triggering hashchange event
  if (window.location.hash !== `#${sectionName}`) {
    window.history.pushState(null, null, `#${sectionName}`);
  }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  initializeApp();
  initializeRouting();
  initializeKeyboardShortcuts();
});


/**
 * Setup login form handler
 */
function setupLoginForm() {
  const loginForm = document.getElementById('login-form');
  const loginError = document.getElementById('login-error');
  
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    // Hide previous errors
    loginError.style.display = 'none';
    
    // Disable submit button
    const submitBtn = loginForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Signing in...';
    
    try {
      // Attempt login
      await AppState.authManager.login(username, password);
      
      // Success - reload page to show dashboard
      window.location.reload();
    } catch (error) {
      // Show error message
      loginError.textContent = error.message || 'Login failed. Please try again.';
      loginError.style.display = 'block';
      
      // Re-enable submit button
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  });
}
