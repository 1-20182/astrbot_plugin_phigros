// 模拟RKS历史数据
const rksHistory = [
  { date: '2024-01-01', rks: 14.5000 },
  { date: '2024-01-02', rks: 14.5500 },
  { date: '2024-01-03', rks: 14.6000 },
  { date: '2024-01-04', rks: 14.6500 },
  { date: '2024-01-05', rks: 14.7000 },
  { date: '2024-01-06', rks: 14.7500 },
  { date: '2024-01-07', rks: 14.8000 },
  { date: '2024-01-08', rks: 14.8500 },
  { date: '2024-01-09', rks: 14.9000 },
  { date: '2024-01-10', rks: 14.9500 },
  { date: '2024-01-11', rks: 15.0000 },
  { date: '2024-01-12', rks: 15.0500 },
  { date: '2024-01-13', rks: 15.1000 },
  { date: '2024-01-14', rks: 15.1500 },
  { date: '2024-01-15', rks: 15.2000 },
  { date: '2024-01-16', rks: 15.1800 },
  { date: '2024-01-17', rks: 15.1500 },
  { date: '2024-01-18', rks: 15.1000 },
  { date: '2024-01-19', rks: 15.0500 },
  { date: '2024-01-20', rks: 15.0000 }
];

// 模拟排行榜数据
const leaderboardData = Array.from({ length: 50 }, (_, index) => ({
  rank: index + 1,
  name: `Player${index + 1}`,
  rks: (16.5 - index * 0.05).toFixed(4),
  avatar: `assets/images/avatar.png`
}));

// 模拟歌曲数据
const songs = [
  {
    id: 1,
    name: "Igallta",
    composer: "Tsukasa",
    difficulties: { ez: 13, hd: 15, in: 16, at: 18 },
    stats: {
      noteCount: 2147,
      bpm: 180,
      duration: "3:45",
      constant: 16.0
    },
    scores: {
      ez: { score: 999999, acc: "99.99%", rank: "S" },
      hd: { score: 999999, acc: "99.99%", rank: "S" },
      in: { score: 999999, acc: "99.99%", rank: "S" },
      at: { score: 999999, acc: "99.99%", rank: "S" }
    },
    illustration: "assets/images/song-placeholder.png"
  },
  {
    id: 2,
    name: "Cthugha",
    composer: "Sakuzyo",
    difficulties: { ez: 12, hd: 14, in: 15, at: 17 },
    stats: {
      noteCount: 1987,
      bpm: 160,
      duration: "3:20",
      constant: 15.0
    },
    scores: {
      ez: { score: 999999, acc: "99.99%", rank: "S" },
      hd: { score: 999999, acc: "99.99%", rank: "S" },
      in: { score: 999999, acc: "99.99%", rank: "S" },
      at: { score: 999999, acc: "99.99%", rank: "S" }
    },
    illustration: "assets/images/song-placeholder.png"
  },
  {
    id: 3,
    name: "Rrhar'il",
    composer: "Team Grimoire",
    difficulties: { ez: 12, hd: 14, in: 16, at: 18 },
    stats: {
      noteCount: 2345,
      bpm: 190,
      duration: "4:10",
      constant: 16.0
    },
    scores: {
      ez: { score: 999999, acc: "99.99%", rank: "S" },
      hd: { score: 999999, acc: "99.99%", rank: "S" },
      in: { score: 999999, acc: "99.99%", rank: "S" },
      at: { score: 999999, acc: "99.99%", rank: "S" }
    },
    illustration: "assets/images/song-placeholder.png"
  },
  {
    id: 4,
    name: "Chronos",
    composer: "Nhato",
    difficulties: { ez: 11, hd: 13, in: 14, at: 16 },
    stats: {
      noteCount: 1765,
      bpm: 150,
      duration: "3:05",
      constant: 14.0
    },
    scores: {
      ez: { score: 999999, acc: "99.99%", rank: "S" },
      hd: { score: 999999, acc: "99.99%", rank: "S" },
      in: { score: 999999, acc: "99.99%", rank: "S" },
      at: { score: 999999, acc: "99.99%", rank: "S" }
    },
    illustration: "assets/images/song-placeholder.png"
  },
  {
    id: 5,
    name: "Glaciaxion",
    composer: "削除",
    difficulties: { ez: 12, hd: 14, in: 15, at: 17 },
    stats: {
      noteCount: 1890,
      bpm: 170,
      duration: "3:30",
      constant: 15.0
    },
    scores: {
      ez: { score: 999999, acc: "99.99%", rank: "S" },
      hd: { score: 999999, acc: "99.99%", rank: "S" },
      in: { score: 999999, acc: "99.99%", rank: "S" },
      at: { score: 999999, acc: "99.99%", rank: "S" }
    },
    illustration: "assets/images/song-placeholder.png"
  }
];

