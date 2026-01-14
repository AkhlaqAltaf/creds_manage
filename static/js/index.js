        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(() => {
                checkDomainStatuses();
            }, 500);
        });
        





        // Selection management
let selectedItems = {
    domains: new Set(),
    credentials: new Set()
};

// Update selection display
function updateSelection() {
    // Count selected items
    const selectedDomains = document.querySelectorAll('.domain-select-checkbox:checked').length;
    const selectedCredentials = document.querySelectorAll('.credential-select-checkbox:checked').length;
    const totalSelected = selectedDomains + selectedCredentials;
    
    // Update counter
    document.getElementById('selectedCount').textContent = totalSelected;
    
    // Show/hide selection header
    const selectionHeader = document.getElementById('selectionHeader');
    selectionHeader.style.display = totalSelected > 0 ? 'block' : 'none';
    
    // Update domain checkboxes based on credential selection
    updateDomainSelectionStates();
}

// Toggle domain selection
function toggleDomainSelection(domainId, isSelected) {
    if (isSelected) {
        selectedItems.domains.add(domainId);
        // Select all credentials in this domain
        selectAllCredentialsInDomain(domainId, true);
    } else {
        selectedItems.domains.delete(domainId);
        // Deselect all credentials in this domain
        selectAllCredentialsInDomain(domainId, false);
    }
    updateSelection();
}

// Select all credentials in a domain
function selectAllCredentialsInDomain(domainId, select) {
    const checkboxes = document.querySelectorAll(`.credential-select-checkbox[data-domain-id="${domainId}"]`);
    const selectAllCheckbox = document.querySelector(`.select-all-credential[data-domain-id="${domainId}"]`);
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = select;
        if (select) {
            selectedItems.credentials.add(parseInt(checkbox.dataset.credentialId));
        } else {
            selectedItems.credentials.delete(parseInt(checkbox.dataset.credentialId));
        }
    });
    
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = select;
    }
}

// Update domain checkbox states based on credential selection
function updateDomainSelectionStates() {
    document.querySelectorAll('.domain-card').forEach(card => {
        const domainId = card.dataset.domainId;
        const credentialCheckboxes = document.querySelectorAll(`.credential-select-checkbox[data-domain-id="${domainId}"]`);
        const domainCheckbox = document.querySelector(`.domain-select-checkbox[data-domain-id="${domainId}"]`);
        
        if (credentialCheckboxes.length > 0) {
            const allChecked = Array.from(credentialCheckboxes).every(cb => cb.checked);
            const someChecked = Array.from(credentialCheckboxes).some(cb => cb.checked);
            
            if (allChecked) {
                domainCheckbox.checked = true;
                selectedItems.domains.add(parseInt(domainId));
            } else if (someChecked) {
                domainCheckbox.checked = false;
                selectedItems.domains.delete(parseInt(domainId));
            } else {
                domainCheckbox.checked = false;
                selectedItems.domains.delete(parseInt(domainId));
            }
        }
    });
}

// Select all domains on current page
function selectAllDomains() {
    const domainCheckboxes = document.querySelectorAll('.domain-select-checkbox');
    domainCheckboxes.forEach(checkbox => {
        const domainId = checkbox.dataset.domainId;
        checkbox.checked = true;
        toggleDomainSelection(parseInt(domainId), true);
    });
}

// Deselect all
function deselectAll() {
    selectedItems.domains.clear();
    selectedItems.credentials.clear();
    
    document.querySelectorAll('.domain-select-checkbox').forEach(cb => cb.checked = false);
    document.querySelectorAll('.credential-select-checkbox').forEach(cb => cb.checked = false);
    document.querySelectorAll('.select-all-credential').forEach(cb => cb.checked = false);
    
    updateSelection();
}

// Clear selection
function clearSelection() {
    deselectAll();
}

