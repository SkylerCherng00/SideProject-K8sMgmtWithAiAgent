// kubernetes-logs.js - Client-side functionality for the Kubernetes logs page
document.addEventListener('DOMContentLoaded', function () {
    // Initialize components
    initLabelSelector();
    initLabelButtons();
    initTimeControls();
    initButtons();

    // Set up auto-refresh if needed
    // setupAutoRefresh();
});

function initLabelSelector() {
    // Handle label selection from dropdown
    document.querySelectorAll('#labelSelector .label-value').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const label = this.getAttribute('data-label');
            const value = this.getAttribute('data-value');
            
            addLabelToQuery(label, value);
        });
    });
}

function initLabelButtons() {
    // Handle label button clicks from the tabbed interface
    document.querySelectorAll('.label-value-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const label = this.getAttribute('data-label');
            const value = this.getAttribute('data-value');
            
            addLabelToQuery(label, value);
        });
    });
    
    // Toggle button states for active tabs
    const tabsEl = document.getElementById('labelsTab');
    if (tabsEl) {
        const triggerTabList = tabsEl.querySelectorAll('button');
        triggerTabList.forEach(triggerEl => {
            triggerEl.addEventListener('click', event => {
                event.preventDefault();
                // Mark as selected in the UI
                triggerTabList.forEach(tab => tab.setAttribute('aria-selected', 'false'));
                triggerEl.setAttribute('aria-selected', 'true');
            });
        });
    }
}

function addLabelToQuery(label, value) {
    const queryInput = document.getElementById('Query');
    const currentValue = queryInput.value || '';
    
    // Format: {label="value"}
    const labelExpression = `{${label}="${value}"}`;
    
    // If there's already content, check if we need to replace or append
    if (currentValue.trim()) {
        // Check if the query already contains a filter for this label
        const labelRegex = new RegExp(`{[^}]*${label}\\s*=\\s*"[^"]*"[^}]*}`);
        if (labelRegex.test(currentValue)) {
            // Replace existing label expression
            queryInput.value = currentValue.replace(labelRegex, labelExpression);
        } else {
            // Just append new expression
            queryInput.value = `${currentValue} ${labelExpression}`;
        }
    } else {
        queryInput.value = labelExpression;
    }
    
    // Focus the input for better UX
    queryInput.focus();
}

function initTimeControls() {
    // Initialize default time values if empty
    const startTimeInput = document.getElementById('StartTime');
    const endTimeInput = document.getElementById('EndTime');
    
    if (!startTimeInput.value) {
        const oneHourAgo = new Date();
        oneHourAgo.setHours(oneHourAgo.getHours() - 1);
        startTimeInput.value = formatDateTime(oneHourAgo);
    }
    
    if (!endTimeInput.value) {
        endTimeInput.value = formatDateTime(new Date());
    }
    
    // Add quick time selection buttons if needed
    // addQuickTimeSelectors();
}

function initButtons() {
    // Refresh button handler
    const refreshButton = document.getElementById('refreshButton');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            document.getElementById('logQueryForm').submit();
        });
    }
    
    // Copy logs button
    const copyLogsBtn = document.getElementById('copyLogsBtn');
    if (copyLogsBtn) {
        copyLogsBtn.addEventListener('click', function() {
            const logsTable = document.getElementById('logsTable');
            if (!logsTable) return;
            
            let logText = '';
            logsTable.querySelectorAll('tbody tr').forEach(row => {
                const timestamp = row.querySelector('td:first-child').textContent.trim();
                const logMessage = row.querySelector('.log-message').textContent.trim();
                logText += `[${timestamp}] ${logMessage}\n`;
            });
            
            if (logText) {
                navigator.clipboard.writeText(logText).then(() => {
                    alert('Logs copied to clipboard!');
                }).catch(err => {
                    console.error('Could not copy logs: ', err);
                });
            }
        });
    }
    
    // Download logs button
    const downloadLogsBtn = document.getElementById('downloadLogsBtn');
    if (downloadLogsBtn) {
        downloadLogsBtn.addEventListener('click', function() {
            const logsTable = document.getElementById('logsTable');
            if (!logsTable) return;
            
            let logText = '';
            logsTable.querySelectorAll('tbody tr').forEach(row => {
                const timestamp = row.querySelector('td:first-child').textContent.trim();
                const logMessage = row.querySelector('.log-message').textContent.trim();
                logText += `[${timestamp}] ${logMessage}\n`;
            });
            
            if (logText) {
                const blob = new Blob([logText], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                const query = document.getElementById('Query').value || 'logs';
                const sanitizedQuery = query.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 20);
                const now = new Date();
                const timestamp = formatDateTime(now).replace(/[^0-9]/g, '');
                
                a.href = url;
                a.download = `${sanitizedQuery}-${timestamp}.log`;
                a.click();
                
                // Clean up
                URL.revokeObjectURL(url);
            }
        });
    }
    
    // Show labels on page load if there's a query
    const queryInput = document.getElementById('Query');
    if (queryInput && queryInput.value) {
        const labelsCollapse = document.getElementById('labelsCollapse');
        if (labelsCollapse) {
            new bootstrap.Collapse(labelsCollapse, {
                toggle: true
            });
        }
    }
}

function formatDateTime(date) {
    // Format date as YYYY-MM-DD HH:MM:SS
    return `${date.getFullYear()}-${padZero(date.getMonth() + 1)}-${padZero(date.getDate())} ${padZero(date.getHours())}:${padZero(date.getMinutes())}:${padZero(date.getSeconds())}`;
}

function padZero(num) {
    return num.toString().padStart(2, '0');
}

// Optional: Add live refresh functionality
function setupAutoRefresh() {
    let isAutoRefreshEnabled = false;
    let refreshInterval = null;
    
    const toggleAutoRefresh = document.getElementById('toggleAutoRefresh');
    if (toggleAutoRefresh) {
        toggleAutoRefresh.addEventListener('click', function() {
            if (isAutoRefreshEnabled) {
                // Disable auto-refresh
                clearInterval(refreshInterval);
                this.textContent = 'Enable Auto-Refresh';
                this.classList.replace('btn-danger', 'btn-success');
            } else {
                // Enable auto-refresh (every 10 seconds)
                refreshInterval = setInterval(refreshLogs, 10000);
                this.textContent = 'Disable Auto-Refresh';
                this.classList.replace('btn-success', 'btn-danger');
            }
            isAutoRefreshEnabled = !isAutoRefreshEnabled;
        });
    }
}

// Function to refresh logs via AJAX
function refreshLogs() {
    const query = document.getElementById('Query').value;
    const startTime = document.getElementById('StartTime').value;
    const endTime = document.getElementById('EndTime').value;
    const limit = document.getElementById('Limit').value;
    
    if (!query) return;
    
    const request = {
        query: query,
        startTime: startTime,
        endTime: endTime,
        limit: parseInt(limit, 10)
    };
    
    fetch('/Kubernetes/GetLogs', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(request)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.data && data.data.values && data.data.values.length > 0) {
            updateLogsTable(data.data);
        }
    })
    .catch(error => console.error('Error refreshing logs:', error));
}

function updateLogsTable(logData) {
    const tableBody = document.querySelector('#logsTable tbody');
    if (!tableBody) return;
    
    // Clear existing rows
    tableBody.innerHTML = '';
    
    // Add new rows
    logData.values.forEach(entry => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="text-nowrap">${entry.timestamp}</td>
            <td><pre class="mb-0 log-message">${escapeHtml(entry.log)}</pre></td>
        `;
        tableBody.appendChild(row);
    });
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}