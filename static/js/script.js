// DOM Elements
const imageUpload = document.getElementById('imageUpload');
const uploadArea = document.getElementById('uploadArea');
const uploadPlaceholder = document.getElementById('uploadPlaceholder');
const imagePreview = document.getElementById('imagePreview');
const previewImage = document.getElementById('previewImage');
const removeImage = document.getElementById('removeImage');
const scanBtn = document.getElementById('scanBtn');
const resetBtn = document.getElementById('resetBtn');
const loadingModal = document.getElementById('loadingModal');
const langEnglish = document.getElementById('langEnglish');
const langTamil = document.getElementById('langTamil');
const searchInput = document.getElementById('textSearch');
const searchBtn = document.getElementById('searchBtn');
const searchResults = document.getElementById('searchResults');

// Image Upload Handling
if (uploadArea) {
    uploadArea.addEventListener('click', () => {
        imageUpload.click();
    });
}

if (imageUpload) {
    imageUpload.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            // File size validation (5MB)
            if (file.size > 5 * 1024 * 1024) {
                alert('File size too large! Maximum size is 5MB.');
                return;
            }
            
            // File type validation
            if (!file.type.match('image.*')) {
                alert('Please upload an image file (JPG, PNG, etc.)!');
                return;
            }
            
            const reader = new FileReader();
            reader.onload = function(e) {
                previewImage.src = e.target.result;
                uploadPlaceholder.style.display = 'none';
                imagePreview.style.display = 'block';
                if (scanBtn) scanBtn.disabled = false;
            }
            reader.readAsDataURL(file);
        }
    });
}

if (removeImage) {
    removeImage.addEventListener('click', (e) => {
        e.stopPropagation();
        previewImage.src = '';
        uploadPlaceholder.style.display = 'block';
        imagePreview.style.display = 'none';
        imageUpload.value = '';
        if (scanBtn) scanBtn.disabled = true;
    });
}

if (resetBtn) {
    resetBtn.addEventListener('click', () => {
        previewImage.src = '';
        uploadPlaceholder.style.display = 'block';
        imagePreview.style.display = 'none';
        imageUpload.value = '';
        if (scanBtn) scanBtn.disabled = true;
        if (searchResults) searchResults.innerHTML = '';
        if (searchInput) searchInput.value = '';
    });
}

// Scan Button Handler
if (scanBtn) {
    scanBtn.addEventListener('click', async () => {
        const file = imageUpload.files[0];
        if (!file) {
            alert('Please select an image first!');
            return;
        }
        
        // Show loading modal
        if (loadingModal) {
            loadingModal.style.display = 'flex';
        }
        
        try {
            const formData = new FormData();
            formData.append('image', file);
            
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Redirect to result page
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                } else {
                    // Fallback: use medicine name if redirect_url not provided
                    const medicineName = data.medicine_name || 'Medicine';
                    window.location.href = `/result?medicine_name=${encodeURIComponent(medicineName)}`;
                }
            } else {
                throw new Error(data.error || 'Upload failed. Please try again.');
            }
        } catch (error) {
            console.error('Upload Error:', error);
            alert(`Upload failed: ${error.message}`);
        } finally {
            // Hide loading modal
            if (loadingModal) {
                loadingModal.style.display = 'none';
            }
        }
    });
}

// Search Functionality
if (searchBtn) {
    searchBtn.addEventListener('click', performSearch);
}

if (searchInput) {
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
}