// Get all selected credential IDs (including those from selected domains)
function getAllSelectedCredentialIds() {
    const allCredentialIds = new Set(selectedItems.credentials);
    
    // Add credentials from selected domains
    selectedItems.domains.forEach(domainId => {
        const credentialCheckboxes = document.querySelectorAll(`.credential-select-checkbox[data-domain-id="${domainId}"]`);
        credentialCheckboxes.forEach(cb => {
            allCredentialIds.add(parseInt(cb.dataset.credentialId));
        });
    });
    
    return Array.from(allCredentialIds);
}




        function refreshDomainStatuses() {
            const domains = document.querySelectorAll('.domain-card');
            domains.forEach(card => {
                const domainId = card.dataset.domainId;
                const statusBadge = document.getElementById('status-' + domainId);
                if (statusBadge) {
                    statusBadge.textContent = 'UNKNOWN';
                    statusBadge.className = 'status-badge status-unknown';
                }
            });
            checkDomainStatuses();
        }
        
        function toggleDomain(domainId) {
            const content = document.getElementById('content-' + domainId);
            const icon = document.getElementById('icon-' + domainId);
            
            if (content.classList.contains('expanded')) {
                content.classList.remove('expanded');
                icon.classList.remove('rotated');
            } else {
                content.classList.add('expanded');
                icon.classList.add('rotated');
            }
        }
        
        async function checkDomainStatuses() {
            const domains = document.querySelectorAll('.domain-card');
            
            // Check domains in parallel with limited concurrency
            const checkPromises = [];
            let activeChecks = 0;
            const maxConcurrent = 5;
            
            for (const domainCard of domains) {
                const domain = domainCard.dataset.domain;
                const domainId = domainCard.dataset.domainId;
                const checkUrlsStr = domainCard.dataset.checkUrls || '';
                const checkUrls = checkUrlsStr ? checkUrlsStr.split(',').filter(url => url.trim()) : [];
                const statusBadge = document.getElementById('status-' + domainId);
                
                // Wait if too many concurrent checks
                while (activeChecks >= maxConcurrent) {
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
                
                activeChecks++;
                const checkPromise = checkSingleDomain(domain, domainId, checkUrls).finally(() => {
                    activeChecks--;
                });
                
                checkPromises.push(checkPromise);
            }
            
            await Promise.allSettled(checkPromises);
        }
        
        async function checkSingleDomain(domain, domainId, checkUrls = []) {
            const statusBadge = document.getElementById('status-' + domainId);
            if (!statusBadge) return;
            
            statusBadge.textContent = 'CHECKING...';
            statusBadge.className = 'status-badge status-unknown';
            
            let isOnline = false;
            
            // Build list of URLs to test (curl-like approach)
            // Priority: actual credential URLs first, then domain root URLs
            const urlsToTry = [];
            
            // Add credential URLs first (these are the actual working URLs)
            if (checkUrls && checkUrls.length > 0) {
                urlsToTry.push(...checkUrls.map(url => url.trim()).filter(url => url));
            }
            
            // Fallback to domain root URLs with different protocols
            urlsToTry.push(`https://${domain}`);
            urlsToTry.push(`http://${domain}`);
            
            // Curl-like checking: try to establish a connection
            // If connection succeeds = online, if it fails = offline
            for (const url of urlsToTry) {
                try {
                    // Try HEAD request first (like curl -I) - fastest, no body transfer
                    const controller = new AbortController();
                    const timeout = setTimeout(() => controller.abort(), 10000); // 10 second timeout
                    
                    try {
                        // Use no-cors to bypass CORS restrictions and just check connectivity
                        // This is like curl - it doesn't care about CORS, just checks if connection works
                        await fetch(url, {
                            method: 'HEAD',
                            mode: 'no-cors', // Like curl - bypasses CORS, just checks connection
                            signal: controller.signal,
                            cache: 'no-store',
                            redirect: 'follow',
                            credentials: 'omit'
                        });
                        
                        clearTimeout(timeout);
                        // If we get here without error, connection was successful (like curl exit code 0)
                        isOnline = true;
                        break;
                    } catch (fetchError) {
                        clearTimeout(timeout);
                        
                        // Check error type
                        if (fetchError.name === 'AbortError') {
                            // Timeout - domain might be slow or unreachable
                            continue; // Try next URL
                        } else if (fetchError.message && (
                            fetchError.message.includes('Failed to fetch') ||
                            fetchError.message.includes('NetworkError') ||
                            fetchError.message.includes('Network request failed')
                        )) {
                            // Network-level failure (DNS error, connection refused, etc.)
                            // This is like curl getting "Could not resolve host" or "Connection refused"
                            continue; // Try next URL
                        } else {
                            // Other error - might still be reachable but had some other issue
                            // Try GET as fallback
                            try {
                                const controller2 = new AbortController();
                                const timeout2 = setTimeout(() => controller2.abort(), 8000);
                                
                                await fetch(url, {
                                    method: 'GET',
                                    mode: 'no-cors',
                                    signal: controller2.signal,
                                    cache: 'no-store',
                                    redirect: 'follow',
                                    credentials: 'omit'
                                });
                                
                                clearTimeout(timeout2);
                                isOnline = true;
                                break;
                            } catch (getError) {
                                clearTimeout(timeout2);
                                continue; // Try next URL
                            }
                        }
                    }
                } catch (outerError) {
                    // Continue to next URL
                    continue;
                }
            }
            
            // Final fallback: try image loading (respects VPN, works even with strict CORS)
            if (!isOnline) {
                try {
                    const imgCheck = await new Promise((resolve, reject) => {
                        const img = new Image();
                        const timeout = setTimeout(() => {
                            img.onload = null;
                            img.onerror = null;
                            reject(new Error('Timeout'));
                        }, 8000);
                        
                        img.onload = () => {
                            clearTimeout(timeout);
                            resolve(true);
                        };
                        
                        img.onerror = () => {
                            clearTimeout(timeout);
                            reject(new Error('Image load failed'));
                        };
                        
                        // Try with the domain
                        img.src = `https://${domain}/favicon.ico?check=${Date.now()}`;
                    });
                    
                    if (imgCheck) {
                        isOnline = true;
                    }
                } catch (imgError) {
                    // All methods failed - domain is offline
                    isOnline = false;
                }
            }
            
            updateStatusBadge(domainId, isOnline);
        }
        
        function updateStatusBadge(domainId, isOnline) {
            const statusBadge = document.getElementById('status-' + domainId);
            statusBadge.className = 'status-badge ' + (isOnline ? 'status-online' : 'status-offline');
            statusBadge.textContent = isOnline ? 'ONLINE' : 'OFFLINE';
        }
        
        async function updateWorkingStatus() {
            const domainCards = document.querySelectorAll('.domain-card');
            const statuses = {};
            
            domainCards.forEach(card => {
                const domainId = card.dataset.domainId;
                const statusBadge = document.getElementById('status-' + domainId);
                if (statusBadge) {
                    const isOnline = statusBadge.classList.contains('status-online');
                    statuses[domainId] = isOnline;
                }
            });
            
            try {
                const response = await fetch('/api/update-working-status', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(statuses)
                });
                
                const result = await response.json();
                if (result.success) {
                    alert(`Updated ${result.updated} domains`);
                }
            } catch (error) {
                alert('Error updating status: ' + error.message);
            }
        }
        
        function copyToClipboard(text, button) {
            navigator.clipboard.writeText(text).then(() => {
                const originalText = button.textContent;
                button.textContent = 'Copied!';
                button.style.background = '#10b981';
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.background = '#667eea';
                }, 2000);
            });
        }
        
        
        async function toggleAccessed(credentialId, isAccessed) {
            const checkbox = event.target;
            try {
                const response = await fetch(`/api/credential/${credentialId}/toggle-accessed`, {
                    method: 'POST'
                });
                const result = await response.json();
                if (!result.success) {
                    // Revert checkbox
                    checkbox.checked = !isAccessed;
                }
            } catch (error) {
                alert('Error updating access status');
                checkbox.checked = !isAccessed;
            }
        }
        
        async function toggleCredentialChecked(credentialId, isChecked) {
            const checkbox = event.target;
            try {
                const response = await fetch(`/api/credential/${credentialId}/toggle-checked`, {
                    method: 'POST'
                });
                const result = await response.json();
                if (!result.success) {
                    checkbox.checked = !isChecked;
                }
            } catch (error) {
                alert('Error updating check status');
                checkbox.checked = !isChecked;
            }
        }
        
        async function toggleDomainChecked(domainId, isChecked) {
            const checkbox = event.target;
            try {
                const response = await fetch(`/api/domain/${domainId}/toggle-checked`, {
                    method: 'POST'
                });
                const result = await response.json();
                if (!result.success) {
                    checkbox.checked = !isChecked;
                }
            } catch (error) {
                alert('Error updating domain check status');
                checkbox.checked = !isChecked;
            }
        }
        
        function filterByStatus(status) {
            const currentUrl = new URL(window.location);
            currentUrl.searchParams.set('status_filter', status);
            currentUrl.searchParams.set('page', '1');
            window.location.href = currentUrl.toString();
        }
        
        function filterByChecked(checkedFilter) {
            const currentUrl = new URL(window.location);
            currentUrl.searchParams.set('checked_filter', checkedFilter);
            currentUrl.searchParams.set('page', '1');
            window.location.href = currentUrl.toString();
        }
        
        function filterByDomain(domainFilter) {
            const currentUrl = new URL(window.location);
            if (domainFilter === 'all') {
                currentUrl.searchParams.delete('domain_filter');
            } else {
                currentUrl.searchParams.set('domain_filter', domainFilter);
            }
            currentUrl.searchParams.set('page', '1');
            window.location.href = currentUrl.toString();
        }
        
        function toggleAccessedFilter() {
            const checked = document.getElementById('accessedOnly').checked;
            const currentUrl = new URL(window.location);
            if (checked) {
                currentUrl.searchParams.set('accessed_only', 'true');
            } else {
                currentUrl.searchParams.delete('accessed_only');
            }
            currentUrl.searchParams.set('page', '1');
            window.location.href = currentUrl.toString();
        }
        
        function changePage(page) {
            const currentUrl = new URL(window.location);
            currentUrl.searchParams.set('page', page);
            window.location.href = currentUrl.toString();
        }
        
        function performSearch() {
            const searchInput = document.getElementById('searchInput');
            const searchTerm = searchInput.value.trim();
            const currentUrl = new URL(window.location);
            
            if (searchTerm) {
                currentUrl.searchParams.set('search', searchTerm);
            } else {
                currentUrl.searchParams.delete('search');
            }
            
            currentUrl.searchParams.set('page', '1'); // Reset to first page
            window.location.href = currentUrl.toString();
        }
        
        function clearSearch() {
            const searchInput = document.getElementById('searchInput');
            searchInput.value = '';
            const currentUrl = new URL(window.location);
            currentUrl.searchParams.delete('search');
            currentUrl.searchParams.set('page', '1');
            window.location.href = currentUrl.toString();
        }
        
        function handleSearchKeypress(event) {
            if (event.key === 'Enter') {
                performSearch();
            }
        }
        


        // Add a global variable to track loaded counts per domain
