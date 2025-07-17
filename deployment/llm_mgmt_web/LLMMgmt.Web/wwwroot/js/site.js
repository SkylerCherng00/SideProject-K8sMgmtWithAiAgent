/* JavaScript functions for side navigation */
/* Important: This script must be executed after the DOM is fully loaded */
document.addEventListener('DOMContentLoaded', function () {
    // Open navigation: set sidebar width to 250px, push main content to the right
    window.openNav = function() {
        document.getElementById("side-nav").style.width = "250px";
        document.getElementById("main-content").style.marginLeft = "250px";
    };

    // Close navigation: set sidebar width to 0, reset main content position
    window.closeNav = function() {
        document.getElementById("side-nav").style.width = "0";
        document.getElementById("main-content").style.marginLeft = "0";
    };

    // Adjust main content margin when window is resized
    window.addEventListener('resize', function() {
        const sidebar = document.getElementById("side-nav");
        const mainContent = document.getElementById("main-content");
        if (sidebar && mainContent) {
            if (sidebar.style.width === "250px") {
                mainContent.style.marginLeft = "250px";
            } else {
                mainContent.style.marginLeft = "0";
            }
        }
    });
});

// Enhanced Chat functionality with robust button locking
document.addEventListener('DOMContentLoaded', function () {
    console.log('Chat script loaded');
    
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const chatMessages = document.getElementById('chat-messages');
    
    console.log('Chat elements found:', {
        chatForm: !!chatForm,
        userInput: !!userInput,
        sendBtn: !!sendBtn,
        chatMessages: !!chatMessages
    });
    
    // Check if we're on the chat page
    if (!chatForm || !userInput || !sendBtn || !chatMessages) {
        console.log('Chat elements not found on this page');
        return;
    }
    
    const btnText = sendBtn.querySelector('.btn-text');
    const spinner = sendBtn.querySelector('.spinner-border');
    let isProcessing = false;
    let processTimeout = null;

    // Auto-scroll to bottom of chat
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Add message to chat UI
    function addMessageToUI(sender, content, isMarkdown = false) {
        console.log('Adding message to UI:', { sender, content, isMarkdown });
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-msg-${sender.toLowerCase()} align-self-${sender === 'User' ? 'end' : 'start'} mb-2`;

        const contentDiv = document.createElement('div');
        contentDiv.className = `${sender === 'User' ? 'bg-primary text-white' : 'bg-light'} p-2 rounded`;

        const label = document.createElement('strong');
        label.textContent = sender === 'User' ? '您：' : '智能助手：';
        contentDiv.appendChild(label);

        if (isMarkdown && sender === 'Bot') {
            const markdownDiv = document.createElement('div');
            markdownDiv.className = 'markdown-content';
            markdownDiv.textContent = content;
            contentDiv.appendChild(markdownDiv);
            
            // Use our enhanced markdown renderer if available
            if (typeof markdownRenderer !== 'undefined') {
                markdownRenderer.render(content, markdownDiv);
            }
        } else {
            const textSpan = document.createElement('span');
            textSpan.textContent = ` ${content}`;
            contentDiv.appendChild(textSpan);
        }

        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }

    // Enhanced button locking with comprehensive state management
    function setButtonLocked(locked, reason = '') {
        isProcessing = locked;
        
        console.log(`Button ${locked ? 'locked' : 'unlocked'}${reason ? ' - ' + reason : ''}`);
        
        if (locked) {
            // Lock everything
            sendBtn.disabled = true;
            sendBtn.classList.add('disabled');
            sendBtn.setAttribute('aria-busy', 'true');
            userInput.disabled = true;
            userInput.classList.add('disabled');
            
            // Show loading state
            btnText.textContent = '發送中...';
            spinner.classList.remove('d-none');
            
            // Safety timeout (30 seconds)
            processTimeout = setTimeout(() => {
                console.warn('Processing timeout reached, force unlocking button');
                setButtonLocked(false, 'timeout');
            }, 30000);
            
        } else {
            // Unlock everything
            sendBtn.disabled = false;
            sendBtn.classList.remove('disabled');
            sendBtn.setAttribute('aria-busy', 'false');
            userInput.disabled = false;
            userInput.classList.remove('disabled');
            
            // Reset button state
            btnText.textContent = '送出';
            spinner.classList.add('d-none');
            
            // Clear timeout
            if (processTimeout) {
                clearTimeout(processTimeout);
                processTimeout = null;
            }
            
            // Focus back to input
            setTimeout(() => {
                userInput.focus();
            }, 100);
            
            // Update button state based on input content
            setTimeout(() => {
                if (!isProcessing) {
                    const hasText = userInput.value.trim().length > 0;
                    sendBtn.disabled = !hasText;
                }
            }, 200);
        }
    }

    // Clear input function - centralized input clearing
    function clearInput() {
        if (userInput) {
            userInput.value = '';
            console.log('Input cleared');
        }
    }

    // Enhanced send message function with robust button locking
    window.sendMessage = async function() {
        if (isProcessing) {
            console.log('Already processing, ignoring request');
            return;
        }

        const message = userInput.value.trim();
        console.log('Sending message:', message);
        
        if (!message) {
            console.log('Empty message, not sending');
            return;
        }

        // Clear input immediately and lock button
        clearInput();
        setButtonLocked(true, 'sending message');

        // Add user message immediately to UI
        addMessageToUI('User', message);

        try {
            const response = await fetch('/Home/SendMessage', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Response received:', data);

            if (data.success) {
                // Add bot response with markdown rendering
                addMessageToUI('Bot', data.response, true);
            } else {
                addMessageToUI('Bot', `錯誤：${data.error}`, false);
            }
        } catch (error) {
            console.error('Error sending message:', error);
            addMessageToUI('Bot', `網路錯誤：${error.message}`, false);
        } finally {
            // Always unlock the button
            setButtonLocked(false, 'request completed');
        }
    };

    // Form submit handler with button locking protection
    chatForm.addEventListener('submit', function (e) {
        console.log('Form submitted');
        e.preventDefault();
        
        if (isProcessing) {
            console.log('Button is locked, ignoring form submit');
            return;
        }
        
        // Check if enhanced function exists from view
        if (window.sendMessageWithText) {
            const message = userInput.value.trim();
            if (message) {
                clearInput();
                window.sendMessageWithText(message);
            }
        } else {
            // Fall back to standard sendMessage
            window.sendMessage();
        }
    });

    // Enter key handler with button locking protection
    userInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            console.log('Enter key pressed');
            e.preventDefault();
            
            if (isProcessing) {
                console.log('Button is locked, ignoring Enter key');
                return;
            }
            
            // Use enhanced function if available
            if (window.sendMessageWithText) {
                const message = this.value.trim();
                if (message) {
                    clearInput();
                    window.sendMessageWithText(message);
                }
            } else {
                window.sendMessage();
            }
        }
    });

    // Input event handler for real-time button state
    userInput.addEventListener('input', function() {
        if (!isProcessing) {
            const hasText = this.value.trim().length > 0;
            sendBtn.disabled = !hasText;
        }
    });

    // Prevent multiple clicks on submit button
    sendBtn.addEventListener('click', function(e) {
        if (isProcessing) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Button click ignored - currently processing');
            return false;
        }
    });

    // Focus on input when page loads
    userInput.focus();

    // Initial scroll to bottom
    scrollToBottom();
    
    // Set initial button state
    sendBtn.disabled = userInput.value.trim().length === 0;
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
        if (processTimeout) {
            clearTimeout(processTimeout);
        }
    });
    
    console.log('Chat script initialization complete');
});