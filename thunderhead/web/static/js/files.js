(function() {
    let currentPath = "/";
    let token = sessionStorage.getItem("token");

    if (!token && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
        return;
    }

    function apiHeaders() {
        return { "Authorization": "Bearer " + token };
    }

    async function api(path, options = {}) {
        if (!options.headers) options.headers = {};
        options.headers = { ...apiHeaders(), ...options.headers };

        const res = await fetch(path, options);
        if (res.status === 401) {
            sessionStorage.removeItem("token");
            window.location.href = "/login";
            return null;
        }
        return res;
    }

    function formatSize(bytes) {
        if (bytes === 0) return "-";
        const units = ["B", "KB", "MB", "GB"];
        let i = Math.floor(Math.log(bytes) / Math.log(1024));
        if (i >= units.length) i = units.length - 1;
        return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + " " + units[i];
    }

    function formatDate(ts) {
        const d = new Date(ts * 1000);
        return d.toLocaleDateString("en-US", {
            year: "numeric", month: "short", day: "numeric",
            hour: "2-digit", minute: "2-digit"
        });
    }

    function updateBreadcrumb() {
        const bc = document.getElementById("breadcrumb");
        bc.innerHTML = "";
        const parts = currentPath.replace(/\/$/, "").split("/").filter(Boolean);
        let accum = "";

        const rootLink = document.createElement("a");
        rootLink.dataset.path = "/";
        rootLink.textContent = "/";
        bc.appendChild(rootLink);

        for (const part of parts) {
            accum += "/" + part;
            const link = document.createElement("a");
            link.dataset.path = accum;
            link.textContent = part;
            bc.appendChild(link);
        }
    }

    async function loadFiles(path) {
        const tbody = document.getElementById("file-list");
        tbody.innerHTML = '<tr><td colspan="4" class="loading">Loading...</td></tr>';
        currentPath = path;
        updateBreadcrumb();

        const res = await api("/api/fs/list?path=" + encodeURIComponent(path));
        if (!res) return;

        const data = await res.json();
        tbody.innerHTML = "";

        if (currentPath !== "/") {
            const parent = currentPath.replace(/\/[^/]*$/, "") || "/";
            const row = document.createElement("tr");
            row.innerHTML = `
                <td><span class="file-icon">📁</span><a class="dir-link" data-path="${parent}">..</a></td>
                <td>-</td>
                <td>-</td>
                <td></td>
            `;
            tbody.appendChild(row);
        }

        for (const item of data.items) {
            const row = document.createElement("tr");
            const icon = item.is_dir ? "📁" : getFileIcon(item.name);
            const nameHtml = item.is_dir
                ? `<a class="dir-link" data-path="${item.path}">${item.name}</a>`
                : `<a class="file-link" data-path="${item.path}">${item.name}</a>`;

            row.innerHTML = `
                <td><span class="file-icon">${icon}</span>${nameHtml}</td>
                <td>${item.is_dir ? "-" : formatSize(item.size)}</td>
                <td>${formatDate(item.modified)}</td>
                <td><button class="action-btn" data-path="${item.path}" ${item.is_dir ? 'data-type="dir"' : 'data-type="file"'}>✕</button></td>
            `;

            const dirLink = row.querySelector(".dir-link");
            if (dirLink) {
                dirLink.addEventListener("click", (e) => {
                    e.preventDefault();
                    loadFiles(dirLink.dataset.path);
                });
            }

            const fileLink = row.querySelector(".file-link");
            if (fileLink) {
                fileLink.addEventListener("click", (e) => {
                    e.preventDefault();
                    downloadFile(fileLink.dataset.path);
                });
            }

            const delBtn = row.querySelector(".action-btn");
            delBtn.addEventListener("click", () => {
                const type = delBtn.dataset.type;
                const name = type === "dir" ? "directory" : "file";
                showConfirm(`Delete ${name}?`, `Are you sure you want to delete "${delBtn.dataset.path}"?`, () => {
                    deleteItem(delBtn.dataset.path);
                });
            });

            tbody.appendChild(row);
        }
    }

    function getFileIcon(name) {
        const ext = name.split(".").pop()?.toLowerCase();
        const types = {
            txt: "📄", md: "📄", json: "📄", yml: "📄", yaml: "📄",
            py: "🐍", js: "📜", ts: "📜", html: "🌐", css: "🎨",
            jpg: "🖼", jpeg: "🖼", png: "🖼", gif: "🖼", svg: "🖼", webp: "🖼",
            mp3: "🎵", wav: "🎵", flac: "🎵",
            mp4: "🎬", mov: "🎬", avi: "🎬",
            zip: "📦", tar: "📦", gz: "📦", rar: "📦",
            pdf: "📕",
            exe: "⚙️", dll: "⚙️",
        };
        return types[ext] || "📄";
    }

    async function downloadFile(path) {
        const res = await api("/api/fs/download?path=" + encodeURIComponent(path));
        if (!res) return;

        const blob = await res.blob();
        const name = path.split("/").pop();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = name;
        a.click();
        window.URL.revokeObjectURL(url);
    }

    async function deleteItem(path) {
        const res = await api("/api/fs/remove?path=" + encodeURIComponent(path), { method: "DELETE" });
        if (res && res.ok) {
            loadFiles(currentPath);
        }
    }

    async function newFolder(name) {
        const path = (currentPath === "/" ? "" : currentPath) + "/" + name;
        const res = await api("/api/fs/mkdir?path=" + encodeURIComponent(path), { method: "POST" });
        if (res && res.ok) {
            loadFiles(currentPath);
        }
    }

    async function uploadFile(file) {
        const formData = new FormData();
        formData.append("file", file);

        const bar = document.getElementById("progress-bar");
        const text = document.getElementById("progress-text");
        const progress = document.getElementById("upload-progress");
        progress.classList.remove("hidden");

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/fs/upload?path=" + encodeURIComponent(currentPath));
        xhr.setRequestHeader("Authorization", "Bearer " + token);

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const pct = Math.round((e.loaded / e.total) * 100);
                bar.style.width = pct + "%";
                text.textContent = `Uploading ${file.name}... ${pct}%`;
            }
        };

        xhr.onload = () => {
            progress.classList.add("hidden");
            bar.style.width = "0%";
            if (xhr.status === 200) {
                loadFiles(currentPath);
            }
        };

        xhr.onerror = () => {
            progress.classList.add("hidden");
            bar.style.width = "0%";
            text.textContent = "Upload failed";
        };

        xhr.send(formData);
    }

    function showConfirm(title, message, onConfirm) {
        const overlay = document.getElementById("modal-overlay");
        document.getElementById("modal-title").textContent = title;
        const body = document.getElementById("modal-body");
        body.innerHTML = `<p>${message}</p>`;
        overlay.classList.remove("hidden");

        const confirmBtn = document.getElementById("modal-confirm");
        const cancelBtn = document.getElementById("modal-cancel");

        const cleanup = () => {
            overlay.classList.add("hidden");
            confirmBtn.removeEventListener("click", handleConfirm);
            cancelBtn.removeEventListener("click", cleanup);
        };

        const handleConfirm = () => {
            cleanup();
            onConfirm();
        };

        confirmBtn.addEventListener("click", handleConfirm);
        cancelBtn.addEventListener("click", cleanup);
    }

    function showFolderPrompt() {
        const overlay = document.getElementById("modal-overlay");
        document.getElementById("modal-title").textContent = "New Folder";
        const body = document.getElementById("modal-body");
        body.innerHTML = `<input type="text" id="folder-name" placeholder="Folder name" autofocus>`;
        overlay.classList.remove("hidden");

        const confirmBtn = document.getElementById("modal-confirm");
        const cancelBtn = document.getElementById("modal-cancel");
        confirmBtn.textContent = "Create";

        const cleanup = () => {
            overlay.classList.add("hidden");
            confirmBtn.removeEventListener("click", handleCreate);
            cancelBtn.removeEventListener("click", cleanup);
            confirmBtn.textContent = "Confirm";
        };

        const handleCreate = () => {
            const name = document.getElementById("folder-name")?.value;
            if (name) {
                newFolder(name);
            }
            cleanup();
        };

        const input = document.getElementById("folder-name");
        input?.addEventListener("keydown", (e) => {
            if (e.key === "Enter") handleCreate();
            if (e.key === "Escape") cleanup();
        });

        setTimeout(() => input?.focus(), 100);
        confirmBtn.addEventListener("click", handleCreate);
        cancelBtn.addEventListener("click", cleanup);
    }

    document.addEventListener("DOMContentLoaded", () => {
        const fileList = document.getElementById("file-list");
        if (!fileList) return;

        loadFiles("/");

        document.getElementById("new-folder-btn")?.addEventListener("click", showFolderPrompt);

        document.getElementById("file-input")?.addEventListener("change", (e) => {
            for (const file of e.target.files) {
                uploadFile(file);
            }
            e.target.value = "";
        });

        // drag and drop
        const dropZone = document.getElementById("drop-zone");

        document.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropZone.classList.remove("hidden");
            dropZone.classList.add("drag-over");
        });

        document.addEventListener("dragleave", (e) => {
            if (!e.relatedTarget || !document.body.contains(e.relatedTarget)) {
                dropZone.classList.add("hidden");
                dropZone.classList.remove("drag-over");
            }
        });

        document.addEventListener("drop", (e) => {
            e.preventDefault();
            dropZone.classList.add("hidden");
            dropZone.classList.remove("drag-over");
            for (const file of e.dataTransfer.files) {
                uploadFile(file);
            }
        });

        // breadcrumb clicks
        document.getElementById("breadcrumb")?.addEventListener("click", (e) => {
            const link = e.target.closest("a");
            if (link && link.dataset.path) {
                e.preventDefault();
                loadFiles(link.dataset.path);
            }
        });
    });
})();
