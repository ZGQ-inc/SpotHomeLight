import os
import sys
import configparser
import subprocess
import platform
from appdirs import user_config_dir

APP_NAME = "spothomelight"
CONFIG_DIR = user_config_dir(APP_NAME)
CONFIG_FILE = os.path.join(CONFIG_DIR, "spothomelight.conf")
TOKEN_FILE = os.path.join(CONFIG_DIR, "token.json")

DEFAULT_CONFIG = """[SPOTIFY]
client_id = 
client_secret = 
redirect_uri = http://127.0.0.1:29092/callback

[HOME_ASSISTANT]
ha_url = http://127.0.0.1:8123
webhook_id = 

[GENERAL]
interval = 5

[DEVICE]
type = rgb
has_motor = false
motor_interval = 5
"""

HA_YAML_TEMPLATE = """
配置完毕后，请将下方配置粘贴到 Home Assistant 的自动化 YAML 编辑器中。

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
"""

def ensure_config():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(DEFAULT_CONFIG)
        print(f"配置文件已生成: {CONFIG_FILE}")

def load_config():
    ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config

def open_config_editor():
    ensure_config()
    
    print(f"\n正在打开配置文件: {CONFIG_FILE}")
    print("请填写 Spotify Client ID/Secret 和 Home Assistant Webhook ID。")
    print(HA_YAML_TEMPLATE)

    system_platform = platform.system()
    
    if system_platform == "Windows":
        try:
            os.startfile(CONFIG_FILE)
        except Exception as e:
            print(f"无法自动打开编辑器: {e}")
            print("请手动打开修改。")
    else:
        editor = os.environ.get('EDITOR')
        if not editor:
            if os.path.exists("/usr/bin/nano"):
                editor = "nano"
            elif os.path.exists("/usr/bin/vi"):
                editor = "vi"
            else:
                print("未找到默认编辑器，请手动编辑。")
                return

        subprocess.call([editor, CONFIG_FILE])