"""
SpotHomeLight - Bridge Mode (免凭证桥接模式)

特别鸣谢 / Credits:
本模块免凭证桥接功能由以下优秀开源项目提供的公共服务支持，特此致谢：
1. kittinan/spotify-github-profile (https://github.com/kittinan/spotify-github-profile)
   Special thanks to @kittinan for providing the public Spotify profile SVG service.
2. JeffreyCA/spotify-recently-played-readme (https://github.com/JeffreyCA/spotify-recently-played-readme)
   Special thanks to @JeffreyCA for providing the recently played Spotify profile service.
"""

import re
import html
import base64
import requests
from io import BytesIO
from PIL import Image
import colorgram

KITTINAN_VIEW_URL = "https://spotify-github-profile.kittinanx.com/api/view"
JEFFREYCA_API_URL = "https://spotify-recently-played-readme.vercel.app/api"


def extract_dominant_color_from_base64(b64_data):
    """从 Base64 图片数据中提取主色调 RGB 与 Hex。

    >>> callable(extract_dominant_color_from_base64)
    True
    """
    if not b64_data:
        return None, None
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
            return (c.r, c.g, c.b), f"#{c.r:02x}{c.g:02x}{c.b:02x}"
    except Exception as e:
        print(f"[Bridge Mode] 封面取色失败: {e}", flush=True)
    return None, None


def _fetch_kittinan(uid, proxies=None):
    """通过 kittinan/spotify-github-profile 接口获取当前播放信息。"""
    params = {
        "uid": uid,
        "cover_image": "true",
        "show_offline": "true"
    }
    headers = {
        "User-Agent": "SpotHomeLight/1.2.1 (HomeAssistant Sync)"
    }
    resp = requests.get(KITTINAN_VIEW_URL, params=params, headers=headers, proxies=proxies, timeout=8)
    resp.raise_for_status()
    svg = resp.text

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
            "hex": None,
            "source": "kittinan/spotify-github-profile"
        }

    img_match = re.search(r'<img[^>]*class=["\']cover["\'][^>]*src=["\']data:image/[^;]+;base64,\s*([^"\']+)["\']', svg)
    b64_data = None
    if img_match:
        b64_data = img_match.group(1).strip()
    else:
        all_imgs = re.findall(r'<img[^>]*src=["\']data:image/[^;]+;base64,\s*([^"\']+)["\']', svg)
        if len(all_imgs) > 1:
            b64_data = all_imgs[1].strip()

    rgb, hex_color = extract_dominant_color_from_base64(b64_data)
    return {
        "is_playing": True,
        "title": song,
        "artist": artist,
        "rgb": rgb,
        "hex": hex_color,
        "source": "kittinan/spotify-github-profile"
    }


def _fetch_jeffreyca(uid, proxies=None):
    """通过 JeffreyCA/spotify-recently-played-readme 接口获取播放信息。"""
    params = {
        "user": uid,
        "count": "5"
    }
    headers = {
        "User-Agent": "SpotHomeLight/1.2.1 (HomeAssistant Sync)"
    }
    resp = requests.get(JEFFREYCA_API_URL, params=params, headers=headers, proxies=proxies, timeout=8)
    resp.raise_for_status()
    svg = resp.text

    title_match = re.search(r'<g><title>(.*?)\s*\n\s*by\s*(.*?)\s*\n\s*from\s*(.*?)</title>', svg)
    if title_match:
        song = html.unescape(title_match.group(1).strip())
        artist = html.unescape(title_match.group(2).strip())
    else:
        texts = re.findall(r'<text[^>]*>(.*?)</text>', svg)
        if len(texts) >= 3 and texts[0] == "Recently Played":
            song = html.unescape(texts[1].strip())
            artist = html.unescape(texts[2].strip())
        else:
            return None

    if not song or not artist:
        return {
            "is_playing": False,
            "title": None,
            "artist": None,
            "rgb": None,
            "hex": None,
            "source": "JeffreyCA/spotify-recently-played-readme"
        }

    img_match = re.search(r'<image[^>]+href=[\'"]data:image/[^;]+;base64,\s*([^\'"]+)[\'"]', svg)
    b64_data = img_match.group(1).strip() if img_match else None
    rgb, hex_color = extract_dominant_color_from_base64(b64_data)

    return {
        "is_playing": True,
        "title": song,
        "artist": artist,
        "rgb": rgb,
        "hex": hex_color,
        "source": "JeffreyCA/spotify-recently-played-readme"
    }


def fetch_bridge_playback(uid, proxies=None):
    """通过免凭证公共服务获取当前播放信息并提取封面主色调。

    采用双源热备容灾机制：
    1. 首选开源项目 kittinan/spotify-github-profile 公共接口。
    2. 若遇 500 内部错误或网络超时，自动无缝切换至备用开源项目 JeffreyCA/spotify-recently-played-readme。

    特别鸣谢:
    - @kittinan (https://github.com/kittinan/spotify-github-profile)
    - @JeffreyCA (https://github.com/JeffreyCA/spotify-recently-played-readme)

    >>> callable(fetch_bridge_playback)
    True
    """
    if not uid:
        return None

    # 1. 尝试首选源 kittinan
    try:
        data = _fetch_kittinan(uid, proxies=proxies)
        if data is not None:
            return data
    except Exception as e:
        # 当遇到 500、429 或连接异常时，无缝切换备用源
        print(f"[Bridge Mode] 首选源 (kittinan) 访问异常 ({e})，自动切换备用源 (JeffreyCA)...", flush=True)

    # 2. 备用源 JeffreyCA
    try:
        data = _fetch_jeffreyca(uid, proxies=proxies)
        if data is not None:
            return data
    except Exception as e:
        print(f"[Bridge Mode] 备用源 (JeffreyCA) 访问异常: {e}", flush=True)

    return None
