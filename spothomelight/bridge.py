"""
SpotHomeLight - Bridge Mode (免凭证桥接模式)

特别鸣谢 / Credits:
本模块免凭证桥接功能基于开源项目 kittinan/spotify-github-profile
(https://github.com/kittinan/spotify-github-profile) 提供的公共服务支持，特此致谢！
Special thanks to kittinan for providing the public Spotify profile SVG service.
"""

import re
import html
import base64
import requests
from io import BytesIO
from PIL import Image
import colorgram

KITTINAN_VIEW_URL = "https://spotify-github-profile.kittinanx.com/api/view"

def fetch_bridge_playback(uid, proxies=None):
    """通过 kittinan/spotify-github-profile 接口获取当前播放信息并提取封面主色调。
    
    特别鸣谢: 基于 kittinan/spotify-github-profile 开源公共服务。
    
    >>> callable(fetch_bridge_playback)
    True
    """
    if not uid:
        return None

    params = {
        "uid": uid,
        "cover_image": "true",
        "show_offline": "true"
    }

    headers = {
        "User-Agent": "SpotHomeLight/1.2.0 (HomeAssistant Sync)"
    }

    try:
        resp = requests.get(KITTINAN_VIEW_URL, params=params, headers=headers, proxies=proxies, timeout=10)
        resp.raise_for_status()
        svg = resp.text

        # 检查是否处于离线或未播放状态
        song_match = re.search(r'<div class=["\']song["\']>(.*?)</div>', svg)
        artist_match = re.search(r'<div class=["\']artist["\']>(.*?)</div>', svg)

        song = html.unescape(song_match.group(1).strip()) if song_match else None
        artist = html.unescape(artist_match.group(1).strip()) if artist_match else None

        if not song or not artist or song == "Currently not playing on Spotify" or artist == "Offline":
            return {
                "is_playing": False,
                "title": None,
                "artist": None,
                "rgb": None,
                "hex": None
            }

        # 提取封面 base64 图片数据
        img_match = re.search(r'<img[^>]*class=["\']cover["\'][^>]*src=["\']data:image/[^;]+;base64,\s*([^"\']+)["\']', svg)
        b64_data = None
        if img_match:
            b64_data = img_match.group(1).strip()
        else:
            all_imgs = re.findall(r'<img[^>]*src=["\']data:image/[^;]+;base64,\s*([^"\']+)["\']', svg)
            if len(all_imgs) > 1:
                b64_data = all_imgs[1].strip()

        rgb = None
        hex_color = None
        if b64_data:
            try:
                raw_bytes = base64.b64decode(b64_data)
                with Image.open(BytesIO(raw_bytes)) as img:
                    img = img.convert('RGB')
                    img.thumbnail((100, 100))
                    buf = BytesIO()
                    img.save(buf, format='JPEG')
                    buf.seek(0)
                colors = colorgram.extract(buf, 1)
                if colors:
                    c = colors[0].rgb
                    rgb = (c.r, c.g, c.b)
                    hex_color = f"#{c.r:02x}{c.g:02x}{c.b:02x}"
            except Exception as e:
                print(f"[Bridge Mode] 封面取色失败: {e}")

        return {
            "is_playing": True,
            "title": song,
            "artist": artist,
            "rgb": rgb,
            "hex": hex_color
        }

    except Exception as e:
        print(f"[Bridge Mode] 请求错误: {e}")
        return None
