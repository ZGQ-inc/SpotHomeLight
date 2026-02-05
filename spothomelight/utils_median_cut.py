import os
import sys
import signal
import requests
from io import BytesIO
from PIL import Image
from appdirs import user_cache_dir

APP_NAME = "spothomelight"
PID_FILE = os.path.join(user_cache_dir(APP_NAME), "spothomelight.pid")

def get_image_color(image_url):
    try:
        response = requests.get(image_url, timeout=10)
        image_data = BytesIO(response.content)
        
        with Image.open(image_data) as img:
            img = img.convert('RGB')
            
            img.thumbnail((100, 100))
            
            p_img = img.quantize(colors=5, method=0)
            
            dominant_color = sorted(p_img.getcolors(maxcolors=10), key=lambda x: x[0], reverse=True)[0]
            
            palette = p_img.getpalette()
            color_index = dominant_color[1]
            
            r = palette[color_index * 3]
            g = palette[color_index * 3 + 1]
            b = palette[color_index * 3 + 2]
            
            return (r, g, b)

    except Exception as e:
        print(f"取色失败: {e}")
        return None

def write_pid():
    pid_dir = os.path.dirname(PID_FILE)
    if not os.path.exists(pid_dir):
        os.makedirs(pid_dir)
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

def check_running():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return pid
        except (OSError, ValueError):
            os.remove(PID_FILE)
    return None

def stop_process():
    pid = check_running()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"已停止进程 PID: {pid}")
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except PermissionError:
            print("权限不足，无法停止进程。")
    else:
        print("服务未运行。")