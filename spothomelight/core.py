import time
import requests
import json
import spotipy
from spotipy.exceptions import SpotifyException
from .utils import get_image_color, write_pid, remove_pid
from .auth import get_spotify_client
from .config import get_proxy
from .bridge import fetch_bridge_playback

def run_loop(config):
    """运行 Spotify 同步循环（支持 official 官方模式与 bridge 免凭证桥接模式）。
    
    >>> callable(run_loop)
    True
    """
    write_pid()
    try:
        mode = config.get('SPOTIFY', 'mode', fallback='official').lower()
        if mode == 'bridge':
            run_bridge_loop(config)
        else:
            run_official_loop(config)
    finally:
        remove_pid()

def run_bridge_loop(config):
    """免凭证桥接循环（基于 kittinan/spotify-github-profile 公共服务）。"""
    uid = config.get('SPOTIFY', 'uid', fallback='').strip()
    if not uid:
        print("错误: 当前处于 bridge (免凭证) 模式，请在配置文件中填写 uid。")
        print("请访问 https://spotify-github-profile.kittinanx.com 登录并复制分配的 UID。")
        print("运行 'spothomelight -c' 可编辑配置。")
        return

    proxies = get_proxy(config)
    ha_url = config['HOME_ASSISTANT']['ha_url'].rstrip('/')
    webhook_id = config['HOME_ASSISTANT']['webhook_id']
    interval = int(config['GENERAL']['interval'])

    if not webhook_id:
        print("Error: webhook_id is empty.")
        return

    webhook_full_url = f"{ha_url}/api/webhook/{webhook_id}"

    print("=" * 65)
    print("【SpotHomeLight】当前运行在：免凭证桥接模式 (Bridge Mode)")
    print("【特别鸣谢】感谢开源项目 kittinan/spotify-github-profile 提供的公共服务支持！")
    print(f"监控 Spotify 用户 UID: {uid}")
    print(f"刷新周期: {interval}s")
    print(f"Home Assistant Webhook: {webhook_full_url}")
    print("=" * 65)

    last_track_key = None
    last_is_playing = False

    ha_session = requests.Session()
    ha_session.trust_env = False

    while True:
        try:
            info = fetch_bridge_playback(uid, proxies=proxies)
            if info and info.get('is_playing'):
                title = info.get('title', 'Unknown')
                artist = info.get('artist', 'Unknown')
                track_key = (title, artist)

                if track_key != last_track_key or not last_is_playing:
                    print(f"Now playing: {title} - {artist}", flush=True)
                    rgb = info.get('rgb')
                    hex_color = info.get('hex')

                    if rgb:
                        payload = {
                            "state": "playing",
                            "title": title,
                            "artist": artist,
                            "image_url": "https://spotify-github-profile.kittinanx.com",
                            "rgb": list(rgb),
                            "hex": hex_color,
                            "energy": 1.0,
                            "valence": 0.5
                        }
                        try:
                            ha_session.post(webhook_full_url, json=payload, timeout=5)
                            print(f"Push {hex_color} to HA (Bridge Mode)", flush=True)
                        except Exception as e:
                            print(f"Webhook Error: {e}", flush=True)

                    last_track_key = track_key

                last_is_playing = True
            else:
                if last_is_playing:
                    print("stop/pause playing", flush=True)
                last_is_playing = False

        except Exception as e:
            print(f"[Bridge Mode Error]: {e}", flush=True)
            time.sleep(10)

        time.sleep(interval)

