        let statusInterval = null;
        
        async function processFiles() {
            const btn = document.getElementById('process-btn');
            const loading = document.getElementById('loading');
            const message = document.getElementById('message');
            const fileInfo = document.getElementById('file-info');
            const results = document.getElementById('results');
            const progressSection = document.getElementById('progress-section');
            
            btn.disabled = true;
            loading.style.display = 'block';
            progressSection.style.display = 'block';
            message.className = 'message';
            fileInfo.style.display = 'none';
            message.style.display = 'none';
            
            try {
                const response = await fetch('/api/process', {
                    method: 'POST'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    message.className = 'message info';
                    message.textContent = `Processing started! Processing ${data.total_files} files in background.`;
                    message.style.display = 'block';
                    
                    // Start polling for status
                    startStatusPolling();
                } else {
                    loading.style.display = 'none';
                    progressSection.style.display = 'none';
                    btn.disabled = false;
                    message.className = 'message error';
                    message.textContent = data.message || 'Error starting processing';
                    message.style.display = 'block';
                }
            } catch (error) {
                loading.style.display = 'none';
                progressSection.style.display = 'none';
                btn.disabled = false;
                message.className = 'message error';
                message.textContent = 'Error: ' + error.message;
                message.style.display = 'block';
            }
        }
        
        function startStatusPolling() {
            if (statusInterval) {
                clearInterval(statusInterval);
            }
            
            statusInterval = setInterval(async () => {
                try {
                    const response = await fetch('/api/process-status');
                    const status = await response.json();
                    
                    updateProgress(status);
                    
                    if (!status.is_processing) {
                        // Processing completed
                        clearInterval(statusInterval);
                        statusInterval = null;
                        
                        const btn = document.getElementById('process-btn');
                        const loading = document.getElementById('loading');
                        const message = document.getElementById('message');
                        
                        loading.style.display = 'none';
                        btn.disabled = false;
                        
                        message.className = 'message success';
                        message.textContent = `Processing completed! Processed ${status.processed_count} credentials.`;
                        message.style.display = 'block';
                        
                        // Show errors if any
                        if (status.errors && status.errors.length > 0) {
                            const fileInfo = document.getElementById('file-info');
                            const results = document.getElementById('results');
                            fileInfo.style.display = 'block';
                            results.innerHTML = `
                                <p><strong>Errors encountered:</strong></p>
                                <ul style="margin-top: 10px; padding-left: 20px; max-height: 200px; overflow-y: auto;">
                                    ${status.errors.slice(0, 20).map(err => `<li style="margin: 5px 0;">${err}</li>`).join('')}
                                    ${status.errors.length > 20 ? `<li>... and ${status.errors.length - 20} more errors</li>` : ''}
                                </ul>
                            `;
                        }
                        
                        // Update stats
                        updateStats();
                    }
                } catch (error) {
                    console.error('Error fetching status:', error);
                }
            }, 1000); // Poll every second
        }
        
        function updateProgress(status) {
            const progressBar = document.getElementById('progress-bar');
            const progressText = document.getElementById('progress-text');
            const currentFile = document.getElementById('current-file');
            const processedCount = document.getElementById('processed-count');
            const timeInfo = document.getElementById('time-info');
            
            if (status.total > 0) {
                const percentage = (status.progress / status.total) * 100;
                progressBar.style.width = percentage + '%';
                progressText.textContent = Math.round(percentage) + '%';
            }
            
            currentFile.textContent = status.current_file || 'Processing...';
            processedCount.textContent = `${status.processed_count.toLocaleString()} credentials processed`;
            
            if (status.elapsed_seconds !== undefined) {
                const elapsed = formatTime(status.elapsed_seconds);
                const remaining = status.estimated_remaining_seconds !== undefined 
                    ? formatTime(status.estimated_remaining_seconds) 
                    : '--';
                timeInfo.textContent = `Elapsed: ${elapsed} | Estimated remaining: ${remaining}`;
            }
        }
        
        function formatTime(seconds) {
            if (seconds < 60) {
                return seconds + 's';
            } else if (seconds < 3600) {
                const mins = Math.floor(seconds / 60);
                const secs = seconds % 60;
                return `${mins}m ${secs}s`;
            } else {
                const hours = Math.floor(seconds / 3600);
                const mins = Math.floor((seconds % 3600) / 60);
                return `${hours}h ${mins}m`;
            }
        }
        
        async function updateStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.getElementById('total-domains').textContent = data.total_domains;
                document.getElementById('online-domains').textContent = data.online_domains;
                document.getElementById('offline-domains').textContent = data.offline_domains;
                document.getElementById('total-credentials').textContent = data.total_credentials;
                document.getElementById('accessed-credentials').textContent = data.accessed_credentials;
            } catch (error) {
                console.error('Error updating stats:', error);
            }
        }
        
        // Update stats periodically
        setInterval(updateStats, 30000); // Every 30 seconds
        
        async function checkAll() {
            const btn = document.getElementById('check-all-btn');
            const message = document.getElementById('check-all-message');
            
            btn.disabled = true;
            message.className = 'message';
            message.style.display = 'none';
            
            try {
                const response = await fetch('/api/check-all', {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    message.className = 'message success';
                    message.textContent = `Successfully checked all items! Updated ${result.domains_updated} domains and ${result.credentials_updated} credentials.`;
                    message.style.display = 'block';
                    
                    // Update stats after a short delay
                    setTimeout(updateStats, 1000);
                } else {
                    message.className = 'message error';
                    message.textContent = 'Error checking all items';
                    message.style.display = 'block';
                }
            } catch (error) {
                message.className = 'message error';
                message.textContent = 'Error: ' + error.message;
                message.style.display = 'block';
            } finally {
                btn.disabled = false;
            }
        }


        // Export functionality
let exportExtensions = new Set(['.in', '.gov.in', '.gov', '.com', '.org', '.edu']);
let statusExtensions = new Set(['.in', '.gov.in', '.gov', '.com', '.org', '.edu']);
let isStatusProcessing = false;
let statusProcessingInterval = null;

// Initialize extension tags
document.addEventListener('DOMContentLoaded', function() {
    updateExportExtensionTags();
    updateStatusExtensionTags();
});

function updateExportExtensionTags() {
    const container = document.getElementById('export-domain-extensions');
    container.innerHTML = '';
    
    exportExtensions.forEach(ext => {
        const tag = document.createElement('span');
        tag.className = 'extension-tag active';
        tag.textContent = ext;
        tag.dataset.extension = ext;
        tag.onclick = function() {
            exportExtensions.delete(ext);
            updateExportExtensionTags();
            updateActiveFilters('export');
        };
        container.appendChild(tag);
    });
}

function updateStatusExtensionTags() {
    const container = document.getElementById('status-domain-extensions');
    container.innerHTML = '';
    
    statusExtensions.forEach(ext => {
        const tag = document.createElement('span');
        tag.className = 'extension-tag active';
        tag.textContent = ext;
        tag.dataset.extension = ext;
        tag.onclick = function() {
            statusExtensions.delete(ext);
            updateStatusExtensionTags();
            updateActiveFilters('status');
        };
        container.appendChild(tag);
    });
}

function addExportExtension() {
    const input = document.getElementById('export-custom-extension');
    const ext = input.value.trim();
    
    if (ext && !exportExtensions.has(ext)) {
        if (!ext.startsWith('.')) {
            exportExtensions.add('.' + ext);
        } else {
            exportExtensions.add(ext);
        }
        updateExportExtensionTags();
        updateActiveFilters('export');
    }
    
    input.value = '';
}

function addStatusExtension() {
    const input = document.getElementById('status-custom-extension');
    const ext = input.value.trim();
    
    if (ext && !statusExtensions.has(ext)) {
        if (!ext.startsWith('.')) {
            statusExtensions.add('.' + ext);
        } else {
            statusExtensions.add(ext);
        }
        updateStatusExtensionTags();
        updateActiveFilters('status');
    }
    
    input.value = '';
}

function updateActiveFilters(type) {
    let container, extensions, checkedFilter, accessedFilter, workingFilter, adminFilter, domainContains;
    
    if (type === 'export') {
        container = document.getElementById('export-active-filters');
        extensions = exportExtensions;
        checkedFilter = document.getElementById('export-checked-filter').value;
        accessedFilter = document.getElementById('export-accessed-filter').value;
        workingFilter = document.getElementById('export-working-filter').value;
        adminFilter = document.getElementById('export-admin-filter').value;
        domainContains = document.getElementById('export-domain-contains').value;
    } else {
        container = document.getElementById('status-active-filters');
        extensions = statusExtensions;
        checkedFilter = document.getElementById('status-checked-filter').value;
        accessedFilter = document.getElementById('status-accessed-filter').value;
        workingFilter = document.getElementById('status-working-filter').value;
        domainContains = document.getElementById('status-domain-contains').value;
    }
    
    container.innerHTML = '';
    
    // Add filter badges
    if (checkedFilter !== 'not_checked') {
        addFilterBadge(container, `Checked: ${checkedFilter}`, type);
    }
    
    if (accessedFilter !== 'all') {
        addFilterBadge(container, `Accessed: ${accessedFilter}`, type);
    }
    
    if (workingFilter !== 'all') {
        addFilterBadge(container, `Working: ${workingFilter}`, type);
    }
    
    if (type === 'export' && adminFilter !== 'all') {
        addFilterBadge(container, `Admin: ${adminFilter}`, type);
    }
    
    if (extensions.size > 0) {
        const extensionsText = Array.from(extensions).join(', ');
        addFilterBadge(container, `Extensions: ${extensionsText}`, type);
    }
    
    if (domainContains) {
        addFilterBadge(container, `Contains: ${domainContains}`, type);
    }
    
    if (container.children.length === 0) {
        container.innerHTML = '<span style="color: #9ca3af;">No filters applied</span>';
    }
}

function addFilterBadge(container, text, type) {
    const badge = document.createElement('div');
    badge.className = 'filter-badge';
    badge.innerHTML = `
        ${text}
        <span class="remove-filter" onclick="removeFilter(this, '${type}')">×</span>
    `;
    container.appendChild(badge);
}

function removeFilter(element, type) {
    const badge = element.parentElement;
    const text = badge.textContent.replace('×', '').trim();
    
    if (text.startsWith('Checked:')) {
        if (type === 'export') {
            document.getElementById('export-checked-filter').value = 'not_checked';
        } else {
            document.getElementById('status-checked-filter').value = 'not_checked';
        }
    } else if (text.startsWith('Accessed:')) {
        if (type === 'export') {
            document.getElementById('export-accessed-filter').value = 'all';
        } else {
            document.getElementById('status-accessed-filter').value = 'all';
        }
    } else if (text.startsWith('Working:')) {
        if (type === 'export') {
            document.getElementById('export-working-filter').value = 'all';
        } else {
            document.getElementById('status-working-filter').value = 'all';
        }
    } else if (text.startsWith('Admin:')) {
        document.getElementById('export-admin-filter').value = 'all';
    } else if (text.startsWith('Extensions:')) {
        const extensionsText = text.replace('Extensions: ', '');
        const extensionsList = extensionsText.split(', ');
        
        if (type === 'export') {
            extensionsList.forEach(ext => exportExtensions.delete(ext));
            updateExportExtensionTags();
        } else {
            extensionsList.forEach(ext => statusExtensions.delete(ext));
            updateStatusExtensionTags();
        }
    } else if (text.startsWith('Contains:')) {
        if (type === 'export') {
            document.getElementById('export-domain-contains').value = '';
        } else {
            document.getElementById('status-domain-contains').value = '';
        }
    }
    
    updateActiveFilters(type);
}

function clearExportFilters() {
    exportExtensions.clear();
    updateExportExtensionTags();
    
    document.getElementById('export-checked-filter').value = 'not_checked';
    document.getElementById('export-accessed-filter').value = 'all';
    document.getElementById('export-working-filter').value = 'all';
    document.getElementById('export-admin-filter').value = 'all';
    document.getElementById('export-domain-contains').value = '';
    document.getElementById('export-format').value = 'excel';
    
    updateActiveFilters('export');
}

function clearStatusFilters() {
    statusExtensions.clear();
    updateStatusExtensionTags();
    
    document.getElementById('status-checked-filter').value = 'not_checked';
    document.getElementById('status-accessed-filter').value = 'all';
    document.getElementById('status-working-filter').value = 'all';
    document.getElementById('status-domain-contains').value = '';
    document.getElementById('status-batch-size').value = '25';
    
    updateActiveFilters('status');
}

async function exportCredentials() {
    // Update active filters display
    updateActiveFilters('export');
    
    const filters = {
        checked_filter: document.getElementById('export-checked-filter').value,
        accessed_filter: document.getElementById('export-accessed-filter').value,
        working_filter: document.getElementById('export-working-filter').value,
        admin_filter: document.getElementById('export-admin-filter').value,
        domain_extensions: Array.from(exportExtensions),
        domain_contains: document.getElementById('export-domain-contains').value,
        format: document.getElementById('export-format').value
    };
    
    try {
        const response = await fetch('/api/export-credentials-filtered', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(filters)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Export failed');
        }
        
        // Create download link
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        a.href = url;
        
        const format = filters.format;
        const ext = format === 'excel' ? 'xlsx' : format;
        a.download = `credentials_export_${timestamp}.${ext}`;
        
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showMessage('Export completed successfully!', 'success');
        
    } catch (error) {
        showMessage('Error during export: ' + error.message, 'error');
    }
}

async function processWorkingStatus() {
    if (isStatusProcessing) {
        alert('Status processing is already in progress');
        return;
    }
    
    // Update active filters display
    updateActiveFilters('status');
    
    const filters = {
        checked_filter: document.getElementById('status-checked-filter').value,
        accessed_filter: document.getElementById('status-accessed-filter').value,
        working_filter: document.getElementById('status-working-filter').value,
        domain_extensions: Array.from(statusExtensions),
        domain_contains: document.getElementById('status-domain-contains').value,
        batch_size: parseInt(document.getElementById('status-batch-size').value)
    };
    
    try {
        const response = await fetch('/api/process-working-status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(filters)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start processing');
        }
        
        const result = await response.json();
        
        // Show processing section
        document.getElementById('status-processing-section').style.display = 'block';
        isStatusProcessing = true;
        
        // Start polling for status
        startStatusPolling(result.task_id);
        
        showMessage('Working status processing started!', 'success');
        
    } catch (error) {
        showMessage('Error starting processing: ' + error.message, 'error');
    }
}

