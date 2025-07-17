/**
 * K8s Analyzer Module - Handles the Kubernetes cluster analysis functionality
 */
const k8sAnalyzer = (function() {
    'use strict';

    // Cache DOM elements
    let $analyzeBtn;
    let $analysisContainer;
    let $analysisContent;
    let $analysisResult;
    let $loadingIndicator;
    let $errorMessage;
    let $toggleBtn;
    
    // Initialize the module
    function init() {
        // Get DOM elements
        $analyzeBtn = document.getElementById('analyzeK8sBtn');
        $analysisContainer = document.getElementById('k8sAnalysisContainer');
        $analysisContent = document.getElementById('analysisContent');
        $analysisResult = document.getElementById('k8sAnalysisResult');
        $loadingIndicator = document.getElementById('k8sAnalysisLoading');
        $errorMessage = document.getElementById('k8sAnalysisError');
        $toggleBtn = document.getElementById('toggleAnalysisBtn');
        
        // Add event listeners
        if ($analyzeBtn) {
            $analyzeBtn.addEventListener('click', analyzeK8sCluster);
        }
    }
    
    // Analyze K8s Cluster
    function analyzeK8sCluster(e) {
        if (e) e.preventDefault();
        
        // Ensure the analysis content is expanded when starting analysis
        if (!$analysisContent.classList.contains('show')) {
            bootstrap.Collapse.getOrCreateInstance($analysisContent).show();
            
            // Update toggle button appearance
            const toggleIcon = $toggleBtn.querySelector('i');
            const toggleText = $toggleBtn.querySelector('span');
            toggleIcon.classList.replace('fa-angle-down', 'fa-angle-up');
            toggleText.textContent = '收起內容';
            $toggleBtn.setAttribute('aria-expanded', 'true');
        }
        
        // Show loading indicator and hide previous results/errors
        showLoading(true);
        $analysisResult.innerHTML = '';
        $errorMessage.textContent = '';
        $errorMessage.classList.add('d-none');
        
        // Make AJAX request to server
        fetch('/Home/AnalyzeK8s', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                "message": "What is the current status of our Kubernetes cluster over the last 30 minutes? Are there any alerts, critical errors, or significant resource utilization issues?"
            })
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading indicator
            showLoading(false);
            
            if (data.success && data.report) {
                // Display the report using enhanced markdown renderer
                displayReport(data.report);
            } else {
                // Show error message
                $errorMessage.textContent = data.error || '無法取得 Kubernetes 叢集分析';
                $errorMessage.classList.remove('d-none');
            }
        })
        .catch(error => {
            showLoading(false);
            $errorMessage.textContent = `請求錯誤: ${error.message}`;
            $errorMessage.classList.remove('d-none');
            console.error('K8s analysis request failed:', error);
        });
    }
    
    // Display the analysis report
    function displayReport(markdownText) {
        // Add a markdown-content class if it doesn't exist
        if (!$analysisResult.classList.contains('markdown-content')) {
            $analysisResult.classList.add('markdown-content');
        }
        
        // Use our enhanced markdown renderer if available
        if (typeof markdownRenderer !== 'undefined') {
            markdownRenderer.render(markdownText, $analysisResult);
        } else if (typeof marked !== 'undefined') {
            // Fallback to direct use of marked.js
            $analysisResult.innerHTML = marked.parse(markdownText);
            
            // Add styling classes to tables
            const tables = $analysisResult.querySelectorAll('table');
            tables.forEach(table => {
                table.classList.add('table', 'table-bordered', 'table-hover');
            });
        } else {
            // Ultimate fallback if neither is available
            $analysisResult.innerHTML = markdownText.replace(/\n/g, '<br>');
            console.warn('No markdown parser is available');
        }
        
        // Show the result section
        $analysisResult.classList.remove('d-none');
    }
    
    // Toggle loading indicator
    function showLoading(isLoading) {
        if (isLoading) {
            $loadingIndicator.classList.remove('d-none');
            $analyzeBtn.disabled = true;
        } else {
            $loadingIndicator.classList.add('d-none');
            $analyzeBtn.disabled = false;
        }
    }
    
    // Public API
    return {
        init: init,
        analyze: analyzeK8sCluster
    };
})();

// Initialize when the document is ready
document.addEventListener('DOMContentLoaded', k8sAnalyzer.init);