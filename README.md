# SpotHomeLight 🎵🏠💡

**SpotHomeLight** 是一个轻量级的 Python 服务，用于将 Spotify 当前播放封面的主色调、音乐能量及 BPM 同步到 Home Assistant。

它运行在你的家用服务器（Linux 或 Windows）上，通过提取封面颜色，并通过 Spotify 音频特征分析（Audio Features）提取动态节奏，通过 Webhook 实时推送到 Home Assistant，让你的智能灯光和电机跟随音乐氛围律动。

## ✨ 功能特性

* **双模式运行**：
  * **官方 Web API 模式 (`mode = official`)**：适合 Spotify Premium 会员用户，拥有极低延迟，支持曲目封面、能量（Energy）与转速（BPM）完整联动。
  * **免凭证桥接模式 (`mode = bridge`)**：适合所有普通用户（**无需开发者账号、免 API 凭证、免费账号亦可**），只需填写 UID 即可同步封面颜色！
* **跨平台支持**：完美支持 Linux (Systemd) 和 Windows (计划任务)。
* **多设备支持**：支持普通 RGB、RGBW（动态亮度映射）以及 RGB-CCT（动态色温映射）氛围灯。
* **无头与一键授权**：专为无显示器的家用服务器设计，本地支持回调服务器自动获取 Token，同时支持终端内手动完成 OAuth。
* **智能取色**：提取封面最主要颜色，并进行缩略图预处理以降低 CPU 占用。
* **物理转速同步**：抓取 Spotify 曲目 BPM (Tempo)，可映射至本地电机/风扇设备，且支持独立周期的脉冲更新。
* **开机自启**：内置一键配置开机自动运行。
* **低资源占用**：去重机制，仅在切歌时进行下载和计算。

## 🛠️ 前置要求

1. **Home Assistant**: 一个运行中的 HA 实例。
2. **Spotify 账号**: 
   - 使用 **官方模式** 需要 Spotify Premium 会员并创建开发者 App。
   - 使用 **免凭证模式** 仅需普通 Spotify 账号即可。

## 📦 安装

使用 pip 安装：

```bash
pip install spothomelight
```

## 🚀 快速开始

### 选择工作模式与配置

运行以下命令打开配置文件：

```bash
spothomelight -c
```

配置文件说明：

```ini
[SPOTIFY]
# 运行模式: official (官方模式，需 Premium) 或 bridge (免凭证模式，免费账号可用)
mode = bridge

# 【模式一：免凭证桥接模式 (bridge)】 
# 适合没有 Premium 会员或不想申请开发者凭证的用户。
# 1. 访问 https://spotify-github-profile.kittinanx.com 点击登录授权
# 2. 授权后页面会显示您的 UID ，将其填入下方即可：
uid = your_spotify_uid

# 【模式二：官方 Web API 模式 (official)】 
# 适合拥有 Spotify Premium 会员的用户，支持获取 Energy、Valence 及 BPM。
# 登录 https://developer.spotify.com/dashboard 创建 App：
# 重定向 URI 设置为: http://127.0.0.1:29092/callback
client_id = 你的 Client ID
client_secret = 你的 Client Secret
redirect_uri = http://127.0.0.1:29092/callback

[HOME_ASSISTANT]
ha_url = http://192.168.1.100:8123
webhook_id = 从 Home Assistant 获取的 Webhook ID

[GENERAL]
interval = 5
# proxy = http://127.0.0.1:7890 (可选，网络需要代理时配置)

[DEVICE]
type = rgb
has_motor = false
motor_interval = 5
```

> **设备类型说明：**
> * **type=rgb**: 提取封面颜色。
> * **type=rgbw**: 读取 `energy` (0.0-1.0)，高能量音乐灯光更亮，轻音乐更柔和。（官方模式支持）
> * **type=rgb_cct**: 除上述外还会读取 `valence` (0.0-1.0)，正向情绪数值可映射为暖色温。（官方模式支持）

### 配置 Home Assistant

登录 Home Assistant 后台，进入「设置」->「自动化与场景」->「创建自动化」->「创建新的自动化」，右上角三点菜单选择「以 YAML 编辑」，将下面的内容粘贴进去并保存：

```yaml
alias: Spotify Cover Sync
description: "根据 Spotify 状态联动灯光亮度及电机转速"
mode: restart

triggers:
  - webhook_id: "填入你的 Webhook ID"
    local_only: false
    trigger: webhook
    allowed_methods:
      - POST
      - PUT

conditions:
  - condition: state
    entity_id: binary_sensor.your_occupancy_sensor  # 替换为你的人在传感器
    state:
      - "on"

actions:
  - if:
      - condition: template
        value_template: "{{ trigger.json.state == 'playing' }}"
    then:
      - action: light.turn_on
        target:
          entity_id:
            - light.your_rgbw_light         # 替换为你的主灯/氛围灯实体
            - light.your_atmosphere_light   # 替换为你的水波纹/极光灯实体
        data:
          transition: 2
          rgb_color: "{{ trigger.json.rgb }}"
          brightness_pct: "{{ (trigger.json.energy * 100) | int if trigger.json.energy is defined else 100 }}"

  - if:
      - condition: template
        value_template: "{{ trigger.json.state in ['playing', 'motor_update'] and trigger.json.tempo is defined }}"
    then:
      - action: fan.set_percentage
        target:
          entity_id:
            - fan.your_motor_entity         # 替换为你的极光灯/水波纹灯电机实体
        data:
          percentage: >
            {% set bpm = trigger.json.tempo | float %}
            {% set pct = (bpm / 1.8) | int %}
            {{ [10, [100, pct] | min] | max }}
```

### 首次运行与服务启动

在终端中前台运行测试：

```bash
spothomelight
```

* **免凭证模式 (`bridge`)**：直接开始监控同步，无需任何登录步骤！
* **官方模式 (`official`)**：首次运行会打印授权 URL 或自动弹出浏览器，完成授权后即可。如需单独登录可执行 `spothomelight -l`。

### 设置开机自启

确认运行正常后，按 `Ctrl+C` 退出测试，然后运行：

```bash
spothomelight -a
```

* **Linux**: 自动创建并启用 Systemd 服务。
* **Windows**: 自动创建 Windows 计划任务。

控制后台服务：

```bash
spothomelight --start   # 启动服务
spothomelight --stop    # 停止服务
```

## 💖 特别鸣谢 (Credits)

本项目免凭证桥接功能由以下开源项目提供的公共服务支持，特此向原作者致谢：
* **[kittinan/spotify-github-profile](https://github.com/kittinan/spotify-github-profile)** - 由 [@kittinan](https://github.com/kittinan) 开发并维护的优秀 Spotify 动态卡片服务（首选源）。
* **[JeffreyCA/spotify-recently-played-readme](https://github.com/JeffreyCA/spotify-recently-played-readme)** - 由 [@JeffreyCA](https://github.com/JeffreyCA) 开发并维护的高可用 Spotify 播放记录服务（热备源）。

当首选源遇到上游服务波动或切歌间隙 500 异常时，SpotHomeLight 会自动无缝切换至备用源，确保灯光同步 24/7 不间断。

## 🐛 已知问题

* **取色结果与客户端不一致**: 
  由于 Spotify 官方客户端的动态取色算法并未公开且涉及专属的饱和度平衡筛选，本工具计算出的主色调可能与你在客户端界面上看到的背景色略有差异。

## 📝 License

MIT License. Copyright (c) 2026 ZGQ Inc.
