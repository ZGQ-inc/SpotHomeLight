# SpotHomeLight 🎵🏠💡

**SpotHomeLight** 是一个轻量级的 Python 服务，用于将 Spotify 当前播放封面的主色调同步到 Home Assistant。

它运行在你的家用服务器（Linux 或 Windows）上，通过 K-Means 聚类算法提取封面颜色，并通过 Webhook 实时推送到 Home Assistant，让你的智能灯光跟随音乐氛围律动。

## ✨ 功能特性

* **跨平台支持**：完美支持 Linux (Systemd) 和 Windows (计划任务)。
* **无头模式设计**：专为无显示器的家用服务器设计，支持终端内完成 OAuth 认证。
* **智能取色**：使用 K-Means 聚类算法提取最主要颜色，并进行缩略图预处理以降低 CPU 占用。
* **开机自启**：内置一键配置开机自动运行 (`-a`)。
* **低资源占用**：去重机制，仅在切歌时进行下载和计算。

## 🛠️ 前置要求

1.  **Home Assistant**: 一个运行中的 HA 实例。
2.  **Spotify 开发者账号**: 用于获取 API 凭证。

## 📦 安装

使用 pip 安装：

```bash
pip install spothomelight
```

## 🚀 快速开始

### 准备 Spotify API

1. 登录 [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).
2. 创建一个新的 App (例如命名为 `SpotHomeLight`)。
3. 将 Redirect URI 设置为：

```
[http://127.0.0.1:29092/callback](http://127.0.0.1:29092/callback)
```

4. 记下 **Client ID** 和 **Client Secret**。

### 初始化配置

运行以下命令打开配置文件：

```bash
spothomelight -c
```

conf描述：

```ini
[SPOTIFY]
client_id = Client ID
client_secret = Client Secret
redirect_uri = 重定向URI（一般不需要修改，除非你知道自己在干什么。）

[HOME_ASSISTANT]
ha_url =  Home Assistant 地址（局域网/广域网）
webhook_id = 从 Home Assistant 获取的 Webhook ID

[GENERAL]
interval = 循环周期（秒）
```

### 配置 Home Assistant

登录 Home Assistant 后台，设置，自动化与场景，创建自动化，创建新的自动化，右上角三点菜单，YAML 编辑，将下面的yaml粘贴进去，保存。

右上角三点菜单，可视化编辑，复制 每当 里面的 Webhook ID，注意不要点复制按钮，那会复制API地址，需要选中输入框的内容并复制。

就执行 的实体删除pending，添加目标，选择自己的RGB灯，保存。

```yaml
alias: Spotify Cover Sync
description: ""
mode: restart
trigger:
  - platform: webhook
    webhook_id: ""
    local_only: true
condition: []
action:
  - service: light.turn_on
    target:
      entity_id: light.pending
    data:
      rgb_color: "{{ trigger.json.rgb }}"
      brightness_pct: 100
      transition: 2
```

### 首次运行与认证

在终端运行：

```bash
spothomelight
```

考虑到服务器通常没有浏览器，程序会打印一个认证 URL。

1. 复制该 URL 到你电脑的浏览器中打开。
2. 登录并点击“同意”。
3. 浏览器会跳转到一个 `127.0.0.1` 的无法连接页面。
4. 复制浏览器地址栏中完整的 URL。
5. 回到服务器终端，粘贴 URL 并回车。

认证成功后，程序应该开始监控并在终端输出日志，观察输出是否正常。

### 第五步：设置开机自启

确认运行正常后，Ctrl+C 停止程序，然后运行：

```bash
spothomelight -a
```

* **Linux**: 会自动创建并启用 Systemd User Service。
* **Windows**: 会自动创建 Windows 计划任务（登录时运行）。

停止服务：

```bash
spothomelight -s
```

## 📝 License

MIT License. Copyright (c) 2026 ZGQ Inc.
