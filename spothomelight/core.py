import time
import requests
import json
from .utils import get_image_color, write_pid
from .auth import get_spotify_client

def run_loop(config):
    write_pid()

    sp = get_spotify_client(config)
    if not sp:
        return

    ha_url = config['HOME_ASSISTANT']['ha_url'].rstrip('/')
    webhook_id = config['HOME_ASSISTANT']['webhook_id']
    interval = int(config['GENERAL']['interval'])
    
    if not webhook_id:
        print("错误: 配置文件中 webhook_id 为空，无法发送数据。")
        return

    webhook_full_url = f"{ha_url}/api/webhook/{webhook_id}"
    
    print(f"服务已启动。监控频率: {interval}秒")
    print(f"Home Assistant 地址: {webhook_full_url}")

    last_track_id = None
    last_is_playing = False

    while True:
        try:
            playback = sp.current_playback()
            
            if playback and playback['is_playing']:
                item = playback['item']
                if not item: 
                    time.sleep(interval)
                    continue

                track_id = item['id']
                
                if track_id != last_track_id or not last_is_playing:
                    print(f"检测到正在播放: {item['name']} - {item['artists'][0]['name']}")
                    
                    images = item['album']['images']
                    image_url = images[0]['url'] if images else None
                    
                    if image_url:
                        rgb = get_image_color(image_url)
                        if rgb:
                            payload = {
                                "state": "playing",
                                "title": item['name'],
                                "artist": item['artists'][0]['name'],
                                "image_url": image_url,
                                "rgb": list(rgb),
                                "hex": '#%02x%02x%02x' % rgb
                            }
                            
                            try:
                                requests.post(webhook_full_url, json=payload, timeout=5)
                                print(f"已发送颜色 {payload['hex']} 到 HA")
                            except Exception as e:
                                print(f"发送 Webhook 失败: {e}")
                    
                    last_track_id = track_id
                
                last_is_playing = True
            
            else:
                if last_is_playing:
                    print("播放已暂停/停止")
                    # try:
                    #     requests.post(webhook_full_url, json={"state": "paused"}, timeout=5)
                    # except:
                    #     pass
                last_is_playing = False

        except Exception as e:
            print(f"运行循环发生错误: {e}")
            time.sleep(10)

        time.sleep(interval)