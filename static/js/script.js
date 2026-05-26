/**
 * Smart Notes Application - Frontend JavaScript (FIXED VERSION)
 * Handles all UI interactions and API calls
 */

// ============================================================================
// LOGIN FUNCTIONS
// ============================================================================

async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value.trim();
    const messageEl = document.getElementById('loginMessage');
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            messageEl.textContent = '✅ Login successful! Redirecting...';
            messageEl.style.color = 'var(--success-color)';
            document.getElementById('loginForm').reset();
            setTimeout(() => {
                showApp();
                initializeApp();
            }, 1000);
        } else {
            messageEl.textContent = '❌ ' + data.message;
            messageEl.style.color = 'var(--danger-color)';
        }
    } catch (error) {
        messageEl.textContent = '❌ Login failed. Please try again.';
        messageEl.style.color = 'var(--danger-color)';
        console.error('Login error:', error);
    }
}

async function handleRegister(event) {
    event.preventDefault();
    
    const username = document.getElementById('regUsername').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const password = document.getElementById('regPassword').value.trim();
    const confirmPassword = document.getElementById('regConfirmPassword').value.trim();
    const messageEl = document.getElementById('registerMessage');
    
    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password, confirm_password: confirmPassword })
        });
        
        const data = await response.json();
        
        if (data.success) {
            messageEl.textContent = '✅ ' + data.message;
            messageEl.style.color = 'var(--success-color)';
            document.getElementById('registerForm').reset();
            setTimeout(() => switchTab('login'), 1500);
        } else {
            messageEl.textContent = '❌ ' + data.message;
            messageEl.style.color = 'var(--danger-color)';
        }
    } catch (error) {
        messageEl.textContent = '❌ Registration failed. Please try again.';
        messageEl.style.color = 'var(--danger-color)';
        console.error('Register error:', error);
    }
}

async function handleLogout() {
    if (!confirm('Are you sure you want to logout?')) return;
    
    try {
        const response = await fetch('/api/logout', { method: 'POST' });
        const data = await response.json();
        if (data.success) showLogin();
    } catch (error) {
        console.error('Logout error:', error);
    }
}

function switchTab(tab) {
    document.getElementById('loginForm').classList.remove('active');
    document.getElementById('registerForm').classList.remove('active');
    document.querySelectorAll('.login-tab-btn').forEach(btn => btn.classList.remove('active'));
    
    if (tab === 'login') {
        document.getElementById('loginForm').classList.add('active');
        document.querySelectorAll('.login-tab-btn')[0].classList.add('active');
    } else {
        document.getElementById('registerForm').classList.add('active');
        document.querySelectorAll('.login-tab-btn')[1].classList.add('active');
    }
    
    document.getElementById('loginMessage').textContent = '';
    document.getElementById('registerMessage').textContent = '';
}

function showLogin() {
    document.getElementById('loginPage').style.display = 'flex';
    document.getElementById('appPage').style.display = 'none';
}

function showApp() {
    document.getElementById('loginPage').style.display = 'none';
    document.getElementById('appPage').style.display = 'flex';
}

async function checkAuthStatus() {
    try {
        const response = await fetch('/api/auth_status');
        const data = await response.json();
        
        if (data.is_logged_in) {
            showApp();
            document.getElementById('userInfo').textContent = `👤 ${data.username}`;
            initializeApp(); // ← was missing: needed on page refresh when already logged in
            return true;
        } else {
            showLogin();
            return false;
        }
    } catch (error) {
        showLogin();
        return false;
    }
}

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

const state = {
    allNotes: [],
    filteredNotes: [],
    currentSubject: null,
    currentNoteId: null,
    currentEditingNoteId: null,
    appMode: 'LOCAL',
    isLoading: false,
    currentSort: 'latest'
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Smart Notes Application Initialized');
    checkAuthStatus();
});

function initializeApp() {
    fetchAppConfig();
    loadNotes();
    loadSubjects();
    setupEventListeners();
    updateStatistics();
}

