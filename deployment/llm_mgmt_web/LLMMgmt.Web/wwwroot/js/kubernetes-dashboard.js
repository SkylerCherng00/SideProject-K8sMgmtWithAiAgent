/**
 * Kubernetes Dashboard JavaScript
 * Handles pod metrics visualization and real-time updates
 */

// Global variables
let podMetricsData = {};
let refreshInterval;
let charts = {};
let isRefreshing = false;

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Kubernetes Dashboard initializing...');
    
    // Check if we're on the Kubernetes dashboard page
    if (!document.getElementById('summaryCards')) {
        console.log('Not on Kubernetes dashboard page');
        return;
    }

    // Initialize dashboard
    initializeDashboard();
    startAutoRefresh();
    
    console.log('Kubernetes Dashboard initialized successfully');
});

/**
 * Get property value with fallback for different naming conventions
 */
function getPropertyValue(obj, propName) {
    if (!obj) return undefined;
    
    // Try camelCase first (for .NET JSON serialization)
    if (obj.hasOwnProperty(propName)) {
        return obj[propName];
    }
    
    // Try snake_case (for raw API response)
    const snakeCase = propName.replace(/([A-Z])/g, '_$1').toLowerCase();
    if (obj.hasOwnProperty(snakeCase)) {
        return obj[snakeCase];
    }
    
    // Try lowercase
    const lowerCase = propName.toLowerCase();
    if (obj.hasOwnProperty(lowerCase)) {
        return obj[lowerCase];
    }
    
    return undefined;
}

/**
 * Initialize the dashboard with current data
 */
function initializeDashboard() {
    try {
        // Get initial data from server-side rendering
        const initialDataElement = document.getElementById('initial-pod-data');
        if (initialDataElement) {
            try {
                const initialData = JSON.parse(initialDataElement.textContent);
                podMetricsData = initialData || {};
                
                // Debug: Log the structure of the first pod to understand the data format
                const firstNamespace = Object.keys(podMetricsData)[0];
                if (firstNamespace && podMetricsData[firstNamespace] && podMetricsData[firstNamespace].length > 0) {
                    const firstPod = podMetricsData[firstNamespace][0];
                    console.log('First pod data structure:', firstPod);
                    console.log('Available properties:', Object.keys(firstPod));
                    
                    // Check specific properties
                    console.log('netIn property:', getPropertyValue(firstPod, 'netIn'));
                    console.log('net_in property:', getPropertyValue(firstPod, 'net_in'));
                    console.log('netOut property:', getPropertyValue(firstPod, 'netOut'));
                    console.log('net_out property:', getPropertyValue(firstPod, 'net_out'));
                    console.log('podStatus property:', getPropertyValue(firstPod, 'podStatus'));
                    console.log('pod_status property:', getPropertyValue(firstPod, 'pod_status'));
                }
            } catch (parseError) {
                console.error('Error parsing initial data:', parseError);
                console.log('Initial data element content:', initialDataElement.textContent);
                podMetricsData = {};
            }
        } else {
            console.log('No initial data element found, starting with empty data');
            podMetricsData = {};
        }
        
        // Always update the dashboard, even with empty data
        updateSummaryCards();
        createNamespaceTabs();
        updateLastRefreshTime();
        
        // If we have no data, try to fetch from API
        if (Object.keys(podMetricsData).length === 0) {
            console.log('No initial data found, attempting to fetch from API...');
            setTimeout(() => {
                refreshData();
            }, 1000);
        }
        
        console.log('Dashboard initialized with data:', podMetricsData);
    } catch (error) {
        console.error('Error initializing dashboard:', error);
        showErrorState('Failed to initialize dashboard: ' + error.message);
    }
}

/**
 * Update summary cards with latest metrics
 */
