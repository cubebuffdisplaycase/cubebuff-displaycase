# CubeBuff Bluesky 每日定时外链发帖机器人 (GitHub Actions 版)

基于 GitHub Actions 搭建的 CubeBuff 自动化外链发布系统。每天北京时间早上 06:00 自动运行，向 Bluesky 发布 20 篇带有精准锚文本和独立内页深层链接的优质帖子，无需本地电脑开机。

---

## 🌟 核心特性
- ☁️ **云端托管**：利用 GitHub Actions 免费运行，电脑关机也能准时发布。
- 🔗 **全站深层内页轮替**：对接 CubeBuff 官方 Sitemaps（57+ 个 Collections 与 Products），禁止单一首页引用。
- 🎯 **精准锚文本外链**：采用 AT Protocol Rich Text Facets，关键词点击直达对应产品页。
- 🖼️ **动态图文卡片**：自动抓取各产品专属实物展盒高清图上传为预览卡片。
- 🧠 **发帖历史记忆**：自动记录 `posted_history.json` 并回写仓库，确保每日 20 个产品均匀轮替不重复。

---

## 🚀 3 步部署到 GitHub

### 第一步：在 GitHub 上新建仓库
1. 打开 [GitHub 新建仓库页面](https://github.com/new)。
2. 仓库名填入：`cubebuff-bluesky-poster`。
3. 推荐勾选 **Private（私有仓库）** 保护业务数据。
4. 点击 **Create repository**。

### 第二步：配置 GitHub Secrets（账号密码）
进入刚建好的仓库页面：
1. 点击 **Settings** ➔ 侧边栏选择 **Secrets and variables** ➔ 点击 **Actions**。
2. 点击绿色的 **New repository secret** 按钮，分别添加以下两个变量：
   - 变量 1：
     - Name: `BLUESKY_HANDLE`
     - Secret: `info@cubebuff.com`
   - 变量 2：
     - Name: `BLUESKY_PASSWORD`
     - Secret: `你的16位应用密码` (如 `etku-db6m-dexn-6gcs`)

3. **开启写权限（重要）**：
   在 **Settings** ➔ **Actions** ➔ **General** 下拉到最底部 **Workflow permissions**，选择 **Read and write permissions**，点击 **Save**（这样 Actions 每天发完帖才能自动保存已发历史记录）。

### 第三步：推送代码到 GitHub
在 Mac 终端中，直接运行以下命令推送到您的仓库：

```bash
cd /Users/haixin/.gemini/antigravity/scratch/bsky_poster

git init -b main
git add .
git commit -m "feat: init cubebuff bluesky daily poster"
git remote add origin https://github.com/你的GitHub用户名/cubebuff-bluesky-poster.git
git push -u origin main
```

---

## 🧪 手动测试运行
推送成功后：
1. 进入 GitHub 仓库页面的 **Actions** 标签。
2. 在左侧点击 **Daily Bluesky Poster for CubeBuff**。
3. 点击右侧 **Run workflow** ➔ 点击绿色的 **Run workflow** 按钮。
4. 即可查看实时的运行日志和生成的帖子链接！
