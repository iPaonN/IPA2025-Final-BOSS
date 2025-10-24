import os
import subprocess
from pathlib import Path


def showrun():
    base_dir = Path(__file__).resolve().parent
    playbook_path = base_dir / "ansible" / "playbooks" / "backup_cisco_router_playbook.yml"
    inventory_path = base_dir / "ansible" / "host"
    backup_file = base_dir / "ansible" / "backups" / "show_run_66070112_CSRv1000.txt"
    ansible_cfg = base_dir / "ansible" / "ansible.cfg"

    command = [
        "ansible-playbook",
        str(playbook_path),
        "-i",
        str(inventory_path),
    ]
    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = str(ansible_cfg)
    env.setdefault("ANSIBLE_HOST_KEY_CHECKING", "False")

    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=base_dir,
        env=env,
    )

    # output = ((process.stdout or "") + (process.stderr or "")).strip()

    if process.returncode == 0 and backup_file.exists():
        return {
            "success": True,
            "message": "show running config.",
            # "output": output,
            "file_path": backup_file,
        }

    return {
        "success": False,
        "message": "Error: Ansible.",
        # "output": output,
        "file_path": None,
    }
