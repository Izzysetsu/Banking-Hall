document.addEventListener('DOMContentLoaded', async () => {
    const container = document.getElementById('display-container');
    const loader = document.getElementById('loader');
    
    let playlist = [];
    let currentIndex = 0;
    let currentElement = null;
    let timer = null;

    // Fetch playlist from server
    async function fetchPlaylist() {
        try {
            const res = await fetch('/api/playlist');
            playlist = await res.json();
            if (playlist.length > 0) {
                loader.style.display = 'none';
                playCurrent();
            } else {
                loader.innerHTML = '<p>Tidak ada media dalam playlist.</p>';
            }
        } catch (err) {
            console.error('Error fetching playlist:', err);
            loader.innerHTML = '<p>Koneksi error. Mencoba lagi...</p>';
            setTimeout(fetchPlaylist, 5000);
        }
    }

    function createMediaElement(item) {
        let el;
        const mediaSrc = item.url ? item.url : '/static/uploads/' + item.filename;
        if (item.type === 'video') {
            el = document.createElement('video');
            el.src = mediaSrc;
            el.autoplay = true;
            el.muted = true; // Often required for autoplay
            el.loop = false;
        } else {
            el = document.createElement('img');
            el.src = mediaSrc;
        }
        el.className = `media-item anim-${item.animation}`;
        return el;
    }

    function playCurrent() {
        if (playlist.length === 0) return;
        
        // Loop back to start
        if (currentIndex >= playlist.length) {
            currentIndex = 0;
            // Optionally re-fetch playlist here to get updates dynamically
            fetchPlaylist();
            return;
        }

        const item = playlist[currentIndex];
        const el = createMediaElement(item);
        container.appendChild(el);
        
        // Trigger reflow to ensure animation runs
        void el.offsetWidth;
        el.classList.add('active');
        
        if (currentElement) {
            // Apply out-animation to previous element
            const oldEl = currentElement;
            const oldAnim = oldEl.className.match(/anim-([a-zA-Z]+)/)[1];
            oldEl.classList.remove('active');
            oldEl.classList.add(`out-${oldAnim}`);
            
            // Remove old element after transition (1s)
            setTimeout(() => {
                if (oldEl.parentNode) oldEl.parentNode.removeChild(oldEl);
            }, 1000);
        }
        
        currentElement = el;

        // Determine how long to wait before next slide
        let parsedDuration = parseInt(item.duration, 10);
        let durationMs = (!isNaN(parsedDuration) && parsedDuration > 0 ? parsedDuration : 10) * 1000;
        
        if (item.type === 'video') {
            // Tunggu sampai video benar-benar selesai
            el.addEventListener('ended', () => {
                clearTimeout(timer);
                nextSlide();
            });
            // Jika video error/gagal dimuat, lewati slide setelah 3 detik
            el.addEventListener('error', () => {
                clearTimeout(timer);
                setTimeout(nextSlide, 3000);
            });
            // Fallback maksimal 15 menit agar layar tidak freeze selamanya
            timer = setTimeout(() => {
                nextSlide();
            }, 15 * 60 * 1000); 
        } else {
            timer = setTimeout(() => {
                nextSlide();
            }, durationMs);
        }
    }

    function nextSlide() {
        currentIndex++;
        playCurrent();
    }

    // Start
    fetchPlaylist();
});