const loadedCredsCount = {};

async function loadMoreCredentials(domainId, currentCount) {
    const loadMoreBtn = document.getElementById('load-more-' + domainId);
    const loadingMore = document.getElementById('loading-more-' + domainId);
    const tbody = document.getElementById('creds-tbody-' + domainId);
    
    if (!tbody || !loadMoreBtn) return;
    
    // Initialize or get current loaded count for this domain
    if (!loadedCredsCount[domainId]) {
        loadedCredsCount[domainId] = currentCount;
    }
    
    loadMoreBtn.disabled = true;
    loadingMore.style.display = 'block';
    
    try {
        // Get current filter state
        const urlParams = new URLSearchParams(window.location.search);
        const accessedOnly = urlParams.get('accessed_only') === 'true' || document.getElementById('accessedOnly')?.checked;
        const checkedFilter = urlParams.get('checked_filter') || 'all';
        
        // Use the tracked count instead of currentCount
        const offset = loadedCredsCount[domainId];
        
        const response = await fetch(`/api/domain/${domainId}/credentials?offset=${offset}&limit=50&accessed_only=${accessedOnly}&checked_filter=${checkedFilter}`);
        const data = await response.json();
        
        // Add new credentials to table
        data.credentials.forEach(cred => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <input type="checkbox" ${cred.is_checked ? 'checked' : ''} 
                           class="credential-select-checkbox"
                           data-credential-id="${cred.id}"
                           onchange="toggleCredentialChecked(${cred.id}, this.checked)"
                           style="width: 20px; height: 20px; cursor: pointer;">
                </td>
                <td class="url-cell">
                    <a href="${escapeHtml(cred.url)}" target="_blank" class="url-link">${escapeHtml(cred.url)}</a>
                </td>
                <td>
                    ${escapeHtml(cred.user)}
                    <button class="copy-btn" onclick="copyToClipboard(${JSON.stringify(cred.user)}, this)">Copy</button>
                </td>
                <td>
                    <span>${escapeHtml(cred.password)}</span>
                    <button class="copy-btn" onclick="copyToClipboard(${JSON.stringify(cred.password)}, this)">Copy</button>
                </td>
                <td>
                    <input type="checkbox" ${cred.is_accessed ? 'checked' : ''} 
                           onchange="toggleAccessed(${cred.id}, this.checked)"
                           style="width: 20px; height: 20px; cursor: pointer;">
                </td>
            `;
            tbody.appendChild(row);
        });
        
        // Update the loaded count
        loadedCredsCount[domainId] += data.credentials.length;
        
        // Update button or hide if all loaded
        if (loadedCredsCount[domainId] >= data.total) {
            loadMoreBtn.style.display = 'none';
        } else {
            loadMoreBtn.textContent = `Load More (Showing ${loadedCredsCount[domainId]} of ${data.total})`;
            loadMoreBtn.disabled = false;
        }
        
    } catch (error) {
        alert('Error loading more credentials: ' + error.message);
        loadMoreBtn.disabled = false;
    } finally {
        loadingMore.style.display = 'none';
    }
}



        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }





// Delete selected items
async function deleteSelected() {
    const credentialIds = getAllSelectedCredentialIds();
    const domainIds = Array.from(selectedItems.domains);
    
    if (credentialIds.length === 0 && domainIds.length === 0) {
        alert('No items selected');
        return;
    }
    
    if (!confirm(`Are you sure you want to delete ${credentialIds.length} credentials and ${domainIds.length} domains? This action cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/bulk-delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                credential_ids: credentialIds,
                domain_ids: domainIds
            })
        });
        
        const result = await response.json();
        if (result.success) {
            alert(`Successfully deleted ${result.deleted_credentials} credentials and ${result.deleted_domains} domains`);
            location.reload(); // Refresh the page
        } else {
            alert('Error deleting items: ' + result.message);
        }
    } catch (error) {
        alert('Error deleting items: ' + error.message);
    }
}

