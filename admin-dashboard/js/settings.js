/**
 * Settings Management Module
 * Handles system configuration including maintenance mode, bot settings, proxy, and fraud detection
 * Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
 */

// Module state
let apiClient = null;
let currentSettings = null;

/**
 * Initialize the settings management module
 * @param {APIClient} api - API client instance
 */
function initSettingsManagement(api) {
  apiClient = api;
  
  // Load initial settings
  loadSettings();
  
  // Setup event handlers
  setupMaintenanceModeToggle();
  setupSaveButton();
}

/**
 * Fetch settings from API
 * @returns {Promise<object>} Settings data
 * Requirements: 5.1
 */
async function fetchSettings() {
  try {
    LoadingSpinner.show('#settings-container');
    
    const data = await apiClient.getSettings();
    
    return data;
  } catch (error) {
    Notification.error(`Failed to load settings: ${error.message}`);
    throw error;
  } finally {
    LoadingSpinner.hide();
  }
}

/**
 * Render settings in the form
 * @param {object} settings - Settings object
 * Requirements: 5.1, 5.3, 5.4, 5.5, 5.6
 */
function renderSettings(settings) {
  if (!settings) {
    console.error('No settings data to render');
    return;
  }
  
  // Store current settings
  currentSettings = settings;
  
  // System Settings
  if (settings.system) {
    const maintenanceModeToggle = document.getElementById('maintenance-mode');
    if (maintenanceModeToggle) {
      maintenanceModeToggle.checked = settings.system.maintenanceMode || false;
    }
    
    const maintenanceMessageInput = document.getElementById('maintenance-message');
    if (maintenanceMessageInput) {
      maintenanceMessageInput.value = settings.system.maintenanceMessage || '';
    }
  }
  
  // Bot Configuration
  if (settings.bot) {
    const welcomeBonusInput = document.getElementById('welcome-bonus');
    if (welcomeBonusInput) {
      welcomeBonusInput.value = settings.bot.welcomeBonus || 0;
    }
    
    const verifyPriceInput = document.getElementById('verify-price');
    if (verifyPriceInput) {
      verifyPriceInput.value = settings.bot.verifyPrice || 0;
    }
    
    // VIP Prices
    if (settings.bot.vipPrices) {
      const basicPriceInput = document.getElementById('vip-basic-price');
      if (basicPriceInput) {
        basicPriceInput.value = settings.bot.vipPrices.basic || 0;
      }
      
      const proPriceInput = document.getElementById('vip-pro-price');
      if (proPriceInput) {
        proPriceInput.value = settings.bot.vipPrices.pro || 0;
      }
      
      const businessPriceInput = document.getElementById('vip-business-price');
      if (businessPriceInput) {
        businessPriceInput.value = settings.bot.vipPrices.business || 0;
      }
    }
  }
  
  // Proxy Settings
  if (settings.proxy) {
    const proxyEnabledToggle = document.getElementById('proxy-enabled');
    if (proxyEnabledToggle) {
      proxyEnabledToggle.checked = settings.proxy.enabled || false;
    }
    
    const proxyUrlInput = document.getElementById('proxy-url');
    if (proxyUrlInput) {
      proxyUrlInput.value = settings.proxy.url || '';
    }
    
    const proxyUsernameInput = document.getElementById('proxy-username');
    if (proxyUsernameInput) {
      proxyUsernameInput.value = settings.proxy.username || '';
    }
    
    const proxyPasswordInput = document.getElementById('proxy-password');
    if (proxyPasswordInput) {
      proxyPasswordInput.value = settings.proxy.password || '';
    }
  }
  
  // Fraud Detection Settings
  if (settings.fraud) {
    const maxDailyVerificationsInput = document.getElementById('max-daily-verifications');
    if (maxDailyVerificationsInput) {
      maxDailyVerificationsInput.value = settings.fraud.maxDailyVerifications || 0;
    }
    
    const fraudThresholdInput = document.getElementById('fraud-threshold');
    if (fraudThresholdInput) {
      fraudThresholdInput.value = settings.fraud.suspiciousThreshold || 0;
    }
    
    const autoBlockToggle = document.getElementById('auto-block-enabled');
    if (autoBlockToggle) {
      autoBlockToggle.checked = settings.fraud.autoBlockEnabled || false;
    }
  }
}

/**
 * Setup maintenance mode toggle with confirmation
 * Requirements: 5.1, 5.2
 */
function setupMaintenanceModeToggle() {
  const maintenanceModeToggle = document.getElementById('maintenance-mode');
  
  if (!maintenanceModeToggle) {
    console.warn('Maintenance mode toggle not found');
    return;
  }
  
  // Add change event listener
  maintenanceModeToggle.addEventListener('change', async (e) => {
    await handleMaintenanceModeToggle(e);
  });
}

