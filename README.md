# 🎮 Phigros Query 插件

> **"你的 RKS 是多少？让我康康！"** 👀

一个超好玩的 **Phigros 音游数据查询插件**！查存档、看排名、搜歌曲、追新曲... 功能多多，快乐加倍！

---

## ✨ 我能干啥？

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

## 📦 怎么装上我？

### 方法一：懒人一键装（推荐⭐）

```bash
cd astrbot_plugin_phigros
python install.py
```
然后躺平等安装完成就行啦~ 😎

### 方法二：手动折腾装

1. 先装依赖：
```bash
pip install -r requirements.txt
```

2. 把整个文件夹丢进 AstrBot 的 `plugins` 目录

3. 重启 AstrBot，搞定！

---

## 📁 我的身体里都有啥？

```
astrbot_plugin_phigros/
├── 📄 main.py                 # 我的大脑（主代码）
├── 📄 utils.py                # 工具箱（公共函数）
├── 📄 config.py               # 配置表（常量定义）
├── 📄 phi_style_renderer.py   # 高级画笔（极速渲染器）
├── 📄 renderer.py             # 旧画笔（备用渲染器）
├── 📄 taptap_login_api.py     # 扫码登录小助手
├── 📄 metadata.yaml           # 我的身份证
├── 📄 requirements.txt        # 我的零食清单（依赖）
├── 📄 _conf_schema.json       # 配置表
├── 📄 install.py              # 自动安装小助手
├── 📄 README.md               # 就是你现在看的这个！
├── 🎨 ILLUSTRATION/           # 曲绘收藏夹
│   ├── 曲名.曲师.png
│   └── ...
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

没有曲师名也可以只写 `曲名.png` 啦~

---

## 🚀 怎么用我？

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
1. 发送命令后，我会给你发一张二维码
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
| `/phi_rks_history` | RKS 历史 | `/phi_rks_history 10` |
| `/phi_leaderboard` | 排行榜（带图） | `/phi_leaderboard` |
| `/phi_rank` | 查排名 | `/phi_rank 1 10` |
| `/phi_search` | 搜歌（带图） | `/phi_search Glaciaxion` |
| `/phi_updates` | 新曲速递 | `/phi_updates 3` |
| `/phi_help` | 喊我帮忙 | `/phi_help` |

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

## 📋 我需要这些才能跑

- Python >= 3.8（太老了不行哦）
- aiohttp >= 3.8.0
- Pillow >= 10.0.0（生成图片用）
- AstrBot（这是必须的啦）

---

## ⚠️ 使用前必看！

1. **曲绘要自己准备！** 我不会自带曲绘哦，请自行放入 `ILLUSTRATION` 文件夹
2. **API Token** - 没填的话会用内置的，但建议自己搞一个更稳定
3. **图片生成** - 需要 Pillow，没装的话只能看文字版（没那么酷）
4. **要联网！** 我要连 Phigros API 才能查数据
5. **绑定账号** - 强烈建议绑定，省得每次都输长长的 token

---

## 🙏 感谢大佬

**特别鸣谢：**

👤 **@Sczr0** - Phigros Query 平台的开发者大佬！没有他就没有我！

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

### v1.9.0 - 极速渲染大升级！🚀

**嗖嗖嗖~ 渲染速度飞起来啦！** ⚡

- 🚀 **多线程并行加载** - 4个线程同时加载30张曲绘，速度提升300%！
- 💾 **智能缓存系统** - 处理好的曲绘都缓存起来，下次用直接拿，超快！
- 🎨 **快速渲染模式** - 简化绘制流程，保留核心效果，渲染时间减半！
- 🖼️ **背景图缓存** - 模糊处理好的背景图直接复用，不用每次都重新搞
- ⚡ **数据提取优化** - 去掉繁琐的日志，代码跑得飞快~
- 🐧 **跨平台优化** - Ubuntu、Debian、CentOS 都能愉快玩耍啦！

### v1.8.0 - 发光大更新！✨

**bling bling 的效果来啦！** 💫

- ✨ **发光文字效果** - 歌曲信息、底部标识都加上了超酷的淡蓝色发光！
- 🎖️ **评级系统** - 自动计算并显示 φ/V/S/A/B/C/F 评级！
  - φ (Phi)：满分 1000000 才能拿到哦～超稀有！
  - V (Full Combo)：FC 玩家的专属徽章，超帅！
- 🎨 **曲绘匹配优化** - 三级匹配策略，再也不怕找不到曲绘啦！
- 🖼️ **背景图支持** - 使用自定义背景，还能模糊+暗化，超有氛围感~

### v1.7.0 - 曲绘自动更新来啦！

**再也不用到处找曲绘了！** 🎨

- ✅ **曲绘自动更新** - 自动从 GitHub 下载最新曲绘
- ✅ **增量更新** - 只下载新文件，超省流量！
- ✅ **代理支持** - 国内也能愉快下载

### v1.6.0 - SVG 转换大升级！
- ✅ **纯 Python SVG 转换器** - 跨平台支持！
- ✅ **本地曲绘自动加载** - 自动匹配并显示本地曲绘
- ✅ **智能字体加载** - 自动检测系统字体

### v1.5.0 - Best30 改用 API SVG！
- ✅ `/phi_b30` 命令改为调用 API 直接生成 SVG

### v1.4.0 - API 文档同步更新！
- ✅ 同步更新 Phigros Query 开放平台 API

### v1.3.0 - Best30 来啦！
- ✅ 新增 Best30 成绩图功能

### v1.2.0 - API 版扫码登录！
- ✅ 使用 Phigros Query API 实现扫码登录

### v1.1.0 - 绑定功能来啦！
- ✅ 新增账号绑定功能

### v1.0.0 - 初次见面！
- ✅ 出生啦！基础功能全都有

---

## 📄 许可证

MIT License - 随便用，但出了问题别找我哦（逃）

---

## 👨‍💻 作者

**飞翔的死猪** - 一只爱打 Phigros 的猪猪 🐷

---

<div align="center">

### 🎵 打歌快乐，RKS 飞涨！🎵

*——来自空间站「塔弦」的 Phigros Query插件*

**Made with ❤️ by 飞翔的死猪**

**[⬆ 回到顶部](#-phigros-query-插件)**

</div>
