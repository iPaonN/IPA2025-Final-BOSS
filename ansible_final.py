import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def _updated_inventory_content(template_path: Path, target_ip: str) -> str:
    content = template_path.read_text()
    lines = content.splitlines()
    updated_lines = []

    for line in lines:
        if "ansible_host=" not in line:
            updated_lines.append(line)
            continue

        parts = line.split()
        for idx, part in enumerate(parts):
            if part.startswith("ansible_host="):
                parts[idx] = f"ansible_host={target_ip}"
        updated_lines.append(" ".join(parts))

    return "\n".join(updated_lines) + "\n"


def showrun(target_ip: Optional[str] = None):
    base_dir = Path(__file__).resolve().parent
    playbook_path = base_dir / "ansible" / "playbooks" / "backup_cisco_router_playbook.yml"
    inventory_path = base_dir / "ansible" / "host"
    backup_file = base_dir / "ansible" / "backups" / "show_run_66070112_CSRv1000.txt"
    ansible_cfg = base_dir / "ansible" / "ansible.cfg"

    if not target_ip:
        return {
            "success": False,
            "message": "Error: IP address required for Ansible command.",
            "file_path": None,
        }

    updated_inventory = _updated_inventory_content(inventory_path, target_ip)

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_inventory:
        temp_inventory.write(updated_inventory)
        temp_inventory_path = temp_inventory.name

    command = [
        "ansible-playbook",
        str(playbook_path),
        "-i",
        temp_inventory_path,
    ]
    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = str(ansible_cfg)
    env.setdefault("ANSIBLE_HOST_KEY_CHECKING", "False")

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=base_dir,
            env=env,
        )
    finally:
        try:
            os.unlink(temp_inventory_path)
        except FileNotFoundError:
            pass

    output = ((process.stdout or "") + (process.stderr or "")).strip()
    print(f"Ansible Output:\n{output}\n")

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
