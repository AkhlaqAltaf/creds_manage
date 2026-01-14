        document.addEventListener('DOMContentLoaded', function() {
            refreshCaptcha();
        });
        
        async function refreshCaptcha() {
            try {
                const response = await fetch('/api/captcha');
                const data = await response.json();
                document.getElementById('captchaId').value = data.captcha_id;
                document.getElementById('captchaChallenge').textContent = data.challenge;
                document.getElementById('captchaAnswer').value = '';
            } catch (error) {
                showError('Failed to load CAPTCHA. Please refresh the page.');
            }
        }
        
        function showError(message) {
            const errorDiv = document.getElementById('errorMessage');
            errorDiv.textContent = message;
            errorDiv.classList.add('show');
            setTimeout(() => {
                errorDiv.classList.remove('show');
            }, 5000);
        }
        
        async function handleLogin(event) {
            event.preventDefault();
            const btn = document.getElementById('loginBtn');
            const errorDiv = document.getElementById('errorMessage');
            
            btn.disabled = true;
            errorDiv.classList.remove('show');
            
            const formData = new FormData(event.target);
            const data = {
                username: formData.get('username'),
                password: formData.get('password'),
                captcha_id: formData.get('captcha_id'),
                captcha_answer: formData.get('captcha_answer')
            };
            
            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Redirect to home page
                    window.location.href = '/';
                } else {
                    showError(result.message || 'Login failed');
                    refreshCaptcha(); // Refresh CAPTCHA on failed login
                    btn.disabled = false;
                }
            } catch (error) {
                showError('Network error. Please try again.');
                refreshCaptcha();
                btn.disabled = false;
            }
        }
