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
    
    device_type = config.get('DEVICE', 'type', fallback='rgb').lower()
    has_motor = config.getboolean('DEVICE', 'has_motor', fallback=False)
    motor_interval = config.getint('DEVICE', 'motor_interval', fallback=10)

    if not webhook_id:
        print("Error: webhook_id is empty.")
        return

    webhook_full_url = f"{ha_url}/api/webhook/{webhook_id}"
    
    print(f"Service started. interval: {interval}s")
    print(f"Device mode: {device_type.upper()}, Motor: {has_motor}")
    print(f"Home Assistant: {webhook_full_url}")

    last_track_id = None
    last_is_playing = False
    last_motor_update_time = 0
    current_tempo = 120.0

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
                    print(f"Now playing: {item['name']} - {item['artists'][0]['name']}")
                    
                    images = item['album']['images']
                    image_url = images[0]['url'] if images else None
                    rgb = get_image_color(image_url) if image_url else None
                    
                    audio_feat = None
                    if device_type in ['rgbw', 'rgb_cct'] or has_motor:
                        try:
                            features = sp.audio_features(tracks=[track_id])
                            if features and features[0]:
                                audio_feat = features[0]
                        except Exception as e:
                            print(f"Fetch audio_features Error: {e}")

                    if rgb:
                        payload = {
                            "state": "playing",
                            "title": item['name'],
                            "artist": item['artists'][0]['name'],
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
                            requests.post(webhook_full_url, json=payload, timeout=5)
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
                        requests.post(webhook_full_url, json=motor_payload, timeout=5)
                        print(f"Push motor update: {current_tempo} BPM")
                    except Exception as e:
                        print(f"Motor Webhook Error: {e}")
                    last_motor_update_time = time.time()

                last_is_playing = True
            
            else:
                if last_is_playing:
                    print("stop/pause playing")
                last_is_playing = False

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

        time.sleep(interval)