async function performSearch() {
    if (!searchInput) return;
    
    const query = searchInput.value.trim();
    if (!query) {
        alert('Please enter a search query about medicines');
        return;
    }
    
    try {
        // Option 1: Direct redirect to result page
        window.location.href = `/result?medicine_name=${encodeURIComponent(query)}`;
        
        // Option 2: If you want to show results on same page (uncomment below)
        /*
        // Show loading state
        if (searchResults) {
            searchResults.innerHTML = `
                <div style="text-align: center; padding: 30px;">
                    <div class="loading-spinner" style="width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; margin: 0 auto 20px; animation: spin 1s linear infinite;"></div>
                    <p>🧠 AI is analyzing your query...</p>
                </div>
            `;
        }
        
        const response = await fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: query })
        });
        
        const data = await response.json();
        
        if (response.ok && data.redirect_url) {
            window.location.href = data.redirect_url;
        } else {
            throw new Error(data.error || 'Search failed');
        }
        */
        
    } catch (error) {
        console.error('Search error:', error);
        alert(`Search failed: ${error.message}. Please try again.`);
        
        if (searchResults) {
            searchResults.innerHTML = `
                <div style="background: #fff5f5; padding: 20px; border-radius: 10px; border-left: 5px solid #ff3b30;">
                    <h3 style="color: #ff3b30; margin-top: 0;">Search Error</h3>
                    <p>${error.message}</p>
                    <button onclick="performSearch()" style="margin-top: 10px; padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 5px; cursor: pointer;">Try Again</button>
                </div>
            `;
        }
    }
}

