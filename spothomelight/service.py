import os
import sys
import platform
import subprocess

def setup_autostart():
    system = platform.system()
    python_exec = sys.executable
    script_cmd = f'"{python_exec}" -m spothomelight.main'

    if system == "Linux":
        is_root = (os.geteuid() == 0)

        if is_root:
            service_dir = "/etc/systemd/system"
            service_file = "spothomelight.service"
            service_path = os.path.join(service_dir, service_file)
            service_content = f"""[Unit]
Description=SpotHomeLight Service (System)
After=network.target

[Service]
ExecStart={script_cmd}
Restart=always
RestartSec=10
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
            with open(service_path, "w") as f:
                f.write(service_content)
            
            print(f"检测到 Root 用户，已生成系统级服务文件: {service_path}")
            print("正在启用服务...")
            
            os.system("systemctl daemon-reload")
            os.system("systemctl enable --now spothomelight")
            print("完成。请使用 'systemctl status spothomelight' 查看状态。")

        else:
            service_dir = os.path.expanduser("~/.config/systemd/user")
            if not os.path.exists(service_dir):
                os.makedirs(service_dir)
            
            service_content = f"""[Unit]
Description=SpotHomeLight Service (User)
After=network.target

[Service]
ExecStart={script_cmd}
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
"""
            service_path = os.path.join(service_dir, "spothomelight.service")
            with open(service_path, "w") as f:
                f.write(service_content)
            
            print(f"检测到普通用户，已生成用户级服务文件: {service_path}")
            print("正在启用服务...")
            
            ret = os.system("systemctl --user daemon-reload")
            if ret != 0:
                print("警告: 无法重载 daemon，可能是 DBus 环境变量缺失。尝试手动运行: systemctl --user daemon-reload")
            
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