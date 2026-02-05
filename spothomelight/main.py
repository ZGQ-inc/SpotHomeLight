import argparse
import sys
from .config import load_config, open_config_editor
from .service import setup_autostart
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
    
    parser.add_argument("-c", "--config", action="store_true", help="打开配置文件")
    parser.add_argument("-a", "--autostart", action="store_true", help="配置开机自动运行")
    parser.add_argument("-s", "--stop", action="store_true", help="停止正在运行的服务")
    
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

    pid = check_running()
    if pid:
        print(f"错误: 服务已在运行中 (PID: {pid})。请先停止或直接使用。")
        sys.exit(1)

    config = load_config()
    try:
        run_loop(config)
    except KeyboardInterrupt:
        print("\n用户手动停止。")
        stop_process()

if __name__ == "__main__":
    main()