function updateSummaryCards() {
    try {
        let totalPods = 0;
        let runningPods = 0;
        let totalCpu = 0;
        let podCount = 0;

        Object.keys(podMetricsData).forEach(namespace => {
            if (podMetricsData[namespace] && Array.isArray(podMetricsData[namespace])) {
                podMetricsData[namespace].forEach(pod => {
                    totalPods++;
                    
                    // Check pod status with property fallback
                    const podStatus = getPropertyValue(pod, 'podStatus') || getPropertyValue(pod, 'pod_status');
                    if (podStatus && podStatus.length > 0 && podStatus[podStatus.length - 1] === 1.0) {
                        runningPods++;
                    }
                    
                    // Check CPU with property fallback
                    const cpu = getPropertyValue(pod, 'cpu');
                    if (cpu && cpu.length > 0) {
                        totalCpu += cpu[cpu.length - 1];
                        podCount++;
                    }
                });
            }
        });

        // Update UI elements
        const totalPodsElement = document.getElementById('totalPods');
        const runningPodsElement = document.getElementById('runningPods');
        const totalNamespacesElement = document.getElementById('totalNamespaces');
        const avgCpuUsageElement = document.getElementById('avgCpuUsage');

        if (totalPodsElement) totalPodsElement.textContent = totalPods;
        if (runningPodsElement) runningPodsElement.textContent = runningPods;
        if (totalNamespacesElement) totalNamespacesElement.textContent = Object.keys(podMetricsData).length;
        if (avgCpuUsageElement) {
            const avgCpu = podCount > 0 ? (totalCpu / podCount).toFixed(3) : '0';
            avgCpuUsageElement.textContent = avgCpu + ' cores';
        }

        console.log('Summary cards updated:', { totalPods, runningPods, totalCpu, podCount });
    } catch (error) {
        console.error('Error updating summary cards:', error);
    }
}

/**
 * Create namespace tabs and content
 */
function createNamespaceTabs() {
    try {
        const tabsContainer = document.getElementById('namespaceTabs');
        const contentContainer = document.getElementById('namespaceTabContent');
        
        if (!tabsContainer || !contentContainer) {
            console.error('Tab containers not found');
            return;
        }

        // Clear existing content and remove loading state
        tabsContainer.innerHTML = '';
        contentContainer.innerHTML = '';
        
        // Hide the initial loading state
        const initialLoadingState = document.getElementById('initialLoadingState');
        if (initialLoadingState) {
            initialLoadingState.style.display = 'none';
        }

        const namespaces = Object.keys(podMetricsData);
        console.log('Processing namespaces:', namespaces);
        
        if (namespaces.length === 0) {
            console.log('No namespaces found, showing no data state');
            showNoDataState();
            return;
        }

        let isFirst = true;
        namespaces.forEach(namespace => {
            const pods = podMetricsData[namespace];
            console.log(`Processing namespace ${namespace} with ${pods?.length || 0} pods`);
            
            if (!pods || !Array.isArray(pods)) {
                console.warn(`Invalid pods data for namespace ${namespace}:`, pods);
                return;
            }

            // Create tab
            const tabId = `tab-${namespace}`;
            const contentId = `content-${namespace}`;
            
            const tab = document.createElement('li');
            tab.className = 'nav-item';
            tab.innerHTML = `
                <a class="nav-link ${isFirst ? 'active' : ''}" id="${tabId}" data-bs-toggle="tab" 
                   href="#${contentId}" role="tab" aria-controls="${contentId}" aria-selected="${isFirst}">
                    ${namespace} (${pods.length})
                </a>
            `;
            tabsContainer.appendChild(tab);

            // Create content
            const content = document.createElement('div');
            content.className = `tab-pane fade ${isFirst ? 'show active' : ''}`;
            content.id = contentId;
            content.setAttribute('role', 'tabpanel');
            content.setAttribute('aria-labelledby', tabId);
            
            content.innerHTML = createNamespaceContent(namespace, pods);
            contentContainer.appendChild(content);

            isFirst = false;
        });

        // Initialize charts after content is created
        setTimeout(() => {
            console.log('Initializing charts for namespaces...');
            namespaces.forEach(namespace => {
                const pods = podMetricsData[namespace];
                if (pods && Array.isArray(pods)) {
                    console.log(`Creating charts for namespace ${namespace} with ${pods.length} pods`);
                    createChartsForNamespace(namespace, pods);
                }
            });
        }, 100);
    } catch (error) {
        console.error('Error creating namespace tabs:', error);
        showErrorState('Failed to create namespace tabs: ' + error.message);
    }
}

