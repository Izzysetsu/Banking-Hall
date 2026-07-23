document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const progressDiv = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const playlistBody = document.getElementById('playlist-body');
    const saveBtn = document.getElementById('save-btn');
    const toast = document.getElementById('toast');

    let playlist = [];

    // Fetch and render
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
            
            // swap order_index
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
            
            // swap order_index
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
        
        // update order_index based on current array position before saving
        playlist.forEach((item, idx) => {
            item.order_index = idx;
        });

        const res = await fetch('/api/playlist/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(playlist)
        });
        
        if(res.ok) {
            showToast('Perubahan berhasil disimpan!');
        } else {
            showToast('Gagal menyimpan perubahan.');
        }
        saveBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Simpan Perubahan';
    });

    // Upload Logic
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

    function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        progressDiv.style.display = 'block';
        uploadArea.style.display = 'none';

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
            fileInput.value = ''; // reset

            if (xhr.status === 200) {
                showToast('Upload berhasil!');
                fetchPlaylist();
            } else {
                showToast('Upload gagal: ' + xhr.responseText);
            }
        };

        xhr.send(formData);
    }

    function showToast(msg) {
        toast.innerText = msg;
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    // Init
    fetchPlaylist();
});