// 移动端菜单切换
const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
const navLinks = document.querySelector('.nav-links');

if (mobileMenuBtn) {
  mobileMenuBtn.addEventListener('click', () => {
    navLinks.classList.toggle('active');
    mobileMenuBtn.classList.toggle('active');
  });
}

// 导航栏滚动效果
window.addEventListener('scroll', () => {
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    if (window.scrollY > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  }
});

// 平滑滚动到锚点
const navLinkItems = document.querySelectorAll('.nav-link');

navLinkItems.forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    
    // 关闭移动端菜单
    if (navLinks.classList.contains('active')) {
      navLinks.classList.remove('active');
    }
    
    const targetId = link.getAttribute('href');
    const targetElement = document.querySelector(targetId);
    
    if (targetElement) {
      targetElement.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
      
      // 更新活动链接状态
      navLinkItems.forEach(item => item.classList.remove('active'));
      link.classList.add('active');
    }
  });
});

// 滚动时更新活动链接
window.addEventListener('scroll', () => {
  const scrollPosition = window.scrollY;
  
  document.querySelectorAll('.section').forEach(section => {
    const sectionTop = section.offsetTop - 100;
    const sectionBottom = sectionTop + section.offsetHeight;
    const sectionId = section.getAttribute('id');
    
    if (scrollPosition >= sectionTop && scrollPosition < sectionBottom) {
      navLinkItems.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === `#${sectionId}`) {
          link.classList.add('active');
        }
      });
    }
  });
});

// 搜索功能
const searchBtn = document.getElementById('searchBtn');
const searchInput = document.getElementById('searchInput');
const searchSuggestions = document.getElementById('searchSuggestions');
const songResults = document.getElementById('songResults');
const songSearchSection = document.getElementById('song-search');
const songDetailsSection = document.getElementById('song-details');
const backBtn = document.getElementById('backBtn');

// 搜索输入事件
if (searchInput) {
  searchInput.addEventListener('input', (e) => {
    const searchTerm = e.target.value.trim().toLowerCase();
    
    if (searchTerm.length > 1) {
      const filteredSongs = songs.filter(song => 
        song.name.toLowerCase().includes(searchTerm) || 
        song.composer.toLowerCase().includes(searchTerm)
      );
      
      if (filteredSongs.length > 0) {
        displaySearchSuggestions(filteredSongs);
      } else {
        hideSearchSuggestions();
      }
    } else {
      hideSearchSuggestions();
    }
  });
  
  // 按回车键搜索
  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      performSearch();
    }
  });
  
  // 点击页面其他地方关闭建议
  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !searchSuggestions.contains(e.target)) {
      hideSearchSuggestions();
    }
  });
}

// 搜索按钮点击事件
if (searchBtn) {
  searchBtn.addEventListener('click', performSearch);
}

// 执行搜索
function performSearch() {
  const searchTerm = searchInput.value.trim().toLowerCase();
  if (searchTerm) {
    const filteredSongs = songs.filter(song => 
      song.name.toLowerCase().includes(searchTerm) || 
      song.composer.toLowerCase().includes(searchTerm)
    );
    
    displaySearchResults(filteredSongs);
    hideSearchSuggestions();
  }
}