/**
 * Create HTML content for a namespace
 */
function createNamespaceContent(namespace, pods) {
    try {
        if (!pods || !Array.isArray(pods) || pods.length === 0) {
            return `
                <div class="no-data-state">
                    <i class="fas fa-inbox"></i>
                    <h5>No pods found in namespace "${namespace}"</h5>
                </div>
            `;
        }

        let content = `
            <div class="metrics-grid">
                <div class="metric-card">
                    <h6><i class="fas fa-chart-line"></i> CPU Usage Trends</h6>
                    <div class="chart-container">
                        <canvas id="cpuChart-${namespace}"></canvas>
                    </div>
                </div>
                <div class="metric-card">
                    <h6><i class="fas fa-memory"></i> Memory Usage Trends</h6>
                    <div class="chart-container">
                        <canvas id="memChart-${namespace}"></canvas>
                    </div>
                </div>
                <div class="metric-card">
                    <h6><i class="fas fa-network-wired"></i> Network I/O</h6>
                    <div class="chart-container">
                        <canvas id="networkChart-${namespace}"></canvas>
                    </div>
                </div>
                <div class="metric-card">
                    <h6><i class="fas fa-heartbeat"></i> Pod Status</h6>
                    <div class="chart-container">
                        <canvas id="statusChart-${namespace}"></canvas>
                    </div>
                </div>
            </div>
            <div class="card">
                <div class="card-header">
                    <h6><i class="fas fa-table"></i> Pod Details</h6>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-striped table-hover">
                            <thead>
                                <tr>
                                    <th>Pod Name</th>
                                    <th>Service</th>
                                    <th>Node</th>
                                    <th>CPU (cores)</th>
                                    <th>Memory (MB)</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
        `;

        pods.forEach(pod => {
            const cpu = getPropertyValue(pod, 'cpu');
            const mem = getPropertyValue(pod, 'mem');
            const podStatus = getPropertyValue(pod, 'podStatus') || getPropertyValue(pod, 'pod_status');
            
            const latestCpu = cpu && cpu.length > 0 ? cpu[cpu.length - 1].toFixed(3) : 'N/A';
            const latestMem = mem && mem.length > 0 ? (mem[mem.length - 1] / 1024 / 1024).toFixed(1) : 'N/A';
            const latestStatus = podStatus && podStatus.length > 0 ? podStatus[podStatus.length - 1] : 0;
            const statusBadge = latestStatus === 1.0 ? 
                '<span class="badge status-running">Running</span>' : 
                '<span class="badge status-not-running">Not Running</span>';

            const podName = getPropertyValue(pod, 'pod') || 'Unknown';
            const service = getPropertyValue(pod, 'service') || 'N/A';
            const node = getPropertyValue(pod, 'node') || 'N/A';

            content += `
                <tr>
                    <td><strong>${escapeHtml(podName)}</strong></td>
                    <td>${escapeHtml(service)}</td>
                    <td>${escapeHtml(node)}</td>
                    <td>${latestCpu}</td>
                    <td>${latestMem}</td>
                    <td>${statusBadge}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="showPodDetails('${escapeHtml(podName)}', '${escapeHtml(namespace)}')">
                            <i class="fas fa-chart-bar"></i> Details
                        </button>
                    </td>
                </tr>
            `;
        });

        content += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;

        return content;
    } catch (error) {
        console.error('Error creating namespace content:', error);
        return `<div class="error-state"><i class="fas fa-exclamation-triangle"></i> Error loading content</div>`;
    }
}

/**
 * Create charts for a namespace
 */
function createChartsForNamespace(namespace, pods) {
    try {
        if (!pods || !Array.isArray(pods) || pods.length === 0) return;

        const timeLabels = ['T-2min', 'T-1min', 'T-now'];
        
        // CPU Chart
        createCpuChart(namespace, pods, timeLabels);
        
        // Memory Chart
        createMemoryChart(namespace, pods, timeLabels);
        
        // Network Chart
        createNetworkChart(namespace, pods, timeLabels);
        
        // Status Chart
        createStatusChart(namespace, pods);
        
        console.log(`Charts created for namespace: ${namespace}`);
    } catch (error) {
        console.error(`Error creating charts for namespace ${namespace}:`, error);
    }
}