/**
 * Handle maintenance mode toggle with confirmation
 * @param {Event} event - Change event
 * Requirements: 5.2
 */
async function handleMaintenanceModeToggle(event) {
  const toggle = event.target;
  const newState = toggle.checked;
  
  // If enabling maintenance mode, show confirmation dialog
  if (newState) {
    const confirmed = await ConfirmDialog.show(
      'Are you sure you want to enable maintenance mode? Users will not be able to use the bot while maintenance mode is active.',
      {
        title: 'Enable Maintenance Mode',
        confirmText: 'Enable',
        confirmClass: 'btn-warning'
      }
    );
    
    if (!confirmed) {
      // User cancelled, revert toggle
      toggle.checked = false;
      return;
    }
  }
  
  // Update maintenance mode via API
  try {
    LoadingSpinner.show();
    
    await apiClient.setMaintenanceMode(newState);
    
    LoadingSpinner.hide();
    Notification.success(`Maintenance mode ${newState ? 'enabled' : 'disabled'} successfully`);
    
    // Update current settings
    if (currentSettings && currentSettings.system) {
      currentSettings.system.maintenanceMode = newState;
    }
  } catch (error) {
    LoadingSpinner.hide();
    Notification.error(`Failed to update maintenance mode: ${error.message}`);
    
    // Revert toggle on error
    toggle.checked = !newState;
  }
}

/**
 * Setup save settings button
 * Requirements: 5.7
 */
function setupSaveButton() {
  const saveButton = document.getElementById('save-settings-btn');
  
  if (!saveButton) {
    console.warn('Save settings button not found');
    return;
  }
  
  // Add click event listener
  saveButton.addEventListener('click', async () => {
    await handleSaveSettings();
  });
}

/**
 * Handle saving settings
 * Requirements: 5.3, 5.4, 5.5, 5.6, 5.7
 */
async function handleSaveSettings() {
  // Validate form inputs
  const validationErrors = validateSettingsForm();
  
  if (validationErrors.length > 0) {
    Notification.error(`Please fix the following errors:\n${validationErrors.join('\n')}`);
    return;
  }
  
  // Collect settings from form
  const settings = collectSettingsFromForm();
  
  try {
    LoadingSpinner.show();
    
    // Save settings via API
    const updatedSettings = await apiClient.updateSettings(settings);
    
    LoadingSpinner.hide();
    Notification.success('Settings saved successfully');
    
    // Update current settings
    currentSettings = updatedSettings;
    
    // Re-render settings to reflect any server-side changes
    renderSettings(updatedSettings);
  } catch (error) {
    LoadingSpinner.hide();
    Notification.error(`Failed to save settings: ${error.message}`);
  }
}

/**
 * Validate settings form inputs
 * @returns {Array<string>} Array of validation error messages
 */
function validateSettingsForm() {
  const errors = [];
  
  // Validate welcome bonus (must be non-negative)
  const welcomeBonusInput = document.getElementById('welcome-bonus');
  if (welcomeBonusInput) {
    const value = parseInt(welcomeBonusInput.value);
    if (isNaN(value) || value < 0) {
      errors.push('Welcome bonus must be a non-negative number');
    }
  }
  
  // Validate verification price (must be positive)
  const verifyPriceInput = document.getElementById('verify-price');
  if (verifyPriceInput) {
    const value = parseInt(verifyPriceInput.value);
    if (isNaN(value) || value < 0) {
      errors.push('Verification price must be a non-negative number');
    }
  }
  
  // Validate VIP prices (must be positive)
  const basicPriceInput = document.getElementById('vip-basic-price');
  if (basicPriceInput) {
    const value = parseFloat(basicPriceInput.value);
    if (isNaN(value) || value < 0) {
      errors.push('VIP Basic price must be a non-negative number');
    }
  }
  
  const proPriceInput = document.getElementById('vip-pro-price');
  if (proPriceInput) {
    const value = parseFloat(proPriceInput.value);
    if (isNaN(value) || value < 0) {
      errors.push('VIP Pro price must be a non-negative number');
    }
  }
  
  const businessPriceInput = document.getElementById('vip-business-price');
  if (businessPriceInput) {
    const value = parseFloat(businessPriceInput.value);
    if (isNaN(value) || value < 0) {
      errors.push('VIP Business price must be a non-negative number');
    }
  }
  
  // Validate proxy URL (if proxy is enabled)
  const proxyEnabledToggle = document.getElementById('proxy-enabled');
  const proxyUrlInput = document.getElementById('proxy-url');
  if (proxyEnabledToggle && proxyEnabledToggle.checked && proxyUrlInput) {
    const url = proxyUrlInput.value.trim();
    if (!url) {
      errors.push('Proxy URL is required when proxy is enabled');
    } else {
      // Basic URL validation
      try {
        new URL(url);
      } catch (e) {
        errors.push('Proxy URL must be a valid URL');
      }
    }
  }
  
  // Validate max daily verifications (must be positive)
  const maxDailyVerificationsInput = document.getElementById('max-daily-verifications');
  if (maxDailyVerificationsInput) {
    const value = parseInt(maxDailyVerificationsInput.value);
    if (isNaN(value) || value < 1) {
      errors.push('Max daily verifications must be at least 1');
    }
  }
  
  // Validate fraud threshold (must be positive)
  const fraudThresholdInput = document.getElementById('fraud-threshold');
  if (fraudThresholdInput) {
    const value = parseInt(fraudThresholdInput.value);
    if (isNaN(value) || value < 1) {
      errors.push('Suspicious activity threshold must be at least 1');
    }
  }
  
  return errors;
}