// 显示搜索建议
function displaySearchSuggestions(filteredSongs) {
  searchSuggestions.innerHTML = '';
  
  filteredSongs.forEach(song => {
    const suggestionItem = document.createElement('div');
    suggestionItem.className = 'suggestion-item';
    suggestionItem.innerHTML = `
      <div class="song-name">${song.name}</div>
      <div class="song-composer">${song.composer}</div>
    `;
    
    suggestionItem.addEventListener('click', () => {
      searchInput.value = song.name;
      hideSearchSuggestions();
      displaySongDetails(song);
    });
    
    searchSuggestions.appendChild(suggestionItem);
  });
  
  searchSuggestions.classList.add('active');
}

// 隐藏搜索建议
function hideSearchSuggestions() {
  searchSuggestions.classList.remove('active');
}

// 显示搜索结果
function displaySearchResults(filteredSongs) {
  songResults.innerHTML = '';
  
  if (filteredSongs.length === 0) {
    songResults.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">未找到匹配的歌曲</p>';
    return;
  }
  
  filteredSongs.forEach((song, index) => {
    const songCard = document.createElement('div');
    songCard.className = 'song-card';
    songCard.style.animationDelay = `${index * 0.1}s`;
    
    // 找到最高难度
    const maxDiff = Object.entries(song.difficulties).reduce((max, [key, value]) => 
      value > max.value ? { key, value } : max, { key: 'ez', value: 0 }
    );
    
    songCard.innerHTML = `
      <div class="song-illustration">
        <img src="${song.illustration}" alt="${song.name}">
        <div class="diff-badge">${maxDiff.key.toUpperCase()}</div>
      </div>
      <div class="song-info">
        <h3 class="song-name">${song.name}</h3>
        <p class="song-composer">${song.composer}</p>
        <div class="song-stats">
          <span class="diff-ez">EZ: ${song.difficulties.ez}</span>
          <span class="diff-hd">HD: ${song.difficulties.hd}</span>
          <span class="diff-in">IN: ${song.difficulties.in}</span>
          <span class="diff-at">AT: ${song.difficulties.at || '-'}</span>
        </div>
      </div>
      <div class="song-score">
        <p class="score-value">${song.scores[maxDiff.key].score.toLocaleString()}</p>
        <p class="score-acc">${song.scores[maxDiff.key].acc}</p>
      </div>
    `;
    
    songCard.addEventListener('click', () => {
      displaySongDetails(song);
    });
    
    songResults.appendChild(songCard);
  });
}

// 显示歌曲详情
function displaySongDetails(song) {
  // 隐藏搜索部分，显示详情部分
  songSearchSection.style.display = 'none';
  songDetailsSection.style.display = 'block';
  
  // 滚动到详情部分
  songDetailsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  
  // 更新详情内容
  document.getElementById('detailSongName').textContent = song.name;
  document.getElementById('detailComposer').textContent = song.composer;
  document.getElementById('detailIllustration').src = song.illustration;
  
  // 更新难度条
  updateDifficultyBar('ez', song.difficulties.ez);
  updateDifficultyBar('hd', song.difficulties.hd);
  updateDifficultyBar('in', song.difficulties.in);
  if (song.difficulties.at) {
    updateDifficultyBar('at', song.difficulties.at);
  }
  
  // 更新图表常量
  document.getElementById('noteCount').textContent = song.stats.noteCount;
  document.getElementById('bpm').textContent = song.stats.bpm;
  document.getElementById('duration').textContent = song.stats.duration;
  document.getElementById('constant').textContent = song.stats.constant;
  
  // 更新成绩卡片
  const scoreCards = document.querySelectorAll('.score-card');
  scoreCards.forEach((card, index) => {
    const diffs = ['ez', 'hd', 'in', 'at'];
    const diff = diffs[index];
    
    if (song.scores[diff]) {
      card.querySelector('.score-diff').textContent = diff.toUpperCase();
      card.querySelector('.score-number').textContent = song.scores[diff].score.toLocaleString();
      card.querySelector('.score-accuracy').textContent = song.scores[diff].acc;
      card.querySelector('.score-rank').textContent = song.scores[diff].rank;
    }
  });
}

// 更新难度条
function updateDifficultyBar(diff, value) {
  const bar = document.getElementById(`${diff}Bar`);
  const valueElement = document.getElementById(`${diff}Value`);
  
  if (bar && valueElement) {
    const percentage = (value / 20) * 100; // 假设最高难度为20
    bar.style.width = `${percentage}%`;
    bar.className = `diff-bar ${diff}`;
    valueElement.textContent = value;
  }
}

