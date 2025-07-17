/**
 * Enhanced Markdown Renderer
 * Uses marked.js and highlight.js to provide better markdown rendering with syntax highlighting
 */
const markdownRenderer = (function() {
    'use strict';
    
    // Initialize the renderer
    function init() {
        if (typeof marked === 'undefined') {
            console.error('marked.js is not loaded. Please include it before using markdown-renderer.js');
            return;
        }
        
        // Configure marked with highlight.js if available
        if (typeof hljs !== 'undefined') {
            marked.setOptions({
                highlight: function(code, lang) {
                    if (lang && hljs.getLanguage(lang)) {
                        try {
                            return hljs.highlight(code, { language: lang }).value;
                        } catch (e) {
                            console.error('Error highlighting code:', e);
                        }
                    }
                    return hljs.highlightAuto(code).value;
                },
                breaks: true,
                gfm: true,
                headerIds: true,
                mangle: false
            });
        } else {
            // Basic marked configuration without syntax highlighting
            marked.setOptions({
                breaks: true,
                gfm: true
            });
        }
        
        // Process any existing markdown content on the page
        renderExistingContent();
    }
    
    // Render markdown content in a specific element
    function render(markdownText, targetElement) {
        if (!markdownText || !targetElement) {
            return false;
        }
        
        try {
            // Render markdown
            const renderedHtml = marked.parse(markdownText);
            
            // Set content
            targetElement.innerHTML = renderedHtml;
            
            // Apply styling to tables, if any
            applyTableStyles(targetElement);
            
            return true;
        } catch (error) {
            console.error('Error rendering markdown:', error);
            targetElement.textContent = markdownText; // Fallback to plain text
            return false;
        }
    }
    
    // Process all existing markdown-content elements
    function renderExistingContent() {
        const markdownElements = document.querySelectorAll('.markdown-content');
        
        markdownElements.forEach(element => {
            // Get text content and render if not already processed
            if (!element.dataset.rendered) {
                const content = element.textContent || element.innerText;
                if (content && content.trim().length > 0) {
                    render(content, element);
                    element.dataset.rendered = 'true';
                }
            }
        });
    }
    
    // Add Bootstrap styling to tables
    function applyTableStyles(container) {
        const tables = container.querySelectorAll('table');
        tables.forEach(table => {
            table.classList.add('table', 'table-bordered', 'table-hover', 'table-sm');
            
            // Add responsive wrapper if not already present
            if (!table.parentElement.classList.contains('table-responsive')) {
                const wrapper = document.createElement('div');
                wrapper.className = 'table-responsive';
                table.parentNode.insertBefore(wrapper, table);
                wrapper.appendChild(table);
            }
        });
        
        // Style code blocks
        const codeBlocks = container.querySelectorAll('pre code');
        codeBlocks.forEach(block => {
            if (!block.parentElement.classList.contains('code-block-wrapper')) {
                block.parentElement.classList.add('rounded', 'code-block');
            }
        });
    }
    
    // Public API
    return {
        init: init,
        render: render,
        refreshContent: renderExistingContent
    };
})();

// Initialize when the document is ready
document.addEventListener('DOMContentLoaded', markdownRenderer.init);