/**
 * Create CPU usage chart
 */
function createCpuChart(namespace, pods, timeLabels) {
    const cpuCtx = document.getElementById(`cpuChart-${namespace}`);
    if (!cpuCtx) return;

    const cpuData = {
        labels: timeLabels,
        datasets: pods.map((pod, index) => {
            const cpu = getPropertyValue(pod, 'cpu');
            const podName = getPropertyValue(pod, 'pod') || 'Unknown';
            
            return {
                label: podName,
                data: cpu || [],
                borderColor: `hsl(${index * 360 / pods.length}, 70%, 50%)`,
                backgroundColor: `hsla(${index * 360 / pods.length}, 70%, 50%, 0.1)`,
                tension: 0.1,
                pointRadius: 3,
                pointHoverRadius: 5
            };
        })
    };

    charts[`cpu-${namespace}`] = new Chart(cpuCtx, {
        type: 'line',
        data: cpuData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'CPU Usage (cores)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: pods.length <= 10
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        }
    });
}

/**
 * Create memory usage chart
 */
function createMemoryChart(namespace, pods, timeLabels) {
    const memCtx = document.getElementById(`memChart-${namespace}`);
    if (!memCtx) return;

    const memData = {
        labels: timeLabels,
        datasets: pods.map((pod, index) => {
            const mem = getPropertyValue(pod, 'mem');
            const podName = getPropertyValue(pod, 'pod') || 'Unknown';
            
            return {
                label: podName,
                data: (mem || []).map(val => val / 1024 / 1024),
                borderColor: `hsl(${index * 360 / pods.length}, 70%, 50%)`,
                backgroundColor: `hsla(${index * 360 / pods.length}, 70%, 50%, 0.1)`,
                tension: 0.1,
                pointRadius: 3,
                pointHoverRadius: 5
            };
        })
    };

    charts[`mem-${namespace}`] = new Chart(memCtx, {
        type: 'line',
        data: memData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Memory Usage (MB)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: pods.length <= 10
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        }
    });
}

/**
 * Create network I/O chart
 */
function createNetworkChart(namespace, pods, timeLabels) {
    const networkCtx = document.getElementById(`networkChart-${namespace}`);
    if (!networkCtx) return;

    const networkData = {
        labels: timeLabels,
        datasets: []
    };

    pods.forEach((pod, index) => {
        const baseColor = `hsl(${index * 360 / pods.length}, 70%, 50%)`;
        const podName = getPropertyValue(pod, 'pod') || 'Unknown';
        
        // Try both camelCase and snake_case property names
        const netIn = getPropertyValue(pod, 'netIn') || getPropertyValue(pod, 'net_in');
        const netOut = getPropertyValue(pod, 'netOut') || getPropertyValue(pod, 'net_out');
        
        console.log(`Pod ${podName} - netIn:`, netIn, 'netOut:', netOut); // Debug log
        
        if (netIn && Array.isArray(netIn)) {
            networkData.datasets.push({
                label: `${podName} (In)`,
                data: netIn.map(val => val / 1024 / 1024),
                borderColor: baseColor,
                backgroundColor: baseColor.replace('50%', '10%'),
                tension: 0.1,
                pointRadius: 3,
                pointHoverRadius: 5
            });
        }
        
        if (netOut && Array.isArray(netOut)) {
            networkData.datasets.push({
                label: `${podName} (Out)`,
                data: netOut.map(val => val / 1024 / 1024),
                borderColor: baseColor,
                backgroundColor: baseColor.replace('50%', '10%'),
                borderDash: [5, 5],
                tension: 0.1,
                pointRadius: 3,
                pointHoverRadius: 5
            });
        }
    });

    console.log('Network chart data:', networkData); // Debug log

    charts[`network-${namespace}`] = new Chart(networkCtx, {
        type: 'line',
        data: networkData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Network I/O (MB)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: pods.length <= 5
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        }
    });
}

/**
 * Create status chart
 */
