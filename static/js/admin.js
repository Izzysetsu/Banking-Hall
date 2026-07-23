document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const progressDiv = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const playlistBody = document.getElementById('playlist-body');
    const usersBody = document.getElementById('users-body');
    const saveBtn = document.getElementById('save-btn');
    const toast = document.getElementById('toast');

    let playlist = [];
    let usersList = [];
    let config = { supabase_enabled: false };

    // Tab Navigation
    window.switchTab = (tabName) => {
        document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
        document.querySelectorAll('.nav-links li').forEach(el => el.classList.remove('active'));

        if (tabName === 'playlist') {
            document.getElementById('tab-playlist').style.display = 'block';
            document.getElementById('nav-playlist').classList.add('active');
            document.getElementById('page-title').innerText = 'Dashboard Admin - Playlist';
        } else if (tabName === 'users') {
            document.getElementById('tab-users').style.display = 'block';
            document.getElementById('nav-users').classList.add('active');
            document.getElementById('page-title').innerText = 'Dashboard Admin - Manajemen User';
            fetchUsers();
        }
    };

    // Modal Helpers
    window.openModal = (modalId) => {
        document.getElementById(modalId).style.display = 'flex';
    };

    window.closeModal = (modalId) => {
        document.getElementById(modalId).style.display = 'none';
    };

    // USER MANAGEMENT LOGIC
    async function fetchUsers() {
        try {
            const res = await fetch('/api/users');
            if (res.ok) {
                usersList = await res.json();
                renderUsers();
            } else if (res.status === 401) {
                window.location.href = '/login';
            }
        } catch (err) {
            console.error('Error fetching users:', err);
        }
    }

    function renderUsers() {
        if (!usersBody) return;
        usersBody.innerHTML = '';
        usersList.forEach(u => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>#${u.id}</td>
                <td><strong>${u.username}</strong></td>
                <td><span class="user-role">${u.role || 'admin'}</span></td>
                <td>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-secondary" onclick="openResetModal(${u.id}, '${u.username}')" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;"><i class="fa-solid fa-key"></i> Reset Password</button>
                        <button class="btn btn-danger" onclick="deleteUserAccount(${u.id}, '${u.username}')" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;"><i class="fa-solid fa-trash"></i> Hapus</button>
                    </div>
                </td>
            `;
            usersBody.appendChild(tr);
        });
    }

    window.openAddUserModal = () => {
        document.getElementById('new-username').value = '';
        document.getElementById('new-password').value = '';
        openModal('modal-add-user');
    };

    window.submitAddUser = async () => {
        const username = document.getElementById('new-username').value.trim();
        const password = document.getElementById('new-password').value.trim();

        if (!username || !password) {
            showToast('Username dan password wajib diisi!');
            return;
        }

        const res = await fetch('/api/users/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();
        if (res.ok) {
            showToast('User admin baru berhasil ditambahkan!');
            closeModal('modal-add-user');
            fetchUsers();
        } else {
            showToast('Gagal: ' + (data.error || 'Terjadi kesalahan'));
        }
    };

    window.openResetModal = (id, username) => {
        document.getElementById('reset-user-id').value = id;
        document.getElementById('reset-username-label').innerText = username;
        document.getElementById('reset-new-password').value = '';
        openModal('modal-reset-password');
    };

    window.submitResetPassword = async () => {
        const user_id = document.getElementById('reset-user-id').value;
        const new_password = document.getElementById('reset-new-password').value.trim();

        if (!new_password) {
            showToast('Password baru tidak boleh kosong!');
            return;
        }

        const res = await fetch('/api/users/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id, new_password })
        });

        if (res.ok) {
            showToast('Password berhasil di-reset!');
            closeModal('modal-reset-password');
        } else {
            const data = await res.json();
            showToast('Gagal: ' + (data.error || 'Terjadi kesalahan'));
        }
    };

    window.deleteUserAccount = async (id, username) => {
        if (confirm(`Yakin ingin menghapus akun admin "${username}"?`)) {
            const res = await fetch(`/api/users/delete/${id}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok) {
                showToast(`User ${username} berhasil dihapus!`);
                fetchUsers();
            } else {
                showToast('Gagal menghapus: ' + (data.error || 'Terjadi kesalahan'));
            }
        }
    };

    // CONFIG & PLAYLIST LOGIC
    async function fetchConfig() {
        try {
            const res = await fetch('/api/config');
            config = await res.json();
        } catch (e) {
            console.error('Error fetching config:', e);
        }
    }

    async function fetchPlaylist() {
        const res = await fetch('/api/playlist');
        playlist = await res.json();
        renderPlaylist();
    }

    function renderPlaylist() {
        playlistBody.innerHTML = '';
        playlist.forEach((item, index) => {
            const tr = document.createElement('tr');
            
            let preview = '';
            const mediaSrc = item.url ? item.url : `/static/uploads/${item.filename}`;
            if(item.type === 'video') {
                preview = `<video class="media-preview" src="${mediaSrc}"></video>`;
            } else {
                preview = `<img class="media-preview" src="${mediaSrc}">`;
            }

            tr.innerHTML = `
                <td>
                    <div class="order-controls">
                        <button class="btn-icon" onclick="moveUp(${index})" ${index === 0 ? 'disabled' : ''}><i class="fa-solid fa-arrow-up"></i></button>
                        <button class="btn-icon" onclick="moveDown(${index})" ${index === playlist.length - 1 ? 'disabled' : ''}><i class="fa-solid fa-arrow-down"></i></button>
                    </div>
                </td>
                <td>${preview}</td>
                <td><span style="text-transform: capitalize;">${item.type}</span></td>
                <td>
                    ${item.type === 'video' ? 
                      `<input type="text" class="form-control" value="Auto (Full Video)" disabled style="opacity:0.6; cursor:not-allowed;" title="Durasi akan otomatis menyesuaikan panjang video.">` : 
                      `<input type="number" class="form-control" value="${item.duration}" min="1" onchange="updateItem(${index}, 'duration', this.value)">`
                    }
                </td>
                <td>
                    <select class="form-control" onchange="updateItem(${index}, 'animation', this.value)">
                        <option value="fade" ${item.animation === 'fade' ? 'selected' : ''}>Fade In</option>
                        <option value="slideLeft" ${item.animation === 'slideLeft' ? 'selected' : ''}>Slide Left</option>
                        <option value="slideUp" ${item.animation === 'slideUp' ? 'selected' : ''}>Slide Up</option>
                        <option value="zoomIn" ${item.animation === 'zoomIn' ? 'selected' : ''}>Zoom In</option>
                        <option value="flip" ${item.animation === 'flip' ? 'selected' : ''}>Flip 3D</option>
                    </select>
                </td>
                <td>
                    <button class="btn-icon btn-danger" onclick="deleteItem('${item.id}', '${item.filename}')"><i class="fa-solid fa-trash"></i></button>
                </td>
            `;
            playlistBody.appendChild(tr);
        });
    }

    window.updateItem = (index, field, value) => {
        if(field === 'duration') playlist[index].duration = parseInt(value);
        if(field === 'animation') playlist[index].animation = value;
    };

    window.moveUp = (index) => {
        if(index > 0) {
            const temp = playlist[index];
            playlist[index] = playlist[index-1];
            playlist[index-1] = temp;
            
            const tempOrder = playlist[index].order_index;
            playlist[index].order_index = playlist[index-1].order_index;
            playlist[index-1].order_index = tempOrder;
            
            renderPlaylist();
        }
    };

    window.moveDown = (index) => {
        if(index < playlist.length - 1) {
            const temp = playlist[index];
            playlist[index] = playlist[index+1];
            playlist[index+1] = temp;
            
            const tempOrder = playlist[index].order_index;
            playlist[index].order_index = playlist[index+1].order_index;
            playlist[index+1].order_index = tempOrder;
            
            renderPlaylist();
        }
    };

    window.deleteItem = async (id, filename) => {
        if(confirm('Yakin ingin menghapus media ini?')) {
            const target = filename || id;
            await fetch(`/api/playlist/delete/${encodeURIComponent(target)}`, { method: 'DELETE' });
            showToast('Media berhasil dihapus');
            fetchPlaylist();
        }
    };

    saveBtn.addEventListener('click', async () => {
        saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Menyimpan...';
        
        const rows = playlistBody.querySelectorAll('tr');
        rows.forEach((tr, idx) => {
            if (playlist[idx]) {
                playlist[idx].order_index = idx;
                const durInput = tr.querySelector('input[type="number"]');
                if (durInput && durInput.value) {
                    playlist[idx].duration = parseInt(durInput.value, 10);
                }
                const animSelect = tr.querySelector('select');
                if (animSelect && animSelect.value) {
                    playlist[idx].animation = animSelect.value;
                }
            }
        });

        const res = await fetch('/api/playlist/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(playlist)
        });
        
        if(res.ok) {
            showToast('Perubahan berhasil disimpan!');
            await fetchPlaylist();
        } else {
            showToast('Gagal menyimpan perubahan.');
        }
        saveBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Simpan Perubahan';
    });

    // Upload Logic
    if (uploadArea) {
        uploadArea.addEventListener('click', () => fileInput.click());
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if(e.dataTransfer.files.length) {
                uploadFile(e.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if(e.target.files.length) {
                uploadFile(e.target.files[0]);
            }
        });
    }

    function getMediaType(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const videoExts = ['mp4', 'webm', 'ogg', 'mov', 'avi', 'mkv', 'm4v', '3gp', 'flv', 'wmv', 'ts'];
        return videoExts.includes(ext) ? 'video' : 'image';
    }

    function uploadFile(file) {
        progressDiv.style.display = 'block';
        uploadArea.style.display = 'none';

        if (config.supabase_enabled && config.supabase_url && config.supabase_key) {
            const mediaType = getMediaType(file.name);
            const safeName = file.name.replace(/[^a-zA-Z0-9_.-]/g, '_');
            const filename = `${Math.floor(Date.now() / 1000)}_${safeName}`;
            const bucket = config.supabase_bucket || 'playlist-media';
            const uploadUrl = `${config.supabase_url.replace(/\/$/, '')}/storage/v1/object/${bucket}/${filename}`;
            
            const xhr = new XMLHttpRequest();
            xhr.open('POST', uploadUrl, true);
            xhr.setRequestHeader('Authorization', `Bearer ${config.supabase_key}`);
            xhr.setRequestHeader('apikey', config.supabase_key);
            xhr.setRequestHeader('Content-Type', file.type || (mediaType === 'video' ? 'video/mp4' : 'image/jpeg'));

            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    progressFill.style.width = percent + '%';
                    progressText.innerText = percent + '%';
                }
            };

            xhr.onload = async () => {
                progressDiv.style.display = 'none';
                uploadArea.style.display = 'block';
                progressFill.style.width = '0%';
                fileInput.value = '';

                if (xhr.status === 200 || xhr.status === 201) {
                    const publicUrl = `${config.supabase_url.replace(/\/$/, '')}/storage/v1/object/public/${bucket}/${filename}`;
                    await fetch('/api/media/add', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ filename, type: mediaType, url: publicUrl })
                    });
                    showToast('Upload berhasil!');
                    fetchPlaylist();
                } else {
                    showToast('Upload gagal: ' + xhr.responseText);
                }
            };

            xhr.onerror = () => {
                progressDiv.style.display = 'none';
                uploadArea.style.display = 'block';
                progressFill.style.width = '0%';
                fileInput.value = '';
                showToast('Upload gagal karena koneksi terputus.');
            };

            xhr.send(file);
        } else {
            const formData = new FormData();
            formData.append('file', file);

            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/upload', true);

            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    progressFill.style.width = percent + '%';
                    progressText.innerText = percent + '%';
                }
            };

            xhr.onload = () => {
                progressDiv.style.display = 'none';
                uploadArea.style.display = 'block';
                progressFill.style.width = '0%';
                fileInput.value = '';

                if (xhr.status === 200) {
                    showToast('Upload berhasil!');
                    fetchPlaylist();
                } else {
                    showToast('Upload gagal: ' + xhr.responseText);
                }
            };

            xhr.send(formData);
        }
    }

    function showToast(msg) {
        toast.innerText = msg;
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    // Init
    fetchConfig();
    fetchPlaylist();
});