function setupEventListeners() {
    // Guard: only attach listeners once
    if (window._listenersAttached) return;
    window._listenersAttached = true;

    document.getElementById('noteForm').addEventListener('submit', handleAddNote);
    
    const fileInput = document.getElementById('noteFile');
    fileInput.addEventListener('change', handleFileSelect);
    
    const fileLabel = document.querySelector('.file-label');
    fileLabel.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileLabel.style.borderColor = 'var(--primary-color)';
        fileLabel.style.backgroundColor = 'rgba(79, 70, 229, 0.1)';
    });
    fileLabel.addEventListener('dragleave', () => {
        fileLabel.style.borderColor = 'var(--gray-border)';
        fileLabel.style.backgroundColor = 'var(--light-bg)';
    });
    fileLabel.addEventListener('drop', (e) => {
        e.preventDefault();
        fileLabel.style.borderColor = 'var(--gray-border)';
        fileLabel.style.backgroundColor = 'var(--light-bg)';
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect();
        }
    });
}

// ============================================================================
// FILE URL HELPER — handles LOCAL vs CLOUD mode
// ============================================================================

/**
 * Given a file_url value from the database, returns a usable href.
 *
 * LOCAL mode: file_url is just a filename  → /uploads/<filename>
 * CLOUD mode: file_url is an S3 key        → fetch a pre-signed URL from
 *             /api/file_url?key=<s3_key> and open it in a new tab.
 *
 * Usage:
 *   <a href="#" onclick="openFile('uploads/20260430_file.pdf'); return false;">Open</a>
 */
