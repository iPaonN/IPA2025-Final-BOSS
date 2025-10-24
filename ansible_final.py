import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import netmiko_final


BASE_DIR = Path(__file__).resolve().parent
PLAYBOOK_DIR = BASE_DIR / "ansible" / "playbooks"
INVENTORY_TEMPLATE = BASE_DIR / "ansible" / "host"
ANSIBLE_CFG = BASE_DIR / "ansible" / "ansible.cfg"
BACKUP_FILE = BASE_DIR / "ansible" / "backups" / "show_run_66070112_CSRv1000.txt"


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


def _run_playbook(playbook_name: str, target_ip: str, extra_vars: Optional[dict] = None) -> Tuple[int, str, str]:
    updated_inventory = _updated_inventory_content(INVENTORY_TEMPLATE, target_ip)

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_inventory:
        temp_inventory.write(updated_inventory)
        temp_inventory_path = temp_inventory.name

    command = [
        "ansible-playbook",
        str(PLAYBOOK_DIR / playbook_name),
        "-i",
        temp_inventory_path,
    ]

    if extra_vars:
        command.extend(["--extra-vars", json.dumps(extra_vars)])

    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = str(ANSIBLE_CFG)
    env.setdefault("ANSIBLE_HOST_KEY_CHECKING", "False")
    env.setdefault("ANSIBLE_STDOUT_CALLBACK", "json")

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=BASE_DIR,
            env=env,
        )
    finally:
        try:
            os.unlink(temp_inventory_path)
        except FileNotFoundError:
            pass

    stdout = (process.stdout or "").strip()
    stderr = (process.stderr or "").strip()
    output_log = "\n".join(part for part in (stdout, stderr) if part)
    print(f"Ansible ({playbook_name}) output:\n{output_log}\n")

    return process.returncode, stdout, stderr


def showrun(target_ip: Optional[str] = None):
    if not target_ip:
        return {
            "success": False,
            "message": "Error: IP address required for Ansible command.",
            "file_path": None,
        }

    returncode, _, _ = _run_playbook("backup_cisco_router_playbook.yml", target_ip)

    if returncode == 0 and BACKUP_FILE.exists():
        return {
            "success": True,
            "message": "show running config.",
            "file_path": BACKUP_FILE,
        }

    return {
        "success": False,
        "message": "Error: Ansible.",
        "file_path": None,
    }


def motd(target_ip: Optional[str] = None, banner_message: Optional[str] = None):
    if not target_ip:
        return {
            "success": False,
            "message": "Error: IP address required for Ansible command.",
            "file_path": None,
        }

    motd_text = (banner_message or "").strip()

    if motd_text:
        returncode, _, _ = _run_playbook(
            "motd_set_cisco_router_playbook.yml",
            target_ip,
            {"banner_message": motd_text},
        )

        if returncode == 0:
            return {
                "success": True,
                "message": "Ok: success.",
                "file_path": None,
            }

        return {
            "success": False,
            "message": "Error: MOTD update.",
            "file_path": None,
        }

    try:
        motd_value = netmiko_final.motd_banner(target_ip)
    except Exception as exc:
        print(f"Netmiko MOTD error: {exc}")
        motd_value = ""

    message = motd_value if motd_value else "Error: No MOTD configured."
    return {
        "success": bool(motd_value),
        "message": message,
        "file_path": None,
    }
