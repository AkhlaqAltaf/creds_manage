        async function createUser(event) {
            event.preventDefault();
            const formData = new FormData(event.target);
            const data = {
                username: formData.get('username'),
                password: formData.get('password'),
                role: formData.get('role')
            };
            
            try {
                const response = await fetch('/api/admin/users', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                if (response.ok) {
                    showMessage('userMessage', 'User created successfully!', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showMessage('userMessage', result.detail || 'Error creating user', 'error');
                }
            } catch (error) {
                showMessage('userMessage', 'Error: ' + error.message, 'error');
            }
        }
        
        async function assignDomain(event) {
            event.preventDefault();
            const formData = new FormData(event.target);
            const data = {
                user_id: parseInt(formData.get('user_id')),
                domain_id: parseInt(formData.get('domain_id'))
            };
            
            try {
                const response = await fetch('/api/admin/assign-domain', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                if (result.success) {
                    showMessage('assignmentMessage', result.message, 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showMessage('assignmentMessage', result.message || 'Error assigning domain', 'error');
                }
            } catch (error) {
                showMessage('assignmentMessage', 'Error: ' + error.message, 'error');
            }
        }
        
        async function removeAssignment(assignmentId) {
            if (!confirm('Are you sure you want to remove this assignment?')) return;
            
            try {
                const response = await fetch(`/api/admin/assignments/${assignmentId}`, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                if (result.success) {
                    showMessage('assignmentMessage', 'Assignment removed', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showMessage('assignmentMessage', 'Error removing assignment', 'error');
                }
            } catch (error) {
                showMessage('assignmentMessage', 'Error: ' + error.message, 'error');
            }
        }
        
        async function createStatus(event) {
            event.preventDefault();
            const formData = new FormData(event.target);
            const data = {
                name: formData.get('name'),
                description: formData.get('description'),
                color: formData.get('color')
            };
            
            try {
                const response = await fetch('/api/admin/statuses', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                if (response.ok) {
                    showMessage('statusMessage', 'Status created successfully!', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showMessage('statusMessage', result.detail || 'Error creating status', 'error');
                }
            } catch (error) {
                showMessage('statusMessage', 'Error: ' + error.message, 'error');
            }
        }
        
        function editUser(userId, username, role) {
            document.getElementById('editUserId').value = userId;
            document.getElementById('editUsername').value = username;
            document.getElementById('editRole').value = role;
            document.getElementById('editPassword').value = '';
            document.getElementById('editUserModal').style.display = 'flex';
        }
        
        function closeEditUserModal() {
            document.getElementById('editUserModal').style.display = 'none';
        }
        
        async function updateUser(event) {
            event.preventDefault();
            const formData = new FormData(event.target);
            const userId = formData.get('user_id');
            const data = {
                username: formData.get('username'),
                role: formData.get('role')
            };
            
            // Password is optional - only include if provided
            const password = formData.get('password');
            if (password && password.trim()) {
                data.password = password;
            }
            
            try {
                const response = await fetch(`/api/admin/users/${userId}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                if (response.ok) {
                    showMessage('userMessage', 'User updated successfully!', 'success');
                    closeEditUserModal();
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showMessage('userMessage', result.detail || 'Error updating user', 'error');
                }
            } catch (error) {
                showMessage('userMessage', 'Error: ' + error.message, 'error');
            }
        }
        
        async function deleteUser(userId) {
            if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) return;
            
            try {
                const response = await fetch(`/api/admin/users/${userId}`, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                if (result.success) {
                    showMessage('userMessage', 'User deleted successfully', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showMessage('userMessage', result.detail || 'Error deleting user', 'error');
                }
            } catch (error) {
                showMessage('userMessage', 'Error: ' + error.message, 'error');
            }
        }
        
        function editStatus(statusId, name, description, color) {
            document.getElementById('editStatusId').value = statusId;
            document.getElementById('editStatusName').value = name;
            document.getElementById('editStatusDescription').value = description || '';
            document.getElementById('editStatusColor').value = color || '#667eea';
            document.getElementById('editStatusModal').style.display = 'flex';
        }
        
        function closeEditStatusModal() {
            document.getElementById('editStatusModal').style.display = 'none';
        }
        
        async function updateStatus(event) {
            event.preventDefault();
            const formData = new FormData(event.target);
            const statusId = formData.get('status_id');
            const data = {
                name: formData.get('name'),
                description: formData.get('description'),
                color: formData.get('color')
            };
            
            try {
                const response = await fetch(`/api/admin/statuses/${statusId}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                if (response.ok) {
                    showMessage('statusMessage', 'Status updated successfully!', 'success');
                    closeEditStatusModal();
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showMessage('statusMessage', result.detail || 'Error updating status', 'error');
                }
            } catch (error) {
                showMessage('statusMessage', 'Error: ' + error.message, 'error');
            }
        }
        
        async function deleteStatus(statusId) {
            if (!confirm('Are you sure you want to delete this status? It will be deactivated.')) return;
            
            try {
                const response = await fetch(`/api/admin/statuses/${statusId}`, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                if (result.success) {
                    showMessage('statusMessage', 'Status deleted successfully', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showMessage('statusMessage', result.detail || 'Error deleting status', 'error');
                }
            } catch (error) {
                showMessage('statusMessage', 'Error: ' + error.message, 'error');
            }
        }
        
        async function uploadFiles(event) {
            event.preventDefault();
            const fileInput = document.getElementById('fileInput');
            const files = fileInput.files;
            
            if (files.length === 0) {
                showMessage('uploadMessage', 'Please select files to upload', 'error');
                return;
            }
            
            const formData = new FormData();
            for (let file of files) {
                formData.append('files', file);
            }
            
            try {
                const response = await fetch('/api/admin/upload-files', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                if (result.success) {
                    showMessage('uploadMessage', result.message, 'success');
                    fileInput.value = '';
                } else {
                    showMessage('uploadMessage', 'Error uploading files', 'error');
                }
            } catch (error) {
                showMessage('uploadMessage', 'Error: ' + error.message, 'error');
            }
        }
        
        function showMessage(elementId, message, type) {
            const element = document.getElementById(elementId);
            element.textContent = message;
            element.className = `message ${type}`;
            setTimeout(() => {
                element.className = 'message';
            }, 5000);
        }
        
        // Close modals when clicking outside
        window.onclick = function(event) {
            const editUserModal = document.getElementById('editUserModal');
            const editStatusModal = document.getElementById('editStatusModal');
            if (event.target == editUserModal) {
                closeEditUserModal();
            }
            if (event.target == editStatusModal) {
                closeEditStatusModal();
            }
        }

