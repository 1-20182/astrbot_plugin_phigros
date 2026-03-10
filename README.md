# 🎮 Phigros Query 插件

> **"你的 RKS 是多少？让本猪康康！"** 👀

一只超可爱的 **Phigros 音游数据查询插件**来啦！查存档、看排名、搜歌曲、追新曲... 功能多多，快乐加倍！✨

---

## ✨ 本猪能干啥？

| 功能 | 说明 |
|------|------|
| 📊 **偷看存档** | 一键获取你的游戏数据（还带美美的曲绘哦~） |
| 📈 **RKS 追踪** | 看看你的 RKS 是涨了还是跌了（希望是涨了🙏） |
| 🏆 **围观大佬** | 查看全服排行榜，膜拜大神 |
| 🔍 **搜歌神器** | 想听啥歌？搜一下就出来！ |
| 🆕 **新曲速递** | 第一时间知道鸽游又更新了啥 |
| 🎨 **美图生成** | 自动生成带曲绘的漂亮图片，发朋友圈必备！ |
| 🔗 **账号绑定** | 绑定一次，永久免输 token！ |
| 📱 **扫码登录** | TapTap 扫码一键登录，超方便！ |
| 🎯 **Best30** | 生成 Best30 成绩图（极速渲染，带发光效果！）✨ |
| 🎯 **BestN** | 生成 BestN 成绩图，自定义数量（API直接生成SVG） |
| 🎵 **单曲成绩** | 生成指定歌曲的成绩图（API直接生成SVG） |

---

## 📦 怎么把本猪带回家？

### ✅ 跨平台支持

**不管你是 Windows 党、Ubuntu 党还是 macOS 党，本猪都能陪你玩！** 🎉

| 系统 | 支持状态 | 安装方式 |
|------|---------|---------|
| 🪟 **Windows** | ✅ 完美支持 | 方法一 |
| 🐧 **Ubuntu/Linux** | ✅ 完美支持 | 方法二 |
| 🍎 **macOS** | ✅ 支持 | 方法一 |

> 💡 **小提示**：不管你用啥系统，扫码登录功能都能正常使用啦！二维码再也不会迷路了~ 🥳

---

### 方法一：懒人一键装（推荐⭐）

**适用于：Windows / macOS / Linux**

```bash
cd astrbot_plugin_phigros
python install.py
```
然后躺平等安装完成就行啦~ 😎

### 方法二：Ubuntu/Linux 安装（推荐⭐）

专为 Ubuntu/Linux 系统优化的安装方式：

```bash
cd astrbot_plugin_phigros

# 方式1：使用安装脚本（推荐）
chmod +x install.sh
./install.sh

# 方式2：不使用虚拟环境（如果方式1遇到问题）
./install.sh --no-venv
```

**脚本会自动完成：**
- ✅ 创建 Python 虚拟环境（隔离依赖）
- ✅ 安装系统依赖（Pillow 所需的图像库）
- ✅ 安装 Python 依赖
- ✅ 创建必要的目录
- ✅ 检查中文字体
- ✅ 设置文件权限

**安装后管理：**
```bash
# 检查环境
./manage.sh check

# 测试二维码功能
./manage.sh test-qr

# 更新依赖
./manage.sh update

# 清理缓存
./manage.sh clean

# 修复权限
./manage.sh fix-permissions
```

---

### 方法三：手动折腾装

1. 先装依赖：
```bash
pip install -r requirements.txt
```

2. 把整个文件夹丢进 AstrBot 的 `plugins` 目录

3. 重启 AstrBot，搞定！

---

## 📦 轻量版本下载（国内用户福音！）

**国内访问 GitHub 网速太慢？别担心！** 🎉

为了解决国内小伙伴下载慢的问题，本猪准备了轻量版本的资源包！

