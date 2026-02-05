import os
import sys
import platform
import subprocess

def setup_autostart():
    system = platform.system()
    python_exec = sys.executable
    script_cmd = f'"{python_exec}" -m spothomelight.main'

    if system == "Linux":
        service_dir = os.path.expanduser("~/.config/systemd/user")
        if not os.path.exists(service_dir):
            os.makedirs(service_dir)
        
        service_content = f"""[Unit]
Description=SpotHomeLight Service
After=network.target

[Service]
ExecStart={script_cmd}
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
"""
        service_path = os.path.join(service_dir, "spothomelight.service")
        with open(service_path, "w") as f:
            f.write(service_content)
        
        print(f"已生成 Systemd 服务文件: {service_path}")
        print("正在启用服务...")
        os.system("systemctl --user daemon-reload")
        os.system("systemctl --user enable --now spothomelight")
        print("完成。请使用 'systemctl --user status spothomelight' 查看状态。")

    elif system == "Windows":
        task_name = "SpotHomeLightAutoStart"
        cmd = [
            "schtasks", "/Create", "/F",
            "/TN", task_name,
            "/TR", script_cmd,
            "/SC", "ONLOGON",
            "/RL", "HIGHEST"
        ]
        try:
            subprocess.run(cmd, check=True)
            print(f"已创建 Windows 计划任务: {task_name}")
            print("下次登录时将自动运行。")
        except subprocess.CalledProcessError as e:
            print(f"创建计划任务失败: {e}")