function startStatusPolling(taskId) {
    let elapsed = 0;
    
    // Update elapsed time every second
    const timeInterval = setInterval(() => {
        elapsed++;
        const timeInfo = document.getElementById('status-time-info');
        const currentText = timeInfo.textContent;
        const newText = currentText.replace(/Elapsed: \d+s/, `Elapsed: ${elapsed}s`);
        timeInfo.textContent = newText;
    }, 1000);
    
    // Poll for status updates
    statusProcessingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/process-working-status/${taskId}`);
            const result = await response.json();
            
            if (result.status === 'completed' || result.status === 'failed') {
                // Processing finished
                clearInterval(statusProcessingInterval);
                clearInterval(timeInterval);
                isStatusProcessing = false;
                
                // Update UI with final results
                updateStatusUI(result);
                
                if (result.status === 'completed') {
                    showMessage(`Processing completed! Updated ${result.online_count} domains to online and ${result.offline_count} to offline.`, 'success');
                } else {
                    showMessage('Processing failed: ' + result.error, 'error');
                }
                
                // Hide processing section after 5 seconds
                setTimeout(() => {
                    document.getElementById('status-processing-section').style.display = 'none';
                }, 5000);
                
            } else if (result.status === 'processing') {
                // Update progress
                updateStatusUI(result);
            }
        } catch (error) {
            console.error('Error polling status:', error);
        }
    }, 2000);
}

function updateStatusUI(result) {
    const progressBar = document.getElementById('status-progress-bar');
    const progressText = document.getElementById('status-progress-text');
    const currentInfo = document.getElementById('status-current-info');
    const processedCount = document.getElementById('status-processed-count');
    const timeInfo = document.getElementById('status-time-info');
    
    if (result.total) {
        const percentage = Math.round((result.processed / result.total) * 100);
        progressBar.style.width = percentage + '%';
        progressText.textContent = percentage + '%';
        processedCount.textContent = `${result.processed}/${result.total} domains`;
    }
    
    if (result.current_domain) {
        currentInfo.textContent = `Checking: ${result.current_domain}`;
    }
    
    if (result.online_count !== undefined && result.offline_count !== undefined) {
        timeInfo.innerHTML = `Elapsed: ${result.elapsed_seconds || 0}s | Online: ${result.online_count} | Offline: ${result.offline_count} | Failed: ${result.failed_count || 0}`;
    }
}

function stopStatusProcessing() {
    if (statusProcessingInterval) {
        clearInterval(statusProcessingInterval);
    }
    
    isStatusProcessing = false;
    document.getElementById('status-processing-section').style.display = 'none';
    
    // Call API to stop processing if needed
    fetch('/api/process-working-status/stop', { method: 'POST' })
        .catch(console.error);
    
    showMessage('Status processing stopped', 'info');
}

function showMessage(message, type) {
    const messageDiv = document.getElementById('message');
    messageDiv.textContent = message;
    messageDiv.style.display = 'block';
    messageDiv.style.background = type === 'error' ? '#fee2e2' : 
                                  type === 'success' ? '#d1fae5' : 
                                  type === 'info' ? '#dbeafe' : '#f3f4f6';
    messageDiv.style.color = type === 'error' ? '#dc2626' : 
                             type === 'success' ? '#059669' : 
                             type === 'info' ? '#2563eb' : '#374151';
    
    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 5000);
}

// Existing functions from your code
async function processFiles() {
    const processBtn = document.getElementById('process-btn');
    const loadingDiv = document.getElementById('loading');
    const progressSection = document.getElementById('progress-section');
    const messageDiv = document.getElementById('message');
    const fileInfo = document.getElementById('file-info');
    
    processBtn.disabled = true;
    loadingDiv.style.display = 'block';
    progressSection.style.display = 'none';
    messageDiv.style.display = 'none';
    fileInfo.style.display = 'none';
    
    try {
        const response = await fetch('/api/process', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            messageDiv.textContent = 'Processing started! Check progress below.';
            messageDiv.style.display = 'block';
            messageDiv.style.background = '#d1fae5';
            messageDiv.style.color = '#059669';
            
            // Start polling for progress
            pollProcessingProgress();
            
            progressSection.style.display = 'block';
        } else {
            messageDiv.textContent = result.message;
            messageDiv.style.display = 'block';
            messageDiv.style.background = '#fee2e2';
            messageDiv.style.color = '#dc2626';
        }
    } catch (error) {
        messageDiv.textContent = 'Error starting processing: ' + error.message;
        messageDiv.style.display = 'block';
        messageDiv.style.background = '#fee2e2';
        messageDiv.style.color = '#dc2626';
    } finally {
        processBtn.disabled = false;
        loadingDiv.style.display = 'none';
    }
}

async function pollProcessingProgress() {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const currentFile = document.getElementById('current-file');
    const processedCount = document.getElementById('processed-count');
    const timeInfo = document.getElementById('time-info');
    const fileInfo = document.getElementById('file-info');
    const resultsDiv = document.getElementById('results');
    
    const interval = setInterval(async () => {
        try {
            const response = await fetch('/api/process-status');
            const status = await response.json();
            
            if (status.total > 0) {
                const percentage = Math.round((status.progress / status.total) * 100);
                progressBar.style.width = percentage + '%';
                progressText.textContent = percentage + '%';
            }
            
            currentFile.textContent = status.current_file || 'Processing...';
            processedCount.textContent = status.processed_count + ' credentials processed';
            
            if (status.elapsed_seconds) {
                timeInfo.textContent = `Elapsed: ${status.elapsed_seconds}s`;
                if (status.estimated_remaining_seconds) {
                    timeInfo.textContent += ` | Estimated remaining: ${status.estimated_remaining_seconds}s`;
                }
            }
            
            // Show errors if any
            if (status.errors && status.errors.length > 0) {
                resultsDiv.innerHTML = status.errors.map(error => 
                    `<div style="color: #dc2626; margin: 5px 0;">${error}</div>`
                ).join('');
                fileInfo.style.display = 'block';
            }
            
            // If processing is complete
            if (!status.is_processing) {
                clearInterval(interval);
                progressText.textContent = '100%';
                progressBar.style.width = '100%';
                
                if (status.errors.length === 0) {
                    resultsDiv.innerHTML = '<div style="color: #059669;">Processing completed successfully!</div>';
                }
                fileInfo.style.display = 'block';
            }
        } catch (error) {
            console.error('Error polling progress:', error);
        }
    }, 1000);
}

async function checkAll() {
    const checkAllBtn = document.getElementById('check-all-btn');
    const checkAllMessage = document.getElementById('check-all-message');
    
    checkAllBtn.disabled = true;
    checkAllMessage.style.display = 'block';
    checkAllMessage.textContent = 'Checking all domains and credentials...';
    checkAllMessage.style.background = '#dbeafe';
    checkAllMessage.style.color = '#2563eb';
    
    try {
        const response = await fetch('/api/check-all', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            checkAllMessage.textContent = `Successfully checked ${result.domains_updated} domains and ${result.credentials_updated} credentials!`;
            checkAllMessage.style.background = '#d1fae5';
            checkAllMessage.style.color = '#059669';
        } else {
            checkAllMessage.textContent = 'Error checking all: ' + result.message;
            checkAllMessage.style.background = '#fee2e2';
            checkAllMessage.style.color = '#dc2626';
        }
    } catch (error) {
        checkAllMessage.textContent = 'Error: ' + error.message;
        checkAllMessage.style.background = '#fee2e2';
        checkAllMessage.style.color = '#dc2626';
    } finally {
        setTimeout(() => {
            checkAllMessage.style.display = 'none';
            checkAllBtn.disabled = false;
        }, 5000);
    }
}