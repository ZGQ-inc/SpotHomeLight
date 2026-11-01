import argparse
import sys
from .config import load_config, open_config_editor
from .service import setup_autostart, start_managed_service
from .utils import check_running, stop_process, remove_pid
from .core import run_loop
from .auth import get_spotify_client

def main():
    parser = argparse.ArgumentParser(
        prog="SpotHomeLight",
        description="Spotify 专辑封面颜色控制智能家居（Home Assistant）。",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
特别鸣谢 / Credits:
本项目免凭证桥接功能由开源项目 kittinan/spotify-github-profile
(https://github.com/kittinan/spotify-github-profile) 提供的公共服务支持，特此致谢！
        """
    )
    
    config_group = parser.add_argument_group('配置选项')
    config_group.add_argument("-c", "--config", action="store_true", help="打开配置文件")
    config_group.add_argument("-l", "--auth", action="store_true", help="登录并授权 Spotify (仅官方模式)")
    
    service_group = parser.add_argument_group('服务管理')
    service_group.add_argument("-a", "--autostart", action="store_true", help="配置开机自动运行")
    service_group.add_argument("--start", action="store_true", help="启动已配置的后台服务")
    service_group.add_argument("-s", "--stop", action="store_true", help="停止正在运行的服务")
    
    args = parser.parse_args()

    if args.config:
        open_config_editor()
        sys.exit(0)

    if args.auth:
        config = load_config()
        mode = config.get('SPOTIFY', 'mode', fallback='official').lower()
        if mode == 'bridge':
            print("提示: 当前配置为 bridge (免凭证) 模式，无需进行 OAuth 登录授权。")
            print("只需在配置文件中填写您的 UID 即可。若需使用官方 API 模式，请在配置文件中设置 mode = official。")
            sys.exit(0)

        client = get_spotify_client(config)
        if client:
            print("Spotify 授权成功且有效！")
            sys.exit(0)
        else:
            print("Spotify 授权失败。")
            sys.exit(1)

    if args.stop:
        stop_process()
        sys.exit(0)

    if args.autostart:
        setup_autostart()
        sys.exit(0)

    if args.start:
        pid = check_running()
        if pid:
            print(f"提示: 服务已经在运行中 (PID: {pid})，无需重复启动。")
        else:
            start_managed_service()
        sys.exit(0)

    pid = check_running()
    if pid:
        print(f"错误: 服务已在后台运行中 (PID: {pid})。")
        print("如果要查看实时日志或调试，请先停止服务: spothomelight -s")
        sys.exit(1)

    config = load_config()
    try:
        run_loop(config)
    except KeyboardInterrupt:
        print("\n用户手动停止。")
    finally:
        remove_pid()

if __name__ == "__main__":
    main()