// Display search results function (for inline results)
function displaySearchResults(data, query) {
    if (!searchResults) return;
    
    let html = `
        <div style="margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid #dee2e6;">
            <h3 style="color: #1a1a1a; margin: 0;">Results for "${query}"</h3>
        </div>
    `;
    
    if (data.answer) {
        html += `
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                    <i class="fas fa-robot" style="color: #2a6ecc; font-size: 1.2rem;"></i>
                    <h4 style="margin: 0; color: #1a1a1a;">AI Response</h4>
                </div>
                <div style="line-height: 1.6;">
                    <p style="margin: 0;">${data.answer.replace(/\n/g, '<br>')}</p>
                </div>
            </div>
        `;
    }
    
    if (data.medicines && data.medicines.length > 0) {
        html += `
            <div>
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                    <i class="fas fa-pills" style="color: #2a6ecc; font-size: 1.2rem;"></i>
                    <h4 style="margin: 0; color: #1a1a1a;">Related Medicines</h4>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px;">
        `;
        
        data.medicines.forEach((medicine) => {
            html += `
                <div style="background: white; border-radius: 10px; padding: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <div style="margin-bottom: 10px;">
                        <h5 style="margin: 0 0 5px 0; color: #1a1a1a;">
                            ${medicine.medicine_name} 
                            <span style="color: #6c757d; font-size: 0.9rem;">(${medicine.brand})</span>
                        </h5>
                        <span style="background: #2a6ecc; color: white; padding: 3px 10px; border-radius: 15px; font-size: 0.8rem;">
                            ${medicine.category}
                        </span>
                    </div>
                    <div style="font-size: 0.9rem;">
                        <p style="margin: 5px 0;"><strong>Uses:</strong> ${medicine.uses.substring(0, 100)}${medicine.uses.length > 100 ? '...' : ''}</p>
                        <p style="margin: 5px 0;"><strong>Dosage:</strong> ${medicine.dosage.substring(0, 100)}${medicine.dosage.length > 100 ? '...' : ''}</p>
                        <div style="margin-top: 10px;">
                            <button onclick="viewMedicineDetails('${medicine.medicine_name}')" style="padding: 6px 12px; background: #2a6ecc; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 0.85rem;">
                                View Details
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    } else if (!data.answer) {
        html += `
            <div style="text-align: center; padding: 30px;">
                <i class="fas fa-search" style="font-size: 2rem; color: #6c757d; margin-bottom: 15px;"></i>
                <p>No specific medicines found. Try asking about a specific medicine name.</p>
            </div>
        `;
    }
    
    searchResults.innerHTML = html;
}

// View medicine details function
function viewMedicineDetails(medicineName) {
    // Redirect to result page with the medicine name
    window.location.href = `/result?medicine_name=${encodeURIComponent(medicineName)}`;
}

// For backward compatibility
function viewMedicine(name) {
    viewMedicineDetails(name);
}

// Language Management for Home Page
if (langEnglish && langTamil) {
    langEnglish.addEventListener('click', () => {
        langEnglish.classList.add('active');
        langTamil.classList.remove('active');
        updateLanguage('english');
    });
    
    langTamil.addEventListener('click', () => {
        langTamil.classList.add('active');
        langEnglish.classList.remove('active');
        updateLanguage('tamil');
    });
}

// Update language function (for home page)
function updateLanguage(lang) {
    // Store language preference in localStorage
    localStorage.setItem('preferredLanguage', lang);
    
    // Update page content based on language
    if (lang === 'tamil') {
        // Update placeholders and text to Tamil
        if (searchInput) {
            searchInput.placeholder = 'எ.கா: "பாராசிட்டமால் எதற்குப் பயன்படுத்தப்படுகிறது?"';
        }
        // You can add more Tamil translations here
        document.documentElement.lang = 'ta';
    } else {
        // English
        if (searchInput) {
            searchInput.placeholder = 'Example: "What is paracetamol used for?" or "Side effects of antibiotics"';
        }
        document.documentElement.lang = 'en';
    }
}

// Language Management for Result Page
const resultLangEnglish = document.getElementById('langEnglish');
const resultLangTamil = document.getElementById('langTamil');

if (resultLangEnglish && resultLangTamil) {
    resultLangEnglish.addEventListener('click', () => {
        resultLangEnglish.classList.add('active');
        resultLangTamil.classList.remove('active');
        updateResultLanguage('english');
    });
    
    resultLangTamil.addEventListener('click', () => {
        resultLangTamil.classList.add('active');
        resultLangEnglish.classList.remove('active');
        updateResultLanguage('tamil');
    });
}

// Update language on result page
function updateResultLanguage(lang) {
    // This function is implemented in result.html inline script
    // The actual implementation is in the result.html template
    console.log(`Switching to ${lang} language on result page`);
    
    // Trigger custom event if needed
    const event = new CustomEvent('languageChange', { detail: { language: lang } });
    window.dispatchEvent(event);
}

// Voice functionality for result page
if (document.getElementById('playVoice')) {
    document.getElementById('playVoice').addEventListener('click', function() {
        const medicineName = document.getElementById('medName')?.textContent || 'Medicine';
        const uses = document.getElementById('medUses')?.textContent || '';
        const dosage = document.getElementById('medDosage')?.textContent || '';
        const precautions = document.getElementById('medPrecautions')?.textContent || '';
        
        const textToSpeak = `${medicineName} is used for ${uses}. Dosage: ${dosage}. Precautions: ${precautions}`;
        
        if ('speechSynthesis' in window) {
            const speech = new SpeechSynthesisUtterance(textToSpeak);
            speech.lang = document.getElementById('langTamil')?.classList.contains('active') ? 'ta-IN' : 'en-US';
            speech.rate = 0.9;
            speech.pitch = 1;
            speech.volume = 1;
            
            // Show loading indicator
            const playBtn = document.getElementById('playVoice');
            const originalHTML = playBtn.innerHTML;
            playBtn.innerHTML = '<i class="fas fa-volume-up"></i> <span>Generating Audio...</span>';
            playBtn.disabled = true;
            
            // Speak
            window.speechSynthesis.speak(speech);
            
            // Restore button when done
            speech.onend = function() {
                playBtn.innerHTML = originalHTML;
                playBtn.disabled = false;
            };
            
            speech.onerror = function() {
                playBtn.innerHTML = originalHTML;
                playBtn.disabled = false;
                alert('Error playing audio. Please try again.');
            };
        } else {
            alert('Text-to-speech is not supported in your browser. Please try Chrome or Edge.');
        }
    });
}

// Initialize language on page load
document.addEventListener('DOMContentLoaded', () => {
    // Set preferred language from localStorage
    const preferredLanguage = localStorage.getItem('preferredLanguage') || 'english';
    
    if (langEnglish && langTamil) {
        if (preferredLanguage === 'tamil') {
            langTamil.classList.add('active');
            langEnglish.classList.remove('active');
            updateLanguage('tamil');
        } else {
            langEnglish.classList.add('active');
            langTamil.classList.remove('active');
            updateLanguage('english');
        }
    }
    
    // Add search examples for home page
    if (searchInput) {
        const examples = [
            "What is paracetamol used for?",
            "Side effects of antibiotics",
            "Dosage for metformin",
            "Compare paracetamol and ibuprofen",
            "Which medicines should avoid alcohol?",
            "Medicine for fever and headache",
            "How to take antibiotics properly",
            "What is the use of cetirizine?"
        ];
        
        let exampleIndex = 0;
        
        // Set initial example
        searchInput.placeholder = `Example: ${examples[exampleIndex]}`;
        
        // Rotate examples every 4 seconds
        const exampleInterval = setInterval(() => {
            if (document.activeElement !== searchInput) {
                exampleIndex = (exampleIndex + 1) % examples.length;
                searchInput.placeholder = `Example: ${examples[exampleIndex]}`;
            }
        }, 4000);
        
        // Clear interval when page is hidden
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                clearInterval(exampleInterval);
            }
        });
    }
    
    // Add CSS for loading spinner if not in style.css
    if (!document.querySelector('#dynamic-css')) {
        const style = document.createElement('style');
        style.id = 'dynamic-css';
        style.textContent = `
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Demo functionality for login page
    const loginForm = document.querySelector('form[method="POST"]');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const username = document.getElementById('username')?.value;
            const password = document.getElementById('password')?.value;
            
            if (username && password) {
                alert('Login successful! (Demo mode - all credentials accepted)');
                window.location.href = '/';
            } else {
                alert('Please enter both username and password');
            }
        });
    }
});