### 下载步骤：
1. 点击链接下载资源包：[https://www.123865.com/s/42S9vd-iMmtv](https://www.123865.com/s/42S9vd-iMmtv)
2. 解压资源包，把里面的文件放到插件目录
3. 完成！现在插件就能正常运行啦~ 🌟

### 为什么要下载资源包？
- 🚀 **下载更快** - 国内云盘速度杠杠的，不用再等半天
- 📦 **轻量便携** - 插件本体很小，资源包单独下载
- 💾 **节省空间** - 只下载你需要的资源

> 💡 **小提示**：如果遇到资源包解压问题，记得检查文件完整性哦！

---

## 📁 本猪的身体里都有啥？

```
astrbot_plugin_phigros/
├── 📄 main.py                 # 本猪的大脑（主代码）
├── 📄 config.py               # 配置表（常量定义）
├── 📄 illustration_updater.py # 曲绘自动更新小助手
├── 📄 image_generator.py      # 图片生成器
├── 📄 phi_style_renderer.py   # 高级画笔（极速渲染器）
├── 📄 renderer.py             # 旧画笔（备用渲染器）
├── 📄 metadata.yaml           # 本猪的身份证
├── 📄 requirements.txt        # 本猪的零食清单（依赖）
├── 📄 _conf_schema.json       # 配置表
├── 📄 install.py              # 自动安装小助手
├── 📄 install.sh              # Ubuntu 安装脚本
├── 📄 manage.sh               # 管理脚本
├── 📄 README.md               # 就是你现在看的这个！
├── 📄 CHANGELOG.md            # 更新日记
├── 📄 Dockerfile              # Docker 配置
├── 📄 docker-compose.yml      # Docker Compose 配置
├── 🎨 ILLUSTRATION/           # 曲绘收藏夹
│   ├── 曲名.曲师.png
│   └── ...
├── 🎨 AVATAR/                 # 头像收藏夹
├── 🎬 VideoClip/              # 视频片段收藏夹
├── 📂 core/                   # 核心模块
│   ├── 📄 __init__.py
│   ├── 📄 api_client.py       # API 客户端（带重试、限流、连接池）
│   ├── 📄 cache_manager.py    # 缓存管理器（三级缓存）
│   ├── 📄 exceptions.py       # 自定义异常类
│   ├── 📄 monitoring.py       # API 监控器
│   └── 📄 thread_pool.py      # 线程池工具（异步化同步 IO）
├── 📂 commands/               # 命令模块
│   ├── 📄 __init__.py
│   ├── 📄 auth_commands.py    # 认证相关命令
│   ├── 📄 query_commands.py   # 查询相关命令
│   └── 📄 other_commands.py   # 其他命令
├── 📂 auth/                   # 认证模块
│   └── 📄 __init__.py
├── 📂 render/                 # 渲染模块
│   └── 📄 __init__.py
├── 📂 resources/              # 资源宝库
│   ├── 📂 data/               # 歌曲数据
│   │   ├── info.csv           # 歌曲基础信息
│   │   ├── difficulty.csv     # 定数表
│   │   └── nicklist.yaml      # 昵称对照
│   ├── 📂 font/               # 字体文件
│   └── 📂 img/                # 图片资源
│       ├── 📂 rating/         # 评级图标
│       ├── 📂 logo/           # Logo图标
│       └── 📂 other/          # 其他图标
└── 📂 output/                 # 作品展示墙
    ├── 📄 user_data.json      # 用户绑定数据
    └── 📂 cache/              # 临时小仓库
```

---

## 🎨 曲绘怎么放？

把曲绘图片丢进 `ILLUSTRATION` 文件夹，命名要乖一点：

**推荐格式：** `曲名.曲师.png`

**举栗子🌰：**
- `Glaciaxion.SunsetRay.png`
- `MARENOL.LeaF.png`
- `Rrharil.TeamGrimoire.png`

没有曲师名也可以只写 `曲名.png` 啦~ 本猪不挑食！

---

## 🚀 怎么和本猪玩？

### 📱 扫码登录（超方便！推荐⭐）

**最简单的方式**，直接用 TapTap APP 扫码：

```
/phi_qrlogin [taptapVersion]
```

**举个栗子：**
- `/phi_qrlogin` - 默认国服
- `/phi_qrlogin cn` - 国服
- `/phi_qrlogin global` - 国际服

**流程：**
1. 发送命令后，本猪会给你发一张二维码
2. 用 TapTap APP 扫码
3. 在手机上确认登录
4. 自动获取 token 并绑定，搞定！

---

### 🔗 手动绑定（备用方案）

如果你不想扫码，也可以手动绑定：

```
/phi_bind <sessionToken> [taptapVersion]
```

**举个栗子：**
- `/phi_bind abc123def456 cn` - 绑定国服账号
- `/phi_bind xyz789uvw012 global` - 绑定国际服账号

**sessionToken 从哪搞？**
1. 访问 https://lilith.xtower.site/
2. 用 TapTap 扫码登录
3. 按 F12 打开开发者工具
4. 在 Console 输入：`localStorage.getItem('sessionToken')`
5. 复制返回的那串字符

**解绑账号：**
```
/phi_unbind
```

---

### 📋 指令大全

| 指令 | 干啥的 | 举个栗子 |
|------|--------|---------|
| `/phi_qrlogin` | 扫码登录⭐ | `/phi_qrlogin cn` |
| `/phi_bind` | 手动绑定 | `/phi_bind your_token cn` |
| `/phi_unbind` | 解绑账号 | `/phi_unbind` |
| `/phi_b30` | Best30 成绩图（极速渲染！）⭐ | `/phi_b30` |
| `/phi_bn` | BestN 成绩图（API SVG） | `/phi_bn 27 black` |
| `/phi_song` | 单曲成绩图 | `/phi_song 曲名.曲师` |
| `/phi_save` | 查存档（带美图） | `/phi_save` |
| `/phi_rks_history` | RKS 历史（带趋势图！）⭐ | `/phi_rks_history 10` |
| `/phi_leaderboard` | 排行榜（带图） | `/phi_leaderboard` |
| `/phi_rank` | 查排名 | `/phi_rank 1 10` |
| `/phi_search` | 搜歌（带图） | `/phi_search Glaciaxion` |
| `/phi_updates` | 新曲速递 | `/phi_updates 3` |
| `/phi_help` | 喊本猪帮忙 | `/phi_help` |
| `/phi_video` | 随机视频 | `/phi_video` |
| `/phi_video_list` | 视频列表 | `/phi_video_list` |
| `/phi_update_illust` | 手动更新曲绘 | `/phi_update_illust` |
| `/phi_metrics` | 查看 API 监控指标 | `/phi_metrics` |

### 💡 使用小技巧

- **扫码登录最方便**，不用到处找 token！
- **绑定后**直接用 `/phi_b30` 生成 Best30 成绩图，嗖嗖快！⚡
- **没绑定**也可以临时查询：`/phi_b30 your_token cn`
- `taptapVersion` 选 `cn` (国服) 或 `global` (国际版)

---

## ⚙️ 配置小天地

在 AstrBot WebUI 里点点点就能配置啦：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `phigros_api_token` | 字符串 | 空 | API 令牌（没有也能用默认的） |
| `enable_renderer` | 开关 | 开✅ | 要不要生成漂亮图片 |
| `illustration_path` | 字符串 | ./ILLUSTRATION | 曲绘放哪 |
| `image_quality` | 数字 | 95 | 图片质量（1-100，越高越清晰） |
| `default_taptap_version` | 字符串 | cn | 默认查国服 |
| `default_search_limit` | 数字 | 5 | 搜歌默认显示几条 |
| `default_history_limit` | 数字 | 10 | RKS历史默认显示几条 |
| `enable_auto_update_illustration` | 开关 | 关❌ | 自动更新曲绘 |
| `illustration_update_proxy` | 字符串 | 空 | 代理地址 |

---

## 📋 本猪需要这些才能跑

- Python >= 3.8（太老了本猪跑不动哦）
- aiohttp >= 3.8.0
- Pillow >= 10.0.0（生成图片用）
- AstrBot（这是必须的啦）

---

## ⚠️ 使用前必看！

1. **曲绘要自己准备！** 本猪不会自带曲绘哦，请自行放入 `ILLUSTRATION` 文件夹
2. **API Token** - 没填的话会用内置的，但建议自己搞一个更稳定
3. **图片生成** - 需要 Pillow，没装的话只能看文字版（没那么酷）
4. **要联网！** 本猪要连 Phigros API 才能查数据
5. **绑定账号** - 强烈建议绑定，省得每次都输长长的 token

---

## 🙏 感谢大佬

**特别鸣谢：**

👤 **@Sczr0** - Phigros Query 平台的开发者大佬！没有他就没有本猪！

**资源文件来源：**
- 歌曲数据、字体、图标等资源来自 [phi-plugin](https://github.com/Catrong/phi-plugin)

---

## 🔗 有用的链接

| 项目 | 链接 |
|------|------|
| 🌐 **Phigros Query 官网** | https://lilith.xtower.site/ |
| 👨‍💻 **Phigros Query GitHub** | https://github.com/Sczr0 |
| 🎮 **phi-plugin** | https://github.com/Catrong/phi-plugin |
| 🎨 **Phigros 曲绘仓库** | https://github.com/NanLiang-Works-Inc/Phigros_Resource |

---

## 📝 更新日记

### v2.0.0 - 架构大重构！稳定又高效！🚀✨

**哇塞！本猪焕然一新啦！** 🎉

这次本猪进行了全面的架构重构，解决了之前提到的所有技术痛点！代码更清晰、性能更强、稳定性更好！

**这次重构了什么？**

#### 🎯 P0 优先级改进（必须立即修复的）：
- ✅ **连接池和限流机制** - 使用 TCPConnector 连接池 + RateLimiter 令牌桶算法，再也不怕 API 被 ban 啦！
- ✅ **真正的错误恢复** - 新增 `@retry` 装饰器，网络波动时自动重试 3 次，指数退避，超智能！
- ✅ **同步阻塞修复** - 使用 ThreadPoolManager 线程池，将 PIL 图片操作和文件 IO 全部异步化，事件循环再也不卡啦！
- ✅ **缓存淘汰策略** - LRUCache + DiskCache + HybridCache 三级缓存，内存磁盘双重保障，性能杠杠的！

#### 🏗️ 架构层面改进：
- ✅ **模块化目录结构** - 新增 core/、render/、auth/ 目录，代码结构更清晰！
- ✅ **自定义异常类** - PhigrosAPIError、RenderError、CacheError、AuthError、ValidationError、NetworkError、RateLimitError，错误处理更精准！
- ✅ **API 客户端独立** - PhigrosAPIClient 封装所有 API 调用，带重试、限流、连接池！
- ✅ **缓存管理器** - LRUCache（内存）+ DiskCache（磁盘）+ HybridCache（混合），三级缓存！
- ✅ **线程池工具** - ThreadPoolManager 单例，asyncify、pil_async、file_async 装饰器！
- ✅ **监控系统** - APIMonitor 统计 API 调用成功率、耗时等指标，支持 `/phi_metrics` 命令查看！

#### 📦 新增模块：
- `core/exceptions.py` - 自定义异常类
- `core/api_client.py` - API 客户端（带重试、限流、连接池）
- `core/cache_manager.py` - 缓存管理器（LRU + Disk + Hybrid）
- `core/thread_pool.py` - 线程池工具（异步化同步 IO）
- `core/monitoring.py` - API 监控器
- `commands/auth_commands.py` - 认证相关命令
- `commands/query_commands.py` - 查询相关命令
- `commands/other_commands.py` - 其他命令

> 💖 **使用小贴士**：现在本猪更稳定、更快速啦！所有 P0 优先级的问题都解决了喵！后续本猪会继续优化其他功能~ ヽ(✿ﾟ▽ﾟ)ノ

### v1.9.6 - 轻量版本来啦！🚀✨

**国内用户福音！下载速度飞起来啦！** 🎉

为了解决国内小伙伴访问 GitHub 网速慢的问题，本猪推出了轻量版本的插件！

**这次更新了什么？**

- 📦 **轻量版本** - 插件本体更小，资源包单独下载
- 🚀 **国内云盘下载** - 提供 123 云盘下载链接，速度杠杠的！
- 📄 **文档更新** - README 新增轻量版本下载指南
- 🌟 **使用更方便** - 解压资源包到插件目录即可使用

**下载链接：** [https://www.123865.com/s/42S9vd-iMmtv](https://www.123865.com/s/42S9vd-iMmtv)

> 💖 **使用小贴士**：国内用户建议使用轻量版本，下载更快更稳定！

---

## 📄 许可证

MIT License - 随便用，但出了问题别找本猪哦（逃）

---

## 👨‍💻 作者

**飞翔的死猪** - 一只爱打 Phigros 的猪猪 🐷

---

<div align="center">

### 🎵 打歌快乐，RKS 飞涨！🎵

*——来自空间站「塔弦」的 Phigros Query 插件*

**Made with ❤️ by 飞翔的死猪**

**[⬆ 回到顶部](#-phigros-query-插件)**

</div>