function createStatusChart(namespace, pods) {
    const statusCtx = document.getElementById(`statusChart-${namespace}`);
    if (!statusCtx) return;

    const runningCount = pods.filter(p => {
        const podStatus = getPropertyValue(p, 'podStatus') || getPropertyValue(p, 'pod_status');
        return podStatus && podStatus.length > 0 && podStatus[podStatus.length - 1] === 1.0;
    }).length;
    
    const notRunningCount = pods.length - runningCount;

    console.log(`Status chart for ${namespace} - Running: ${runningCount}, Not Running: ${notRunningCount}`); // Debug log

    charts[`status-${namespace}`] = new Chart(statusCtx, {
        type: 'doughnut',
        data: {
            labels: ['Running', 'Not Running'],
            datasets: [{
                data: [runningCount, notRunningCount],
                backgroundColor: ['#28a745', '#dc3545'],
                borderWidth: 2,
                hoverBorderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((context.parsed / total) * 100).toFixed(1) : '0';
                            return `${context.label}: ${context.parsed} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Show pod details modal
 */
function showPodDetails(podName, namespace) {
    try {
        const pod = podMetricsData[namespace]?.find(p => {
            const name = getPropertyValue(p, 'pod');
            return name === podName;
        });
        
        if (!pod) {
            console.error(`Pod ${podName} not found in namespace ${namespace}`);
            return;
        }

        const modal = new bootstrap.Modal(document.getElementById('podDetailsModal'));
        const modalLabel = document.getElementById('podDetailsModalLabel');
        const modalContent = document.getElementById('podDetailsContent');

        if (modalLabel) modalLabel.textContent = `Pod Details: ${podName}`;
        
        const cpu = getPropertyValue(pod, 'cpu');
        const mem = getPropertyValue(pod, 'mem');
        const netIn = getPropertyValue(pod, 'netIn') || getPropertyValue(pod, 'net_in');
        const netOut = getPropertyValue(pod, 'netOut') || getPropertyValue(pod, 'net_out');
        const podStatus = getPropertyValue(pod, 'podStatus') || getPropertyValue(pod, 'pod_status');
        const podNamespace = getPropertyValue(pod, 'namespace') || namespace;
        const service = getPropertyValue(pod, 'service') || 'N/A';
        const node = getPropertyValue(pod, 'node') || 'N/A';
        
        // Get latest values
        const latestCpu = cpu && cpu.length > 0 ? cpu[cpu.length - 1].toFixed(3) : 'N/A';
        const latestMem = mem && mem.length > 0 ? (mem[mem.length - 1] / 1024 / 1024).toFixed(1) : 'N/A';
        const latestStatus = podStatus && podStatus.length > 0 ? podStatus[podStatus.length - 1] : 0;
        const statusBadge = latestStatus === 1.0 ? 
            '<span class="badge bg-success">Running</span>' : 
            '<span class="badge bg-danger">Not Running</span>';
        
        const content = `
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h6><i class="fas fa-info-circle"></i> Pod Information</h6>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-striped">
                                    <thead>
                                        <tr>
                                            <th>Pod Name</th>
                                            <th>Service</th>
                                            <th>Node</th>
                                            <th>CPU</th>
                                            <th>MEM</th>
                                            <th>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td><strong>${escapeHtml(podName)}</strong></td>
                                            <td>${escapeHtml(service)}</td>
                                            <td>${escapeHtml(node)}</td>
                                            <td>${latestCpu} cores</td>
                                            <td>${latestMem} MB</td>
                                            <td>${statusBadge}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h6><i class="fas fa-server"></i> Basic Information</h6>
                        </div>
                        <div class="card-body">
                            <p><strong>Name:</strong> ${escapeHtml(podName)}</p>
                            <p><strong>Namespace:</strong> ${escapeHtml(podNamespace)}</p>
                            <p><strong>Service:</strong> ${escapeHtml(service)}</p>
                            <p><strong>Node:</strong> ${escapeHtml(node)}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h6><i class="fas fa-chart-bar"></i> Current Metrics</h6>
                        </div>
                        <div class="card-body">
                            <p><strong>CPU:</strong> ${latestCpu} cores</p>
                            <p><strong>Memory:</strong> ${latestMem} MB</p>
                            <p><strong>Network In:</strong> ${netIn && netIn.length > 0 ? (netIn[netIn.length - 1] / 1024 / 1024).toFixed(1) + ' MB' : 'N/A'}</p>
                            <p><strong>Network Out:</strong> ${netOut && netOut.length > 0 ? (netOut[netOut.length - 1] / 1024 / 1024).toFixed(1) + ' MB' : 'N/A'}</p>
                            <p><strong>Status:</strong> ${statusBadge}</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h6><i class="fas fa-chart-line"></i> Metrics History</h6>
                        </div>
                        <div class="card-body">
                            <div class="chart-container">
                                <canvas id="podDetailChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        if (modalContent) modalContent.innerHTML = content;
        modal.show();

        // Create detailed chart
        setTimeout(() => {
            const ctx = document.getElementById('podDetailChart');
            if (ctx) {
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: ['T-2min', 'T-1min', 'T-now'],
                        datasets: [
                            {
                                label: 'CPU Usage (cores)',
                                data: cpu || [],
                                borderColor: 'rgb(255, 99, 132)',
                                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                                yAxisID: 'y',
                                tension: 0.1
                            },
                            {
                                label: 'Memory Usage (MB)',
                                data: (mem || []).map(val => val / 1024 / 1024),
                                borderColor: 'rgb(54, 162, 235)',
                                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                                yAxisID: 'y1',
                                tension: 0.1
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                type: 'linear',
                                display: true,
                                position: 'left',
                                title: {
                                    display: true,
                                    text: 'CPU Usage (cores)'
                                }
                            },
                            y1: {
                                type: 'linear',
                                display: true,
                                position: 'right',
                                title: {
                                    display: true,
                                    text: 'Memory Usage (MB)'
                                },
                                grid: {
                                    drawOnChartArea: false,
                                }
                            }
                        }
                    }
                });
            }
        }, 100);
    } catch (error) {
        console.error('Error showing pod details:', error);
    }
}

/**
 * Refresh data from server
 */
function refreshData() {
    if (isRefreshing) {
        console.log('Refresh already in progress');
        return;
    }

    isRefreshing = true;
    const refreshButton = document.getElementById('refreshPods');
    
    // Show loading state
    if (refreshButton) {
        refreshButton.disabled = true;
        refreshButton.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> Refreshing...';
    }
    
    console.log('Starting data refresh...');

    fetch('/Kubernetes/GetPodMetrics')
        .then(response => {
            console.log('Received response:', response.status, response.statusText);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Received data:', data);
            
            if (data.success) {
                // Hide error block on successful refresh
                hideErrorBlock();
                
                // Show success message
                showSuccessMessage('Data refreshed successfully');
                
                podMetricsData = data.data.namespaces || {};
                console.log('Updated podMetricsData:', podMetricsData);
                
                // Destroy existing charts
                console.log('Destroying existing charts...');
                Object.values(charts).forEach(chart => {
                    if (chart && typeof chart.destroy === 'function') {
                        chart.destroy();
                    }
                });
                charts = {};
                
                // Reinitialize dashboard
                console.log('Reinitializing dashboard...');
                updateSummaryCards();
                createNamespaceTabs();
                updateLastRefreshTime();
                
                console.log('Data refreshed successfully');
            } else {
                console.error('Error fetching data:', data.error);
                showErrorState('Failed to refresh data: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error refreshing data:', error);
            showErrorState('Network error: ' + error.message);
        })
        .finally(() => {
            isRefreshing = false;
            if (refreshButton) {
                refreshButton.disabled = false;
                refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
            }
        });
}

/**
 * Update last refresh time
 */
function updateLastRefreshTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    const lastUpdateElement = document.getElementById('lastUpdate');
    if (lastUpdateElement) {
        lastUpdateElement.textContent = `Last updated: ${timeString}`;
    }
}

/**
 * Start auto refresh
 */
function startAutoRefresh() {
    // Clear existing interval
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    // Refresh every 60 seconds
    refreshInterval = setInterval(() => {
        refreshData();
    }, 60000);
    
    console.log('Auto refresh started (60 seconds interval)');
}

/**
 * Stop auto refresh
 */
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
        console.log('Auto refresh stopped');
    }
}