/**
 * Collect settings from form inputs
 * @returns {object} Settings object
 */
function collectSettingsFromForm() {
  const settings = {
    system: {},
    bot: {
      vipPrices: {}
    },
    proxy: {},
    fraud: {}
  };
  
  // System Settings
  const maintenanceModeToggle = document.getElementById('maintenance-mode');
  if (maintenanceModeToggle) {
    settings.system.maintenanceMode = maintenanceModeToggle.checked;
  }
  
  const maintenanceMessageInput = document.getElementById('maintenance-message');
  if (maintenanceMessageInput) {
    settings.system.maintenanceMessage = maintenanceMessageInput.value.trim();
  }
  
  // Bot Configuration
  const welcomeBonusInput = document.getElementById('welcome-bonus');
  if (welcomeBonusInput) {
    settings.bot.welcomeBonus = parseInt(welcomeBonusInput.value) || 0;
  }
  
  const verifyPriceInput = document.getElementById('verify-price');
  if (verifyPriceInput) {
    settings.bot.verifyPrice = parseInt(verifyPriceInput.value) || 0;
  }
  
  // VIP Prices
  const basicPriceInput = document.getElementById('vip-basic-price');
  if (basicPriceInput) {
    settings.bot.vipPrices.basic = parseFloat(basicPriceInput.value) || 0;
  }
  
  const proPriceInput = document.getElementById('vip-pro-price');
  if (proPriceInput) {
    settings.bot.vipPrices.pro = parseFloat(proPriceInput.value) || 0;
  }
  
  const businessPriceInput = document.getElementById('vip-business-price');
  if (businessPriceInput) {
    settings.bot.vipPrices.business = parseFloat(businessPriceInput.value) || 0;
  }
  
  // Proxy Settings
  const proxyEnabledToggle = document.getElementById('proxy-enabled');
  if (proxyEnabledToggle) {
    settings.proxy.enabled = proxyEnabledToggle.checked;
  }
  
  const proxyUrlInput = document.getElementById('proxy-url');
  if (proxyUrlInput) {
    settings.proxy.url = proxyUrlInput.value.trim();
  }
  
  const proxyUsernameInput = document.getElementById('proxy-username');
  if (proxyUsernameInput) {
    settings.proxy.username = proxyUsernameInput.value.trim();
  }
  
  const proxyPasswordInput = document.getElementById('proxy-password');
  if (proxyPasswordInput) {
    settings.proxy.password = proxyPasswordInput.value.trim();
  }
  
  // Fraud Detection Settings
  const maxDailyVerificationsInput = document.getElementById('max-daily-verifications');
  if (maxDailyVerificationsInput) {
    settings.fraud.maxDailyVerifications = parseInt(maxDailyVerificationsInput.value) || 0;
  }
  
  const fraudThresholdInput = document.getElementById('fraud-threshold');
  if (fraudThresholdInput) {
    settings.fraud.suspiciousThreshold = parseInt(fraudThresholdInput.value) || 0;
  }
  
  const autoBlockToggle = document.getElementById('auto-block-enabled');
  if (autoBlockToggle) {
    settings.fraud.autoBlockEnabled = autoBlockToggle.checked;
  }
  
  return settings;
}

/**
 * Load settings and render form
 */
async function loadSettings() {
  try {
    const settings = await fetchSettings();
    renderSettings(settings);
  } catch (error) {
    console.error('Failed to load settings:', error);
  }
}

// Export functions for global access
if (typeof window !== 'undefined') {
  window.initSettingsManagement = initSettingsManagement;
  window.fetchSettings = fetchSettings;
  window.renderSettings = renderSettings;
  window.handleMaintenanceModeToggle = handleMaintenanceModeToggle;
  window.handleSaveSettings = handleSaveSettings;
  window.validateSettingsForm = validateSettingsForm;
  window.collectSettingsFromForm = collectSettingsFromForm;
  window.loadSettings = loadSettings;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    initSettingsManagement,
    fetchSettings,
    renderSettings,
    handleMaintenanceModeToggle,
    handleSaveSettings,
    validateSettingsForm,
    collectSettingsFromForm,
    loadSettings
  };
}
