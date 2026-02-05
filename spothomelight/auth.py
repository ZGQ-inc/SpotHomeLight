import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging
from .config import TOKEN_FILE

def get_spotify_client(config):
    client_id = config['SPOTIFY']['client_id']
    client_secret = config['SPOTIFY']['client_secret']
    redirect_uri = config['SPOTIFY']['redirect_uri']
    
    if not client_id or not client_secret:
        print("错误: 请先在配置文件中填写 Client ID 和 Client Secret。")
        print("运行 'spothomelight -c' 进行配置。")
        return None

    scope = "user-read-playback-state"

    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        open_browser=False,
        cache_path=TOKEN_FILE
    )

    token_info = sp_oauth.get_cached_token()

    if not token_info:
        auth_url = sp_oauth.get_authorize_url()
        print("初次运行需要登录 Spotify。")
        print("考虑到服务器环境，请复制以下 URL 到你电脑的浏览器中打开：")
        print(f"\n{auth_url}\n")
        print("登录并授权后，浏览器会重定向到 127.0.0.1。")
        print("请复制地址栏中的完整 URL，并粘贴到下面。")
        
        response = input("粘贴 URL: ").strip()
        
        try:
            code = sp_oauth.parse_response_code(response)
            token_info = sp_oauth.get_access_token(code)
            print(f"登录成功。Token 已保存至: {TOKEN_FILE}")
        except Exception as e:
            print(f"登录失败: {e}")
            return None

    return spotipy.Spotify(auth=token_info['access_token'], oauth_manager=sp_oauth)