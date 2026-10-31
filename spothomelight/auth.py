import os
import sys
import webbrowser
import threading
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
from .config import TOKEN_FILE, get_proxy

def get_spotify_client(config):
    """获取并验证 Spotify 客户端。
    
    >>> callable(get_spotify_client)
    True
    """
    client_id = config['SPOTIFY']['client_id']
    client_secret = config['SPOTIFY']['client_secret']
    redirect_uri = config['SPOTIFY']['redirect_uri']
    
    if not client_id or not client_secret:
        print("错误: 请先在配置文件中填写 Client ID 和 Client Secret。")
        print("运行 'spothomelight -c' 进行配置。")
        return None

    proxies = get_proxy(config)
    scope = "user-read-playback-state"

    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        open_browser=False,
        cache_path=TOKEN_FILE,
        proxies=proxies
    )

    token_info = None
    try:
        token_info = sp_oauth.get_cached_token()
    except (SpotifyOauthError, Exception) as e:
        print(f"提示: 缓存的 Spotify Token 验证失败 ({e})，需要重新授权。")
        if os.path.exists(TOKEN_FILE):
            try:
                os.remove(TOKEN_FILE)
            except OSError:
                pass
        token_info = None

    if not token_info:
        if not sys.stdin.isatty():
            print("错误: Spotify Token 无效或不存在，且当前处于非交互环境（如 systemd 服务运行中）。")
            print("请先停止服务，并在终端中手动运行 'spothomelight --auth' 完成登录授权后，再启动服务。")
            return None

        auth_url = sp_oauth.get_authorize_url()
        print("\n" + "=" * 60)
        print("初次运行或 Token 已失效，需要登录 Spotify 进行授权。")
        print("已尝试在默认浏览器中打开授权页面。如果未自动打开，请复制以下链接访问：")
        print(f"\n{auth_url}\n")
        print("=" * 60 + "\n")

        # 尝试启动本地 HTTP 回调服务以自动获取授权码
        code_holder = {"code": None}
        server_obj = None

        parsed_uri = urlparse(redirect_uri)
        if parsed_uri.hostname in ("127.0.0.1", "localhost") and parsed_uri.port:
            class OAuthCallbackHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    parsed_req = urlparse(self.path)
                    if parsed_req.path == parsed_uri.path:
                        query = parse_qs(parsed_req.query)
                        if 'code' in query:
                            code_holder["code"] = query['code'][0]
                            self.send_response(200)
                            self.send_header('Content-Type', 'text/html; charset=utf-8')
                            self.end_headers()
                            self.wfile.write("<html><body><h1 style='color:green;'>Spotify 授权成功！</h1><p>您可以关闭此页面并回到终端。</p></body></html>".encode('utf-8'))
                        elif 'error' in query:
                            self.send_response(400)
                            self.send_header('Content-Type', 'text/html; charset=utf-8')
                            self.end_headers()
                            self.wfile.write(f"<html><body><h1 style='color:red;'>授权失败</h1><p>{query['error'][0]}</p></body></html>".encode('utf-8'))
                    else:
                        self.send_response(404)
                        self.end_headers()

                def log_message(self, format, *args):
                    pass

            try:
                server_obj = HTTPServer(('0.0.0.0', parsed_uri.port), OAuthCallbackHandler)
                server_thread = threading.Thread(target=server_obj.handle_request, daemon=True)
                server_thread.start()
            except Exception:
                server_obj = None

        try:
            webbrowser.open(auth_url)
        except Exception:
            pass

        print("提示: 授权完成后若浏览器自动回调成功，将无需手动粘贴；")
        print("若在无浏览器环境（如远程 SSH），请在本地浏览器打开链接授权后，复制地址栏完整 URL 粘贴到下方。")

        # 等待用户手动输入或回调服务器接收
        if server_obj and code_holder["code"]:
            code = code_holder["code"]
        else:
            try:
                response = input("\n粘贴重定向后的 URL 或授权码 (按回车提交): ").strip()
                if code_holder["code"]:
                    code = code_holder["code"]
                elif response.startswith("http"):
                    code = sp_oauth.parse_response_code(response)
                else:
                    code = response
            except (EOFError, KeyboardInterrupt):
                if server_obj and code_holder["code"]:
                    code = code_holder["code"]
                else:
                    return None

        if server_obj:
            try:
                server_obj.server_close()
            except Exception:
                pass

        try:
            token_info = sp_oauth.get_access_token(code, check_cache=False)
            print(f"登录成功！Token 已保存至: {TOKEN_FILE}")
        except Exception as e:
            print(f"登录失败: {e}")
            return None

    return spotipy.Spotify(oauth_manager=sp_oauth, proxies=proxies)