// 返回搜索页面
if (backBtn) {
  backBtn.addEventListener('click', () => {
    songDetailsSection.style.display = 'none';
    songSearchSection.style.display = 'block';
    
    // 滚动到搜索部分
    songSearchSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
}

// 卡片悬停效果
const cards = document.querySelectorAll('.stat-card, .song-card, .update-item, .score-card');

cards.forEach(card => {
  card.addEventListener('mouseenter', () => {
    card.style.transform = 'translateY(-5px)';
    card.style.boxShadow = '0 8px 16px rgba(0, 0, 0, 0.5)';
  });
  
  card.addEventListener('mouseleave', () => {
    card.style.transform = 'translateY(0)';
    card.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.3)';
  });
});

// 初始化图表（如果需要）
function initCharts() {
  const rksChartCanvas = document.getElementById('rksChart');
  if (rksChartCanvas) {
    // 计算峰值RKS和当前RKS
    const peakRks = Math.max(...rksHistory.map(item => item.rks));
    const currentRks = rksHistory[rksHistory.length - 1].rks;
    
    // 更新显示
    document.getElementById('currentRks').textContent = currentRks.toFixed(4);
    document.getElementById('peakRks').textContent = peakRks.toFixed(4);
    
    // 准备图表数据
    const labels = rksHistory.map(item => item.date);
    const data = rksHistory.map(item => item.rks);
    
    // 计算变化值
    const changes = [];
    for (let i = 0; i < rksHistory.length; i++) {
      if (i === 0) {
        changes.push(0);
      } else {
        changes.push((rksHistory[i].rks - rksHistory[i-1].rks).toFixed(4));
      }
    }
    
    // 更新历史列表
    const historyList = document.getElementById('historyList');
    historyList.innerHTML = '';
    
    rksHistory.forEach((item, index) => {
      const historyItem = document.createElement('div');
      historyItem.className = 'history-item';
      historyItem.style.animationDelay = `${index * 0.05}s`;
      
      const changeClass = changes[index] >= 0 ? 'history-jump' : 'history-jump negative';
      const changeSign = changes[index] >= 0 ? '+' : '';
      
      historyItem.innerHTML = `
        <span class="history-date">${item.date}</span>
        <span class="history-rks">${item.rks.toFixed(4)}</span>
        <span class="${changeClass}">${changeSign}${changes[index]}</span>
      `;
      
      historyList.appendChild(historyItem);
    });
    
    // 创建图表
    const ctx = rksChartCanvas.getContext('2d');
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'RKS',
          data: data,
          borderColor: '#00b0f0',
          backgroundColor: 'rgba(0, 176, 240, 0.1)',
          borderWidth: 2,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: '#00b0f0',
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 2000,
          easing: 'easeOutQuart'
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#ffffff',
            bodyColor: '#ffffff',
            borderColor: '#00b0f0',
            borderWidth: 1,
            padding: 12,
            displayColors: false,
            callbacks: {
              label: function(context) {
                return `RKS: ${context.parsed.y.toFixed(4)}`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            },
            ticks: {
              color: '#aaaaaa',
              maxRotation: 45,
              minRotation: 45
            }
          },
          y: {
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            },
            ticks: {
              color: '#aaaaaa'
            },
            min: Math.floor(Math.min(...data) * 10) / 10 - 0.1,
            max: Math.ceil(Math.max(...data) * 10) / 10 + 0.1
          }
        },
        interaction: {
          mode: 'nearest',
          axis: 'x',
          intersect: false
        }
      }
    });
    
    console.log('初始化RKS历史图表完成');
  }
}

// 排行榜相关变量
let currentPage = 1;
const itemsPerPage = 10;