/**
 * Show error state
 */
function showErrorState(message) {
    const contentContainer = document.getElementById('namespaceTabContent');
    if (contentContainer) {
        contentContainer.innerHTML = `
            <div class="error-state">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Error:</strong> ${escapeHtml(message)}
            </div>
        `;
    }
}

/**
 * Show no data state
 */
function showNoDataState() {
    const contentContainer = document.getElementById('namespaceTabContent');
    if (contentContainer) {
        contentContainer.innerHTML = `
            <div class="no-data-state">
                <i class="fas fa-inbox"></i>
                <h5>No pod data available</h5>
                <p>Check your API connection or refresh the page.</p>
            </div>
        `;
    }
}

/**
 * Hide error block when API call is successful
 */
function hideErrorBlock() {
    const errorBlock = document.querySelector('.alert-danger');
    if (errorBlock) {
        errorBlock.style.display = 'none';
        console.log('Error block hidden after successful API call');
    }
}

/**
 * Show success message temporarily
 */
function showSuccessMessage(message) {
    // Remove existing success message
    const existingSuccess = document.querySelector('.alert-success.temp-success');
    if (existingSuccess) {
        existingSuccess.remove();
    }
    
    // Create new success message
    const successDiv = document.createElement('div');
    successDiv.className = 'alert alert-success temp-success';
    successDiv.innerHTML = `<strong>Success:</strong> ${message}`;
    
    // Insert after the header
    const header = document.querySelector('.d-flex.justify-content-between.align-items-center.mb-4');
    if (header) {
        header.parentNode.insertBefore(successDiv, header.nextSibling);
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            if (successDiv.parentNode) {
                successDiv.remove();
            }
        }, 3000);
    }
}

