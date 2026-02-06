import argparse
import sys
from .config import load_config, open_config_editor
from .service import setup_autostart, start_managed_service
from .utils import check_running, stop_process
from .core import run_loop

def main():
    parser = argparse.ArgumentParser(
        prog="SpotHomeLight",
        description="Spotify 专辑封面颜色控制智能家居（Home Assistant）。",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
        """
    )
    
    config_group = parser.add_argument_group('配置选项')
    config_group.add_argument("-c", "--config", action="store_true", help="打开配置文件")
    service_group = parser.add_argument_group('服务管理')
    service_group.add_argument("-a", "--autostart", action="store_true", help="配置开机自动运行")
    service_group.add_argument("--start", action="store_true", help="启动已配置的后台服务")
    service_group.add_argument("-s", "--stop", action="store_true", help="停止正在运行的服务")
    
    args = parser.parse_args()

    if args.config:
        open_config_editor()
        sys.exit(0)

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
        stop_process()

if __name__ == "__main__":
    main()