// 初始化排行榜
function initLeaderboard() {
  const leaderboardList = document.getElementById('leaderboardList');
  if (leaderboardList) {
    displayLeaderboardPage(currentPage);
    updatePagination();
    
    // 绑定分页按钮事件
    const prevPageBtn = document.getElementById('prevPage');
    const nextPageBtn = document.getElementById('nextPage');
    
    if (prevPageBtn) {
      prevPageBtn.addEventListener('click', () => {
        if (currentPage > 1) {
          currentPage--;
          displayLeaderboardPage(currentPage);
          updatePagination();
        }
      });
    }
    
    if (nextPageBtn) {
      nextPageBtn.addEventListener('click', () => {
        const totalPages = Math.ceil(leaderboardData.length / itemsPerPage);
        if (currentPage < totalPages) {
          currentPage++;
          displayLeaderboardPage(currentPage);
          updatePagination();
        }
      });
    }
    
    console.log('排行榜初始化完成');
  }
}

// 显示排行榜指定页
function displayLeaderboardPage(page) {
  const leaderboardList = document.getElementById('leaderboardList');
  if (!leaderboardList) return;
  
  leaderboardList.innerHTML = '';
  
  const startIndex = (page - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const pageData = leaderboardData.slice(startIndex, endIndex);
  
  pageData.forEach((player, index) => {
    const leaderboardItem = document.createElement('div');
    leaderboardItem.className = 'leaderboard-item';
    leaderboardItem.style.animationDelay = `${index * 0.1}s`;
    
    leaderboardItem.innerHTML = `
      <span class="rank">${player.rank}</span>
      <span class="player">
        <img src="${player.avatar}" alt="${player.name}" class="player-avatar-small">
        ${player.name}
      </span>
      <span class="score">${player.rks}</span>
    `;
    
    leaderboardList.appendChild(leaderboardItem);
  });
}

// 更新分页控件
function updatePagination() {
  const paginationNumbers = document.getElementById('paginationNumbers');
  const prevPageBtn = document.getElementById('prevPage');
  const nextPageBtn = document.getElementById('nextPage');
  
  if (!paginationNumbers || !prevPageBtn || !nextPageBtn) return;
  
  const totalPages = Math.ceil(leaderboardData.length / itemsPerPage);
  
  // 更新上一页/下一页按钮状态
  prevPageBtn.disabled = currentPage === 1;
  nextPageBtn.disabled = currentPage === totalPages;
  
  // 生成页码按钮
  paginationNumbers.innerHTML = '';
  
  // 显示当前页附近的页码
  const startPage = Math.max(1, currentPage - 2);
  const endPage = Math.min(totalPages, startPage + 4);
  
  for (let i = startPage; i <= endPage; i++) {
    const pageNumber = document.createElement('div');
    pageNumber.className = `pagination-number ${i === currentPage ? 'active' : ''}`;
    pageNumber.textContent = i;
    
    pageNumber.addEventListener('click', () => {
      currentPage = i;
      displayLeaderboardPage(currentPage);
      updatePagination();
    });
    
    paginationNumbers.appendChild(pageNumber);
  }
}

// 页面加载完成后初始化
window.addEventListener('DOMContentLoaded', () => {
  initCharts();
  initLeaderboard();
  console.log('Phigros 插件前端加载完成');
  
  // 初始显示所有歌曲
  displaySearchResults(songs);
});

// 页面滚动动画
function animateOnScroll() {
  const elements = document.querySelectorAll('.section');
  
  elements.forEach(element => {
    const elementTop = element.getBoundingClientRect().top;
    const elementVisible = 150;
    
    if (elementTop < window.innerHeight - elementVisible) {
      element.style.opacity = '1';
      element.style.transform = 'translateY(0)';
    }
  });
}

// 监听滚动事件
window.addEventListener('scroll', animateOnScroll);

// 初始调用一次
animateOnScroll();

// 认证功能
function initAuth() {
  const authTabs = document.querySelectorAll('.auth-tab');
  const authForms = document.querySelectorAll('.auth-form');
  const loginBtn = document.getElementById('login-btn');
  const registerBtn = document.getElementById('register-btn');
  const saveTokenBtn = document.getElementById('save-token-btn');
  const logoutBtn = document.getElementById('logout-btn');
  const authStatus = document.getElementById('auth-status');
  const sessionTokenInput = document.getElementById('session-token');
  const tokenExpiryInput = document.getElementById('token-expiry');
  
  // 标签切换功能
  authTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetTab = tab.getAttribute('data-tab');
      
      // 更新标签状态
      authTabs.forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
      
      // 更新表单显示
      authForms.forEach(form => {
        form.classList.remove('active');
        form.setAttribute('hidden', 'true');
        if (form.classList.contains(`${targetTab}-form`)) {
          form.classList.add('active');
          form.removeAttribute('hidden');
        }
      });
    });
  });
  
  // 登录功能
  if (loginBtn) {
    loginBtn.addEventListener('click', () => {
      const username = document.getElementById('login-username').value;
      const password = document.getElementById('login-password').value;
      
      if (username && password) {
        // 模拟登录成功
        const token = `mock-token-${Date.now()}`;
        const expiry = new Date();
        expiry.setHours(expiry.getHours() + 24); // 24小时过期
        
        // 保存令牌
        saveAuthToken(token, expiry);
        updateAuthStatus(true, username);
        
        // 清空表单
        document.getElementById('login-username').value = '';
        document.getElementById('login-password').value = '';
        
        // 显示成功动画
        showAuthAnimation('登录成功');
      } else {
        showAuthAnimation('请输入用户名和密码', 'error');
      }
    });
  }
  
  // 注册功能
  if (registerBtn) {
    registerBtn.addEventListener('click', () => {
      const username = document.getElementById('register-username').value;
      const password = document.getElementById('register-password').value;
      const confirmPassword = document.getElementById('register-confirm-password').value;
      
      if (username && password && confirmPassword) {
        if (password === confirmPassword) {
          // 模拟注册成功
          const token = `mock-token-${Date.now()}`;
          const expiry = new Date();
          expiry.setHours(expiry.getHours() + 24); // 24小时过期
          
          // 保存令牌
          saveAuthToken(token, expiry);
          updateAuthStatus(true, username);
          
          // 清空表单
          document.getElementById('register-username').value = '';
          document.getElementById('register-password').value = '';
          document.getElementById('register-confirm-password').value = '';
          
          // 显示成功动画
          showAuthAnimation('注册成功');
        } else {
          showAuthAnimation('密码确认不匹配', 'error');
        }
      } else {
        showAuthAnimation('请填写所有字段', 'error');
      }
    });
  }
  
  // 保存令牌功能
  if (saveTokenBtn) {
    saveTokenBtn.addEventListener('click', () => {
      const token = sessionTokenInput.value;
      const expiry = tokenExpiryInput.value;
      
      if (token && expiry) {
        // 保存令牌
        saveAuthToken(token, new Date(expiry));
        updateAuthStatus(true, '用户');
        
        // 清空表单
        sessionTokenInput.value = '';
        tokenExpiryInput.value = '';
        
        // 显示成功动画
        showAuthAnimation('令牌保存成功');
      } else {
        showAuthAnimation('请输入令牌和过期时间', 'error');
      }
    });
  }
  
  // 登出功能
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      // 清除令牌
      clearAuthToken();
      updateAuthStatus(false);
      
      // 显示成功动画
      showAuthAnimation('已退出登录');
    });
  }
  
  // 初始化认证状态
  checkAuthStatus();
}

