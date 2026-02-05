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
"""

HA_YAML_TEMPLATE = """
配置完毕后，请配置 Home Assistant 的自动化配置。

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