/**
 * Debug API connection
 */
function debugApi() {
    const debugButton = document.getElementById('debugApi');
    
    if (debugButton) {
        debugButton.disabled = true;
        debugButton.innerHTML = '<i class="fas fa-bug fa-spin"></i> Testing...';
    }
    
    fetch('/Kubernetes/DebugApi')
        .then(response => response.json())
        .then(data => {
            console.log('Debug API response:', data);
            
            if (data.success) {
                // Hide error block on success
                hideErrorBlock();
                
                // Show success message
                showSuccessMessage('API connection test successful');
                
                // If we received data, update the dashboard
                if (data.parsedData && data.parsedData.namespaces) {
                    podMetricsData = data.parsedData.namespaces;
                    
                    // Destroy existing charts
                    Object.values(charts).forEach(chart => {
                        if (chart && typeof chart.destroy === 'function') {
                            chart.destroy();
                        }
                    });
                    charts = {};
                    
                    // Reinitialize dashboard
                    updateSummaryCards();
                    createNamespaceTabs();
                    updateLastRefreshTime();
                    
                    console.log('Dashboard updated with debug API data');
                }
                
                alert(`API Debug Results:
- Raw API call time: ${data.rawCallTime}ms
- Parsed API call time: ${data.parsedCallTime}ms
- Raw response length: ${data.rawResponseLength} characters
- Namespace count: ${data.namespaceCount}
- Total pods: ${data.totalPods}

Check console for full response details.`);
            } else {
                alert(`API Debug Error: ${data.error}`);
                console.error('Debug API error:', data);
            }
        })
        .catch(error => {
            console.error('Debug API request failed:', error);
            alert(`Debug API request failed: ${error.message}`);
        })
        .finally(() => {
            if (debugButton) {
                debugButton.disabled = false;
                debugButton.innerHTML = '<i class="fas fa-bug"></i> Debug API';
            }
        });
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    const refreshButton = document.getElementById('refreshPods');
    if (refreshButton) {
        refreshButton.addEventListener('click', refreshData);
    }
    
    const debugButton = document.getElementById('debugApi');
    if (debugButton) {
        debugButton.addEventListener('click', debugApi);
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
    Object.values(charts).forEach(chart => {
        if (chart && typeof chart.destroy === 'function') {
            chart.destroy();
        }
    });
});

// Make functions available globally
window.showPodDetails = showPodDetails;
window.refreshData = refreshData;window.refreshData = refreshData;