// Handle beforeunload to clear speech synthesis
window.addEventListener('beforeunload', function() {
    if (window.speechSynthesis && window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
    }
});

// Error handling for fetch requests
function handleFetchError(error, context) {
    console.error(`${context} Error:`, error);
    
    let errorMessage = 'An error occurred. Please try again.';
    
    if (error.message.includes('Failed to fetch')) {
        errorMessage = 'Cannot connect to server. Please check your internet connection.';
    } else if (error.message.includes('NetworkError')) {
        errorMessage = 'Network error. Please check your connection.';
    } else if (error.message.includes('500')) {
        errorMessage = 'Server error. Please try again later.';
    } else {
        errorMessage = error.message || 'An unexpected error occurred.';
    }
    
    return errorMessage;
}

// Utility function to show notification
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div style="position: fixed; top: 20px; right: 20px; padding: 15px 20px; border-radius: 8px; background: ${type === 'error' ? '#ff3b30' : type === 'success' ? '#34c759' : '#2a6ecc'}; color: white; z-index: 9999; box-shadow: 0 4px 12px rgba(0,0,0,0.15); min-width: 300px; max-width: 400px;">
            <p style="margin: 0; font-size: 0.95rem;">${message}</p>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + S to search
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (searchInput && document.activeElement !== searchInput) {
            searchInput.focus();
        }
    }
    
    // Esc to clear search
    if (e.key === 'Escape') {
        if (searchInput) {
            searchInput.value = '';
            if (searchResults) searchResults.innerHTML = '';
        }
        if (imagePreview.style.display === 'block') {
            resetBtn?.click();
        }
    }
    
    // Ctrl/Cmd + U to open file upload
    if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
        e.preventDefault();
        if (uploadArea && !imageUpload.files[0]) {
            uploadArea.click();
        }
    }
});

// Add styles for notification
if (!document.querySelector('#notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        .notification {
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        .notification-error {
            background: #ff3b30 !important;
        }
        
        .notification-success {
            background: #34c759 !important;
        }
        
        .notification-info {
            background: #2a6ecc !important;
        }
    `;
    document.head.appendChild(style);
}