// 保存认证令牌
function saveAuthToken(token, expiry) {
  try {
    // 使用localStorage存储令牌
    localStorage.setItem('authToken', token);
    localStorage.setItem('tokenExpiry', expiry.toISOString());
  } catch (error) {
    console.error('保存令牌失败:', error);
  }
}

// 清除认证令牌
function clearAuthToken() {
  try {
    localStorage.removeItem('authToken');
    localStorage.removeItem('tokenExpiry');
  } catch (error) {
    console.error('清除令牌失败:', error);
  }
}

// 检查认证状态
function checkAuthStatus() {
  try {
    const token = localStorage.getItem('authToken');
    const expiry = localStorage.getItem('tokenExpiry');
    
    if (token && expiry) {
      const expiryDate = new Date(expiry);
      if (expiryDate > new Date()) {
        updateAuthStatus(true, '用户');
        return true;
      } else {
        // 令牌已过期
        clearAuthToken();
        updateAuthStatus(false);
        return false;
      }
    } else {
      updateAuthStatus(false);
      return false;
    }
  } catch (error) {
    console.error('检查认证状态失败:', error);
    updateAuthStatus(false);
    return false;
  }
}

// 更新认证状态显示
function updateAuthStatus(isLoggedIn, username = '') {
  const authStatus = document.getElementById('auth-status');
  const logoutBtn = document.getElementById('logout-btn');
  
  if (authStatus && logoutBtn) {
    if (isLoggedIn) {
      authStatus.innerHTML = `<p>已登录: ${username}</p>`;
      logoutBtn.style.display = 'block';
      authStatus.appendChild(logoutBtn);
    } else {
      authStatus.innerHTML = '<p>未登录</p>';
      logoutBtn.style.display = 'none';
    }
  }
}

