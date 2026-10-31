import os
import sys
import signal
import requests
from io import BytesIO
from PIL import Image
import colorgram
from appdirs import user_cache_dir

APP_NAME = "spothomelight"
PID_FILE = os.path.join(user_cache_dir(APP_NAME), "spothomelight.pid")

def get_image_color(image_url, proxies=None):
    """提取图片的主色调 RGB。
    
    >>> callable(get_image_color)
    True
    """
    try:
        response = requests.get(image_url, proxies=proxies, timeout=10)
        response.raise_for_status()
        original_image_data = BytesIO(response.content)
        
        with Image.open(original_image_data) as img:
            img = img.convert('RGB')
            img.thumbnail((100, 100))
            
            buffer = BytesIO()
            img.save(buffer, format="JPEG")
            buffer.seek(0)
        
        colors = colorgram.extract(buffer, 1)
        
        if colors:
            rgb = colors[0].rgb
            return (rgb.r, rgb.g, rgb.b)

    except Exception as e:
        print(f"get_image_color Error: {e}")
        return None

def write_pid():
    pid_dir = os.path.dirname(PID_FILE)
    if not os.path.exists(pid_dir):
        os.makedirs(pid_dir)
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

def remove_pid():
    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
        except OSError:
            pass

def check_running():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return pid
        except (OSError, ValueError):
            remove_pid()
    return None

def stop_process():
    pid = check_running()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"已停止进程 PID: {pid}")
            remove_pid()
        except PermissionError:
            print("权限不足，无法停止进程。")
    else:
        print("服务未运行。")