async function openFile(fileUrl) {
    if (!fileUrl) return;

    if (state.appMode === 'LOCAL') {
        // Simple local file — open directly
        window.open(`/uploads/${fileUrl}`, '_blank');
        return;
    }

    // CLOUD mode — get a pre-signed S3 URL first
    try {
        const response = await fetch(`/api/file_url?key=${encodeURIComponent(fileUrl)}`);
        const data = await response.json();

        if (data.success && data.url) {
            window.open(data.url, '_blank');
        } else {
            showNotification('❌ Could not open file: ' + (data.message || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error fetching file URL:', error);
        showNotification('❌ Error opening file', 'danger');
    }
}

/**
 * Returns an HTML anchor that works for both LOCAL and CLOUD.
 * Uses onclick so the pre-signed URL is fetched fresh on every click
 * (pre-signed URLs expire after 1 hour).
 */
function fileLink(fileUrl, label) {
    if (!fileUrl) return '';
    const safeUrl = escapeHtml(fileUrl);
    const safeLabel = escapeHtml(label || fileUrl);
    return `<a href="#" onclick="openFile('${safeUrl}'); return false;" style="color: inherit; text-decoration: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1;">${safeLabel}</a>`;
}

// ============================================================================
// API CALLS
// ============================================================================

async function fetchAppConfig() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        
        state.appMode = data.app_mode;
        document.getElementById('modeBadge').textContent = data.app_mode;
        document.getElementById('helpMode').textContent = data.app_mode;
        
        console.log(`✅ App Mode: ${data.app_mode}`);
    } catch (error) {
        console.error('Error fetching config:', error);
    }
}

async function loadNotes() {
    try {
        state.isLoading = true;
        const subject = state.currentSubject ? `?subject=${state.currentSubject}` : '?';
        const separator = subject === '?' ? '' : '&';
        const sortParam = `${separator}sort=${state.currentSort}`;
        
        const response = await fetch(`/api/get_notes${subject}${sortParam}`);
        const data = await response.json();
        
        if (data.success) {
            state.allNotes = data.notes;
            state.filteredNotes = data.notes;
            renderNotes();
            updateStatistics();
        }
    } catch (error) {
        console.error('Error loading notes:', error);
        showNotification('Error loading notes', 'danger');
    } finally {
        state.isLoading = false;
    }
}

async function loadSubjects() {
    try {
        const response = await fetch('/api/subjects');
        const data = await response.json();
        
        if (data.success) {
            renderSubjects(data.subjects);
            renderSubjectSuggestions(data.subjects);
        }
    } catch (error) {
        console.error('Error loading subjects:', error);
    }
}

async function handleAddNote(e) {
    e.preventDefault();
    
    try {
        const formData = new FormData();
        formData.append('title', document.getElementById('noteTitle').value);
        formData.append('subject', document.getElementById('noteSubject').value);
        formData.append('content', document.getElementById('noteContent').value);
        
        const file = document.getElementById('noteFile').files[0];
        if (file) formData.append('file', file);
        
        const isEditMode = state.currentEditingNoteId !== null;
        const url = isEditMode ? `/api/update_note/${state.currentEditingNoteId}` : '/api/add_note';
        const method = isEditMode ? 'PUT' : 'POST';
        
        const response = await fetch(url, { method, body: formData });
        const data = await response.json();
        
        if (data.success) {
            showNotification(
                isEditMode ? '✏️ Note updated successfully!' : '✅ Note created successfully!',
                'success'
            );
            
            document.getElementById('noteForm').reset();
            document.getElementById('filePreview').innerHTML = '';
            document.getElementById('filePreview').classList.remove('active');
            document.getElementById('existingFilePreview').innerHTML = '';
            document.getElementById('existingFilePreview').classList.remove('active');
            closeNoteModal();
            
            state.currentEditingNoteId = null;
            state.currentNoteId = null;
            
            loadNotes();
            loadSubjects();
        } else {
            showNotification(data.message || 'Error saving note', 'danger');
        }
    } catch (error) {
        console.error('Error adding note:', error);
        showNotification('Error saving note', 'danger');
    }
}

async function deleteNote(noteId) {
    if (!confirm('⚠️ Are you sure you want to delete this note?')) return;
    
    try {
        const response = await fetch(`/api/delete_note/${noteId}`, { method: 'DELETE' });
        const data = await response.json();
        
        if (data.success) {
            showNotification('🗑️ Note deleted successfully!', 'success');
            closeViewModal();
            loadNotes();
            loadSubjects();
        } else {
            showNotification(data.message || 'Error deleting note', 'danger');
        }
    } catch (error) {
        console.error('Error deleting note:', error);
        showNotification('Error deleting note', 'danger');
    }
}

async function pinNote(noteId, currentPinnedState) {
    try {
        const response = await fetch(`/api/pin_note/${noteId}`, { method: 'PUT' });
        const data = await response.json();
        
        if (data.success) {
            loadNotes();
        } else {
            showNotification(data.message || 'Error pinning note', 'danger');
        }
    } catch (error) {
        console.error('Error pinning note:', error);
        showNotification('Error pinning note', 'danger');
    }
}

// ============================================================================
// UI RENDERING
// ============================================================================

function renderNotes() {
    const container = document.getElementById('notesContainer');
    
    if (state.filteredNotes.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>📝 No notes yet</p>
                <p class="empty-state-subtitle">
                    ${state.currentSubject
                        ? `No notes in ${state.currentSubject}. Create one now!`
                        : 'Create your first note to get started!'}
                </p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = state.filteredNotes.map(note => createNoteCard(note)).join('');
}

function createNoteCard(note) {
    const truncatedContent = note.content.length > 150
        ? note.content.substring(0, 150) + '...'
        : note.content;
    
    const pinnedClass = note.pinned ? 'pinned' : '';
    const pinnedIcon = note.pinned ? '⭐' : '☆';

    // ✅ FIX: use fileLink() helper instead of hardcoded /uploads/
    const fileSection = note.file_url ? `
        <div class="note-card-file">
            <span class="note-card-file-icon">📄</span>
            ${fileLink(note.file_url, note.file_url)}
        </div>
    ` : '';
    
    return `
        <div class="note-card">
            <div class="note-card-header">
                <div style="flex: 1;">
                    <div class="note-card-title">${escapeHtml(note.title)}</div>
                    <span class="note-card-subject">${escapeHtml(note.subject)}</span>
                </div>
                <button class="note-card-pin ${pinnedClass}" onclick="pinNote('${note.id}', ${note.pinned})">
                    ${pinnedIcon}
                </button>
            </div>
            
            <p class="note-card-content">${escapeHtml(truncatedContent)}</p>
            
            <div class="note-card-tags">
                ${note.tags && note.tags.length > 0
                    ? note.tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')
                    : '<span class="tag">untagged</span>'
                }
            </div>
            
            ${fileSection}
            
            <div class="note-card-meta">
                <span>${formatDate(note.created_at)}</span>
            </div>
            
            <div class="note-card-actions">
                <button class="note-card-btn btn-view" onclick="viewNote('${note.id}')">👁️ View</button>
                <button class="note-card-btn btn-delete" onclick="deleteNote('${note.id}')">🗑️ Delete</button>
            </div>
        </div>
    `;
}

function renderSubjects(subjects) {
    const subjectsList = document.getElementById('subjectsList');
    
    subjectsList.innerHTML = `
        <button class="subject-btn ${!state.currentSubject ? 'active' : ''}" onclick="filterBySubject(null)">
            📌 All Notes
        </button>
        ${subjects.map(subject => `
            <button class="subject-btn ${state.currentSubject === subject ? 'active' : ''}" 
                    onclick="filterBySubject('${escapeHtml(subject)}')">
                🏷️ ${escapeHtml(subject)}
            </button>
        `).join('')}
    `;
}

function renderSubjectSuggestions(subjects) {
    document.getElementById('subjectSuggestions').innerHTML =
        subjects.map(s => `<option value="${escapeHtml(s)}">`).join('');
}

function updateStatistics() {
    document.getElementById('totalNotes').textContent = state.allNotes.length;
    document.getElementById('pinnedNotes').textContent = state.allNotes.filter(n => n.pinned).length;
}

// ============================================================================
// MODAL MANAGEMENT
// ============================================================================

function openAddNoteModal() {
    state.currentEditingNoteId = null;
    state.currentNoteId = null;
    document.getElementById('modalTitle').textContent = '➕ Create New Note';
    document.getElementById('noteForm').reset();
    document.getElementById('filePreview').innerHTML = '';
    document.getElementById('filePreview').classList.remove('active');
    document.getElementById('existingFilePreview').innerHTML = '';
    document.getElementById('existingFilePreview').classList.remove('active');
    document.getElementById('noteModal').classList.add('active');
}

function closeNoteModal() {
    document.getElementById('noteModal').classList.remove('active');
    state.currentEditingNoteId = null;
}

async function viewNote(noteId) {
    try {
        const response = await fetch(`/api/get_note/${noteId}`);
        const data = await response.json();
        
        if (data.success) {
            const note = data.note;
            state.currentNoteId = noteId;
            
            const tagsHtml = (note.tags && note.tags.length > 0)
                ? note.tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')
                : '<span class="tag">untagged</span>';
            
            // ✅ FIX: use fileLink() helper instead of hardcoded /uploads/
            const fileHtml = note.file_url ? `
                <div class="view-modal-item">
                    <div class="view-modal-label">📎 Attachment</div>
                    <div class="view-modal-value">
                        <div class="view-modal-file">
                            📄 ${fileLink(note.file_url, note.file_url)}
                        </div>
                    </div>
                </div>
            ` : '';
            
            document.getElementById('viewModalBody').innerHTML = `
                <div class="view-modal-item">
                    <div class="view-modal-label">📌 Title</div>
                    <div class="view-modal-value">${escapeHtml(note.title)}</div>
                </div>
                <div class="view-modal-item">
                    <div class="view-modal-label">🏷️ Subject</div>
                    <div class="view-modal-value">
                        <span class="note-card-subject">${escapeHtml(note.subject)}</span>
                    </div>
                </div>
                <div class="view-modal-item">
                    <div class="view-modal-label">✍️ Content</div>
                    <div class="view-modal-value">${escapeHtml(note.content).replace(/\n/g, '<br>')}</div>
                </div>
                <div class="view-modal-item">
                    <div class="view-modal-label">🏷️ Tags</div>
                    <div class="view-modal-value">
                        <div class="view-modal-tags">${tagsHtml}</div>
                    </div>
                </div>
                ${fileHtml}
                <div class="view-modal-item">
                    <div class="view-modal-label">📅 Created</div>
                    <div class="view-modal-value">${formatDate(note.created_at)}</div>
                </div>
            `;
            
            document.getElementById('viewModal').classList.add('active');
        }
    } catch (error) {
        console.error('Error viewing note:', error);
        showNotification('Error loading note', 'danger');
    }
}

function closeViewModal() {
    document.getElementById('viewModal').classList.remove('active');
    state.currentNoteId = null;
}

function editCurrentNote() {
    const note = state.allNotes.find(n => n.id === state.currentNoteId);
    
    if (note) {
        state.currentEditingNoteId = state.currentNoteId;
        
        document.getElementById('modalTitle').textContent = '✏️ Edit Note';
        document.getElementById('noteTitle').value = note.title;
        document.getElementById('noteSubject').value = note.subject;
        document.getElementById('noteContent').value = note.content;
        
        // ✅ FIX: use fileLink() helper instead of hardcoded /uploads/
        if (note.file_url) {
            const existingFilePreview = document.getElementById('existingFilePreview');
            existingFilePreview.innerHTML = `
                <strong>📎 Current File:</strong><br>
                📄 ${fileLink(note.file_url, note.file_url)}
                <br><small style="color: #64748B;">Upload a new file to replace it</small>
            `;
            existingFilePreview.classList.add('active');
        } else {
            document.getElementById('existingFilePreview').classList.remove('active');
        }
        
        document.getElementById('filePreview').innerHTML = '';
        document.getElementById('filePreview').classList.remove('active');
        
        closeViewModal();
        document.getElementById('noteModal').classList.add('active');
    }
}

function deleteCurrentNote() {
    deleteNote(state.currentNoteId);
}

function showHelpModal() {
    document.getElementById('helpModal').classList.add('active');
}

function closeHelpModal() {
    document.getElementById('helpModal').classList.remove('active');
}

window.showHelp = showHelpModal;

// ============================================================================
// FILTER & SEARCH
// ============================================================================

function filterBySubject(subject) {
    state.currentSubject = subject;
    
    document.querySelectorAll('.subject-btn').forEach(btn => btn.classList.remove('active'));
    
    if (subject === null) {
        document.querySelectorAll('.subject-btn')[0].classList.add('active');
    } else {
        document.querySelectorAll('.subject-btn').forEach(btn => {
            if (btn.textContent.includes(subject)) btn.classList.add('active');
        });
    }
    
    loadNotes();
}

function searchNotes() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    
    state.filteredNotes = state.allNotes.filter(note =>
        note.title.toLowerCase().includes(searchTerm) ||
        note.content.toLowerCase().includes(searchTerm)
    );
    
    renderNotes();
}

function clearSearch() {
    document.getElementById('searchInput').value = '';
    state.filteredNotes = [...state.allNotes];
    renderNotes();
}

function changeSortOrder() {
    state.currentSort = document.getElementById('sortSelect').value;
    loadNotes();
}

// ============================================================================
// FILE HANDLING
// ============================================================================

function handleFileSelect() {
    const fileInput = document.getElementById('noteFile');
    const file = fileInput.files[0];
    const filePreview = document.getElementById('filePreview');
    
    if (file) {
        const maxSize = 50 * 1024 * 1024;
        const allowedExtensions = ['txt', 'pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'gif'];
        const fileExtension = file.name.split('.').pop().toLowerCase();
        
        if (file.size > maxSize) {
            showNotification('File size exceeds 50MB limit', 'danger');
            fileInput.value = '';
            return;
        }
        
        if (!allowedExtensions.includes(fileExtension)) {
            showNotification('File type not allowed', 'danger');
            fileInput.value = '';
            return;
        }
        
        filePreview.innerHTML = `
            <strong>📎 New File Selected:</strong> ${escapeHtml(file.name)}
            <br><small>${(file.size / 1024).toFixed(2)} KB</small>
        `;
        filePreview.classList.add('active');
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function formatDate(dateString) {
    const date = new Date(dateString);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    if (date.toDateString() === today.toDateString()) {
        return `Today at ${date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
    } else if (date.toDateString() === yesterday.toDateString()) {
        return `Yesterday at ${date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
    } else {
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined
        });
    }
}

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        font-weight: 600;
        z-index: 2000;
        max-width: 400px;
        animation: fadeIn 0.3s ease-out;
    `;
    
    const bgColors = {
        'success': '#10B981',
        'danger': '#EF4444',
        'warning': '#F59E0B',
        'info': '#3B82F6'
    };
    
    notification.style.backgroundColor = bgColors[type] || bgColors['info'];
    notification.style.color = 'white';
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'fadeOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

const style = document.createElement('style');
style.textContent = `
    @keyframes fadeOut {
        from { opacity: 1; transform: translateX(0); }
        to   { opacity: 0; transform: translateX(20px); }
    }
`;
document.head.appendChild(style);

// ============================================================================
// GLOBAL EXPORTS
// ============================================================================

window.openAddNoteModal  = openAddNoteModal;
window.closeNoteModal    = closeNoteModal;
window.deleteNote        = deleteNote;
window.pinNote           = pinNote;
window.viewNote          = viewNote;
window.closeViewModal    = closeViewModal;
window.editCurrentNote   = editCurrentNote;
window.deleteCurrentNote = deleteCurrentNote;
window.filterBySubject   = filterBySubject;
window.searchNotes       = searchNotes;
window.clearSearch       = clearSearch;
window.changeSortOrder   = changeSortOrder;
window.openFile          = openFile;   // needed by fileLink() onclick