// 显示认证动画
function showAuthAnimation(message, type = 'success') {
  const authContainer = document.querySelector('.auth-container');
  
  if (authContainer) {
    // 创建动画元素
    const animationEl = document.createElement('div');
    animationEl.className = `auth-animation ${type}`;
    animationEl.textContent = message;
    
    // 添加到容器
    authContainer.appendChild(animationEl);
    
    // 显示认证动画
    animationEl.style.webkitAnimation = 'fadeIn 0.3s ease-out forwards';
    animationEl.style.mozAnimation = 'fadeIn 0.3s ease-out forwards';
    animationEl.style.oAnimation = 'fadeIn 0.3s ease-out forwards';
    animationEl.style.animation = 'fadeIn 0.3s ease-out forwards';
    
    // 3秒后移除
    setTimeout(() => {
      animationEl.style.webkitAnimation = 'fadeOut 0.3s ease-in forwards';
      animationEl.style.mozAnimation = 'fadeOut 0.3s ease-in forwards';
      animationEl.style.oAnimation = 'fadeOut 0.3s ease-in forwards';
      animationEl.style.animation = 'fadeOut 0.3s ease-in forwards';
      setTimeout(() => {
        if (authContainer.contains(animationEl)) {
          authContainer.removeChild(animationEl);
        }
      }, 300);
    }, 3000);
  }
}

// 页面加载完成后初始化认证功能
window.addEventListener('DOMContentLoaded', () => {
  initAuth();
  console.log('认证功能初始化完成');
});

// 添加认证动画样式
const style = document.createElement('style');
style.textContent = `
  .auth-animation {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: var(--spacing-md);
    border-radius: var(--border-radius-md);
    color: var(--text-primary);
    font-weight: bold;
    z-index: 1000;
    box-shadow: var(--shadow-lg);
  }
  
  .auth-animation.success {
    background-color: var(--accent-secondary);
  }
  
  .auth-animation.error {
    background-color: var(--accent-danger);
  }
  
  @-webkit-keyframes fadeOut {
    from {
      opacity: 1;
      -webkit-transform: translateY(0);
      transform: translateY(0);
    }
    to {
      opacity: 0;
      -webkit-transform: translateY(-20px);
      transform: translateY(-20px);
    }
  }
  
  @-moz-keyframes fadeOut {
    from {
      opacity: 1;
      -moz-transform: translateY(0);
      transform: translateY(0);
    }
    to {
      opacity: 0;
      -moz-transform: translateY(-20px);
      transform: translateY(-20px);
    }
  }
  
  @-o-keyframes fadeOut {
    from {
      opacity: 1;
      -o-transform: translateY(0);
      transform: translateY(0);
    }
    to {
      opacity: 0;
      -o-transform: translateY(-20px);
      transform: translateY(-20px);
    }
  }
  
  @keyframes fadeOut {
    from {
      opacity: 1;
      -webkit-transform: translateY(0);
      -moz-transform: translateY(0);
      -ms-transform: translateY(0);
      -o-transform: translateY(0);
      transform: translateY(0);
    }
    to {
      opacity: 0;
      -webkit-transform: translateY(-20px);
      -moz-transform: translateY(-20px);
      -ms-transform: translateY(-20px);
      -o-transform: translateY(-20px);
      transform: translateY(-20px);
    }
  }
`;
document.head.appendChild(style);