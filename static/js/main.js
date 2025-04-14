document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const connectButton = document.getElementById("connect-button")
    const webdavUrl = document.getElementById("webdav-url")
    const webdavUsername = document.getElementById("webdav-username")
    const webdavPassword = document.getElementById("webdav-password")
    const connectionStatus = document.getElementById("connection-status")
    const connectionForm = document.getElementById("connection-form")
    const appContainer = document.getElementById("app-container")
    const fileBrowser = document.getElementById("file-browser")
    const fileList = document.getElementById("file-list")
    const videoPlayer = document.getElementById("video-player")
    const player = document.getElementById("player")
    const currentVideo = document.getElementById("current-video")
    const currentPath = document.getElementById("current-path")
    const breadcrumbs = document.getElementById("breadcrumbs")
    const usernameDisplay = document.getElementById("username-display")
    const logoutButton = document.getElementById("logout-button")
    const searchInput = document.getElementById("search-input")
    const searchButton = document.getElementById("search-button")
    const refreshButton = document.getElementById("refresh-button")
    const createPlaylistButton = document.getElementById("create-playlist-button")
    const listViewButton = document.getElementById("list-view-button")
    const gridViewButton = document.getElementById("grid-view-button")
    const minimizePlayerButton = document.getElementById("minimize-player")
    const maximizePlayerButton = document.getElementById("maximize-player")
    const speedSelector = document.getElementById("speed-selector")
    const pipButton = document.getElementById("pip-button")
    const playlistPanel = document.getElementById("playlist-panel")
    const playlistItems = document.getElementById("playlist-items")
    const playAllButton = document.getElementById("play-all-button")
    const shuffleButton = document.getElementById("shuffle-button")
    const closePlaylistButton = document.getElementById("close-playlist")
    const playlistCount = document.getElementById("playlist-count")
    const loadingIndicator = document.getElementById("loading-indicator")
    const themeToggleBtn = document.getElementById("theme-toggle-btn")
    const toastContainer = document.getElementById("toast-container")
  
    // State
    let currentBrowsePath = "/"
    let pathHistory = [{ path: "/", name: "Root" }]
    let currentPlaylist = []
    let currentPlaylistIndex = -1
    let isAuthenticated = false
    let isDarkMode = localStorage.getItem("darkMode") === "true"
  
    // Initialize
    init()
  
    // Event Listeners
    connectButton.addEventListener("click", connectToWebDAV)
    logoutButton.addEventListener("click", logout)
    searchButton.addEventListener("click", () => searchFiles(searchInput.value))
    searchInput.addEventListener("keyup", (e) => {
      if (e.key === "Enter") {
        searchFiles(searchInput.value)
      }
    })
    refreshButton.addEventListener("click", () => browseDirectory(currentBrowsePath))
    createPlaylistButton.addEventListener("click", createPlaylist)
    listViewButton.addEventListener("click", () => setViewMode("list"))
    gridViewButton.addEventListener("click", () => setViewMode("grid"))
    minimizePlayerButton.addEventListener("click", minimizePlayer)
    maximizePlayerButton.addEventListener("click", maximizePlayer)
    speedSelector.addEventListener("change", () => {
      player.playbackRate = Number.parseFloat(speedSelector.value)
    })
    pipButton.addEventListener("click", togglePictureInPicture)
    playAllButton.addEventListener("click", playAllVideos)
    shuffleButton.addEventListener("click", shufflePlaylist)
    closePlaylistButton.addEventListener("click", () => {
      playlistPanel.classList.add("hidden")
    })
    player.addEventListener("ended", playNextVideo)
    themeToggleBtn.addEventListener("click", toggleDarkMode)

    // 添加清除缓存功能
    document.getElementById('clear-cache-btn').addEventListener('click', function() {
        if (confirm('确定要清除路径缓存吗？这将重置所有目录和文件的编号。')) {
            fetch('/api/clear_cache', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('缓存已清除，页面将刷新');
                    location.reload();
                } else {
                    alert('清除缓存失败: ' + (data.message || '未知错误'));
                }
            })
            .catch(error => {
                alert('清除缓存出错: ' + error);
            });
        }
    });
  
    // Functions
    function init() {
      // Check if dark mode is enabled
      if (isDarkMode) {
        document.body.classList.add("dark-mode")
        themeToggleBtn.innerHTML = '<i class="fas fa-sun"></i>'
      }
  
      // Check authentication status
      checkAuthStatus()
        .then((status) => {
          if (status.authenticated) {
            isAuthenticated = true
            showAuthenticatedUI(status.username)
            browseDirectory("/")
          }
        })
        .catch((error) => {
          console.error("Error checking auth status:", error)
        })
  
      // Load view mode preference
      const viewMode = localStorage.getItem("viewMode") || "list"
      setViewMode(viewMode, false)
    }
  
    function checkAuthStatus() {
      return fetch("/api/status")
        .then((response) => response.json())
        .then((data) => {
          return data
        })
    }
  
    function connectToWebDAV() {
      const url = webdavUrl.value.trim()
      const username = webdavUsername.value.trim()
      const password = webdavPassword.value.trim()
  
      if (!url) {
        showStatus("Please enter WebDAV URL", "error")
        return
      }
  
      showStatus("Connecting...", "info")
      showLoading(true)
  
      fetch("/api/connect", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: url,
          username: username,
          password: password,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          showLoading(false)
          if (data.success) {
            showStatus(data.message, "success")
            showToast("Connected successfully", "success")
            isAuthenticated = true
            showAuthenticatedUI(data.username)
            browseDirectory("/")
          } else {
            showStatus(data.message, "error")
            showToast("Connection failed", "error")
          }
        })
        .catch((error) => {
          showLoading(false)
          showStatus(`Error: ${error.message}`, "error")
          showToast("Connection error", "error")
        })
    }
  
    function logout() {
      fetch("/api/logout", {
        method: "POST",
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            isAuthenticated = false
            showToast("Logged out successfully", "success")
            showLoginUI()
          }
        })
        .catch((error) => {
          console.error("Logout error:", error)
          showToast("Logout failed", "error")
        })
    }
  
    function showAuthenticatedUI(username) {
      connectionForm.classList.add("hidden")
      appContainer.classList.remove("hidden")
      usernameDisplay.textContent = username || "User"
    }
  
    function showLoginUI() {
      connectionForm.classList.remove("hidden")
      appContainer.classList.add("hidden")
      videoPlayer.classList.add("hidden")
      playlistPanel.classList.add("hidden")
      player.pause()
      player.src = ""
      currentPlaylist = []
      currentPlaylistIndex = -1
    }
  
    function browseDirectory(path) {
      clearError();
      showLoading(true);
      currentBrowsePath = path;
      
      fetch(`/api/browse?path=${encodeURIComponent(path)}`)
          .then(response => response.json())
          .then(data => {
              showLoading(false);
              if (data.success) {
                  displayFileList(data.items);
                  currentPath.innerText = path.startsWith('dir_') 
                      ? `目录 ID: ${path}` 
                      : path;
                  
                  // 更新面包屑
                  updateBreadcrumbs();
              } else {
                  showError(data.message || 'Failed to browse directory');
              }
          })
          .catch(error => {
              showLoading(false);
              showError('Error browsing directory: ' + error);
          });
    }
  
    function searchFiles(query) {
      if (!query.trim()) {
        browseDirectory(currentBrowsePath)
        return
      }
      browseDirectory(currentBrowsePath, query.trim())
    }
  
    function displayFileList(items) {
      fileList.innerHTML = ""
    
      // Sort items: directories first, then files
      items.sort((a, b) => {
        if (a.isDir && !b.isDir) return -1
        if (!a.isDir && b.isDir) return 1
        return a.displayName.localeCompare(b.displayName)
      })
    
      if (items.length === 0) {
        const emptyMessage = document.createElement("div")
        emptyMessage.className = "empty-message"
        emptyMessage.textContent = "No files found"
        fileList.appendChild(emptyMessage)
        return
      }
    
      items.forEach((item) => {
        const itemElement = document.createElement("div")
        itemElement.className = `file-item ${item.isDir ? "directory" : ""}`
    
        // Determine if it's a video file
        const isVideo =
          !item.isDir &&
          (item.contentType.startsWith("video/") ||
            [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".3gp"].some((ext) =>
              item.displayName.toLowerCase().endsWith(ext),
            ))
    
        if (isVideo) {
          itemElement.classList.add("video")
        }
    
        // Create icon
        const iconElement = document.createElement("span")
        iconElement.className = "file-icon"
    
        if (item.isDir) {
          iconElement.innerHTML = '<i class="fas fa-folder"></i>'
        } else if (isVideo) {
          iconElement.innerHTML = '<i class="fas fa-film"></i>'
        } else {
          iconElement.innerHTML = '<i class="fas fa-file"></i>'
        }
    
        itemElement.appendChild(iconElement)
    
        // Create text
        const textElement = document.createElement("span")
        textElement.className = "file-name"
        textElement.textContent = item.displayName
        itemElement.appendChild(textElement)
    
        // Add details for files
        if (!item.isDir) {
          const detailsElement = document.createElement("div")
          detailsElement.className = "file-details"
    
          const sizeElement = document.createElement("span")
          sizeElement.textContent = formatFileSize(item.size)
          detailsElement.appendChild(sizeElement)
    
          if (item.lastModified) {
            const dateElement = document.createElement("span")
            dateElement.textContent = formatDate(item.lastModified)
            detailsElement.appendChild(dateElement)
          }
    
          itemElement.appendChild(detailsElement)
        }
    
        // 添加ID显示
        if (item.id) {
          const idBadge = document.createElement("span")
          idBadge.className = "id-badge"
          idBadge.textContent = item.id
          itemElement.appendChild(idBadge)
        }
    
        // Add click event
        itemElement.addEventListener("click", () => {
          handleFileClick(item)
        })
    
        fileList.appendChild(itemElement)
      })
    }
  
    function handleFileClick(item) {
      if (item.isDir) {
        // 目录导航，使用目录ID
        browseDirectory(item.webdavPath)
      } else if (isVideoFile(item.displayName)) {
        // 使用ID播放视频
        playVideo(item.webdavPath, item.displayName)
      } else {
        alert('Non-video files cannot be previewed')
      }
    }
  
    function isVideoFile(filename) {
      const videoExtensions = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".3gp"]
      return videoExtensions.some(ext => filename.toLowerCase().endsWith(ext))
    }
  
    function playVideo(path, displayName) {
      // 确保视频播放器可见
      videoPlayer.classList.remove("hidden");
      currentVideo.innerHTML = displayName;
      
      // 设置视频源
      player.src = `/api/stream?path=${encodeURIComponent(path)}`;
      player.load();
      player.play();
      
      // 加载视频元数据
      fetch(`/api/metadata?path=${encodeURIComponent(path)}`)
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            // 可以使用元数据增强播放体验
            console.log('Video metadata:', data.metadata);
          }
        })
        .catch(error => {
          console.error('Error fetching metadata:', error);
        });
        
      // 记录当前播放的视频，方便播放列表功能使用
      if (!currentPlaylist.find(item => item.webdavPath === path)) {
        currentPlaylistIndex = -1; // 重置播放列表索引，因为我们在播放列表外的视频
      }
    }
  
    function createPlaylist() {
      showLoading(true);
      fetch(`/api/playlist?path=${encodeURIComponent(currentBrowsePath)}&recursive=true`)
        .then(response => response.json())
        .then(data => {
          showLoading(false);
          if (data.success) {
            if (data.items.length === 0) {
              showToast("No video files found in this directory", "info");
              return;
            }
            
            currentPlaylist = data.items;
            currentPlaylistIndex = -1;
            displayPlaylist();
            playlistPanel.classList.remove("hidden");
            playlistCount.textContent = `${data.items.length} videos`;
            showToast(`Created playlist with ${data.items.length} videos`, "success");
          } else {
            showToast(data.message, "error");
          }
        })
        .catch(error => {
          showLoading(false);
          showToast(`Error creating playlist: ${error.message}`, "error");
        });
    }
  
    function clearError() {
      const errorEl = document.getElementById('error-message');
      if (errorEl) {
        errorEl.style.display = 'none';
      }
    }
  
    function showError(message) {
      let errorEl = document.getElementById('error-message');
      if (!errorEl) {
        errorEl = document.createElement('div');
        errorEl.id = 'error-message';
        errorEl.className = 'error-message';
        document.querySelector('#file-browser').prepend(errorEl);
      }
      
      errorEl.textContent = message;
      errorEl.style.display = 'block';
    }
  
    function updateBreadcrumbs() {
      breadcrumbs.innerHTML = ""
      pathHistory.forEach((item, index) => {
        const crumb = document.createElement("span")
        crumb.className = "breadcrumb"
        if (index === 0) {
          crumb.innerHTML = '<i class="fas fa-home"></i> Root'
        } else {
          crumb.textContent = item.name
        }
  
        crumb.dataset.path = item.path
        crumb.addEventListener("click", () => {
          // Navigate to this path
          pathHistory = pathHistory.slice(0, index + 1)
          browseDirectory(item.path)
        })
        breadcrumbs.appendChild(crumb)
      })
    }

    // 添加缺失的 setViewMode 函数
    function setViewMode(mode, savePreference = true) {
      if (mode === "list") {
        fileList.className = "list-view";
        listViewButton.classList.add("active");
        gridViewButton.classList.remove("active");
      } else {
        fileList.className = "grid-view";
        gridViewButton.classList.add("active");
        listViewButton.classList.remove("active");
      }
    
      if (savePreference) {
        localStorage.setItem("viewMode", mode);
      }
    }

    // 添加丢失的函数

    // 视频播放器控制函数
    function minimizePlayer() {
      if (window.innerWidth >= 992) {
        // 在桌面端，只是缩小播放器
        player.style.maxHeight = "300px";
      } else {
        // 在移动端，隐藏播放器区域
        videoPlayer.classList.add("hidden");
      }
    }
    
    function maximizePlayer() {
      player.style.maxHeight = "none";
      videoPlayer.classList.remove("hidden");
    }
    
    // 显示状态消息
    function showStatus(message, type) {
      connectionStatus.textContent = message;
      connectionStatus.className = "status";
      if (type) {
        connectionStatus.classList.add(type);
      }
    }
    
    // 显示/隐藏加载指示器
    function showLoading(show) {
      if (show) {
        loadingIndicator.classList.remove("hidden");
      } else {
        loadingIndicator.classList.add("hidden");
      }
    }
    
    // 由于缺失的函数可能还有其他，添加一个更全面的通用函数集
    function showToast(message, type = "info") {
      const toast = document.createElement("div");
      toast.className = `toast toast-${type}`;
    
      const messageSpan = document.createElement("span");
      messageSpan.textContent = message;
      toast.appendChild(messageSpan);
    
      const closeButton = document.createElement("button");
      closeButton.className = "toast-close";
      closeButton.innerHTML = "&times;";
      closeButton.addEventListener("click", () => {
        toast.remove();
      });
      toast.appendChild(closeButton);
    
      toastContainer.appendChild(toast);
    
      // 3秒后自动移除提示
      setTimeout(() => {
        toast.remove();
      }, 3000);
    }
    
    // 格式化文件大小的辅助函数
    function formatFileSize(bytes) {
      if (bytes === 0) return "0 Bytes";
      const k = 1024;
      const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
    }
    
    // 格式化日期的辅助函数
    function formatDate(dateString) {
      try {
        const date = new Date(dateString);
        return date.toLocaleDateString();
      } catch (e) {
        return dateString;
      }
    }
    
    // 处理播放列表相关函数
    function displayPlaylist() {
      playlistItems.innerHTML = "";
    
      currentPlaylist.forEach((item, index) => {
        const playlistItem = document.createElement("div");
        playlistItem.className = "playlist-item";
        if (index === currentPlaylistIndex) {
          playlistItem.classList.add("active");
        }
    
        const numberElement = document.createElement("span");
        numberElement.className = "playlist-item-number";
        numberElement.textContent = (index + 1).toString().padStart(2, "0");
        playlistItem.appendChild(numberElement);
    
        const nameElement = document.createElement("span");
        nameElement.className = "playlist-item-name";
        nameElement.textContent = item.displayName;
        playlistItem.appendChild(nameElement);
    
        const actionsElement = document.createElement("div");
        actionsElement.className = "playlist-item-actions";
    
        const playButton = document.createElement("button");
        playButton.innerHTML = '<i class="fas fa-play"></i>';
        playButton.title = "Play";
        playButton.addEventListener("click", (e) => {
          e.stopPropagation();
          playPlaylistItem(index);
        });
        actionsElement.appendChild(playButton);
    
        playlistItem.appendChild(actionsElement);
    
        playlistItem.addEventListener("click", () => {
          playPlaylistItem(index);
        });
    
        playlistItems.appendChild(playlistItem);
      });
    }
    
    function playPlaylistItem(index) {
      if (index < 0 || index >= currentPlaylist.length) return;
    
      currentPlaylistIndex = index;
      const item = currentPlaylist[index];
      playVideo(item.webdavPath, item.displayName);
    
      // 更新播放列表项的活跃状态
      const playlistItemElements = playlistItems.querySelectorAll(".playlist-item");
      playlistItemElements.forEach((el, i) => {
        if (i === index) {
          el.classList.add("active");
        } else {
          el.classList.remove("active");
        }
      });
    }
    
    function playNextVideo() {
      if (currentPlaylist.length === 0 || currentPlaylistIndex === -1) return;
      const nextIndex = (currentPlaylistIndex + 1) % currentPlaylist.length;
      playPlaylistItem(nextIndex);
    }
    
    function playPreviousVideo() {
      if (currentPlaylist.length === 0 || currentPlaylistIndex === -1) return;
      const prevIndex = (currentPlaylistIndex - 1 + currentPlaylist.length) % currentPlaylist.length;
      playPlaylistItem(prevIndex);
    }
    
    function playAllVideos() {
      if (currentPlaylist.length === 0) return;
      playPlaylistItem(0);
    }
    
    function shufflePlaylist() {
      if (currentPlaylist.length <= 1) return;
    
      // Fisher-Yates 洗牌算法
      for (let i = currentPlaylist.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [currentPlaylist[i], currentPlaylist[j]] = [currentPlaylist[j], currentPlaylist[i]];
      }
    
      currentPlaylistIndex = -1;
      displayPlaylist();
      showToast("播放列表已随机排序", "info");
    }
    
    async function togglePictureInPicture() {
      try {
        if (document.pictureInPictureElement) {
          await document.exitPictureInPicture();
        } else if (document.pictureInPictureEnabled) {
          await player.requestPictureInPicture();
        }
      } catch (error) {
        console.error("Picture-in-Picture error:", error);
        showToast("画中画模式不受支持", "error");
      }
    }

    // 添加缺失的 toggleDarkMode 函数
    function toggleDarkMode() {
      isDarkMode = !isDarkMode;
      document.body.classList.toggle("dark-mode", isDarkMode);
      localStorage.setItem("darkMode", isDarkMode);
      
      if (isDarkMode) {
        themeToggleBtn.innerHTML = '<i class="fas fa-sun"></i>';
      } else {
        themeToggleBtn.innerHTML = '<i class="fas fa-moon"></i>';
      }
    }
  })