// Mark selected as checked
async function markAsChecked() {
    const credentialIds = getAllSelectedCredentialIds();
    const domainIds = Array.from(selectedItems.domains);
    
    if (credentialIds.length === 0 && domainIds.length === 0) {
        alert('No items selected');
        return;
    }
    
    try {
        const response = await fetch('/api/bulk-check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                credential_ids: credentialIds,
                domain_ids: domainIds
            })
        });
        
        const result = await response.json();
        if (result.success) {
            alert(`Successfully marked ${result.checked_credentials} credentials and ${result.checked_domains} domains as checked`);
            // Update UI without refreshing
            credentialIds.forEach(id => {
                const checkbox = document.querySelector(`input[data-credential-id="${id}"]`);
                if (checkbox && checkbox.type === 'checkbox') {
                    checkbox.checked = true;
                }
            });
            domainIds.forEach(id => {
                const checkbox = document.querySelector(`.domain-select-checkbox[data-domain-id="${id}"]`);
                if (checkbox) {
                    checkbox.nextElementSibling.checked = true; // The is_checked checkbox
                }
            });
            deselectAll();
        } else {
            alert('Error marking items: ' + result.message);
        }
    } catch (error) {
        alert('Error marking items: ' + error.message);
    }
}

// Export selected items
async function exportSelected() {
    const credentialIds = getAllSelectedCredentialIds();
    const domainIds = Array.from(selectedItems.domains);
    
    if (credentialIds.length === 0 && domainIds.length === 0) {
        alert('No items selected');
        return;
    }
    
    // Ask for export format
    const format = prompt('Select export format (xlsx, csv, txt):', 'xlsx');
    if (!format || !['xlsx', 'csv', 'txt'].includes(format.toLowerCase())) {
        alert('Please select a valid format: xlsx, csv, or txt');
        return;
    }
    
    try {
        const response = await fetch('/api/bulk-export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                credential_ids: credentialIds,
                domain_ids: domainIds,
                format: format.toLowerCase()
            })
        });
        
        if (response.ok) {
            // Create download link
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            a.href = url;
            a.download = `credentials_export_${timestamp}.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            const error = await response.json();
            alert('Error exporting: ' + error.detail);
        }
    } catch (error) {
        alert('Error exporting: ' + error.message);
    }
}