def run_official_loop(config):
    """官方 Web API 循环。"""
    sp = get_spotify_client(config)
    if not sp:
        return

    proxies = get_proxy(config)
    ha_url = config['HOME_ASSISTANT']['ha_url'].rstrip('/')
    webhook_id = config['HOME_ASSISTANT']['webhook_id']
    interval = int(config['GENERAL']['interval'])
    
    device_type = config.get('DEVICE', 'type', fallback='rgb').lower()
    has_motor = config.getboolean('DEVICE', 'has_motor', fallback=False)
    motor_interval = config.getint('DEVICE', 'motor_interval', fallback=10)

    if not webhook_id:
        print("Error: webhook_id is empty.")
        return

    webhook_full_url = f"{ha_url}/api/webhook/{webhook_id}"
    
    print("=" * 65)
    print("【SpotHomeLight】当前运行在：官方 Web API 模式 (Official Mode)")
    print(f"Service started. interval: {interval}s")
    print(f"Device mode: {device_type.upper()}, Motor: {has_motor}")
    print(f"Home Assistant: {webhook_full_url}")
    print("=" * 65)

    last_track_id = None
    last_is_playing = False
    last_motor_update_time = 0
    current_tempo = 120.0

    ha_session = requests.Session()
    ha_session.trust_env = False

    while True:
        try:
            playback = sp.current_playback()
            
            if playback and playback.get('is_playing'):
                item = playback.get('item')
                if not item: 
                    time.sleep(interval)
                    continue

                track_id = item.get('id')
                
                if (track_id and track_id != last_track_id) or not last_is_playing:
                    track_name = item.get('name', 'Unknown')
                    artist_name = item['artists'][0]['name'] if item.get('artists') else 'Unknown'
                    print(f"Now playing: {track_name} - {artist_name}")
                    
                    images = item.get('album', {}).get('images', [])
                    image_url = images[0]['url'] if images else None
                    rgb = get_image_color(image_url, proxies=proxies) if image_url else None
                    
                    audio_feat = None
                    if (device_type in ['rgbw', 'rgb_cct'] or has_motor) and track_id:
                        try:
                            features = sp.audio_features(tracks=[track_id])
                            if features and features[0]:
                                audio_feat = features[0]
                        except Exception as e:
                            print(f"Fetch audio_features Error: {e}")

                    if rgb:
                        payload = {
                            "state": "playing",
                            "title": track_name,
                            "artist": artist_name,
                            "image_url": image_url,
                            "rgb": list(rgb),
                            "hex": '#%02x%02x%02x' % rgb
                        }

                        if audio_feat:
                            if device_type in ['rgbw', 'rgb_cct']:
                                payload['energy'] = audio_feat.get('energy', 1.0)
                            if device_type == 'rgb_cct':
                                payload['valence'] = audio_feat.get('valence', 0.5)
                            if has_motor:
                                current_tempo = audio_feat.get('tempo', 120.0)
                                payload['tempo'] = current_tempo
                        
                        try:
                            ha_session.post(webhook_full_url, json=payload, timeout=5)
                            print(f"Push {payload['hex']} to HA (Energy: {payload.get('energy', 'N/A')}, BPM: {payload.get('tempo', 'N/A')})")
                        except Exception as e:
                            print(f"Webhook Error: {e}")
                    
                    last_track_id = track_id
                    last_motor_update_time = time.time() 
                
                elif has_motor and (time.time() - last_motor_update_time >= motor_interval):
                    motor_payload = {
                        "state": "motor_update",
                        "tempo": current_tempo
                    }
                    try:
                        ha_session.post(webhook_full_url, json=motor_payload, timeout=5)
                        print(f"Push motor update: {current_tempo} BPM")
                    except Exception as e:
                        print(f"Motor Webhook Error: {e}")
                    last_motor_update_time = time.time()

                last_is_playing = True
            
            else:
                if last_is_playing:
                    print("stop/pause playing")
                last_is_playing = False

        except requests.exceptions.RequestException as e:
            print(f"Network Error: {e}")
            time.sleep(10)
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 403 and "Active premium subscription" in str(e):
                print("错误 [Spotify 403 Forbidden]: 创建此 Spotify Developer App 的账号必须拥有处于有效期的 Spotify Premium (会员)。")
                print("原因: Spotify 官方政策限制，开发者后台 App 的所有者账号必须为 Premium。")
                print("提示: 若无 Spotify 会员，您可切换至 bridge 免凭证模式 (修改配置文件 mode = bridge 并填写 uid)。")
            else:
                print(f"Spotify API Error: {e}")
            time.sleep(15)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

        time.sleep(interval)
