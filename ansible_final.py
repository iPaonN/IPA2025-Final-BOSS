import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple


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


def _run_playbook(playbook_name: str, target_ip: str, extra_vars: Optional[dict] = None) -> Tuple[int, str]:
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

    output = ((process.stdout or "") + (process.stderr or "")).strip()
    print(f"Ansible ({playbook_name}) output:\n{output}\n")

    return process.returncode, output


def showrun(target_ip: Optional[str] = None):
    if not target_ip:
        return {
            "success": False,
            "message": "Error: IP address required for Ansible command.",
            "file_path": None,
        }

    returncode, _ = _run_playbook("backup_cisco_router_playbook.yml", target_ip)

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


def _extract_motd_from_output(output: str) -> str:
    match = re.search(r'"msg"\s*:\s*"([^"]*)"', output)
    if not match:
        return ""
    raw_message = match.group(1)
    try:
        decoded = bytes(raw_message, "utf-8").decode("unicode_escape")
    except Exception:
        decoded = raw_message
    return decoded.strip()


def motd(target_ip: Optional[str] = None, banner_message: Optional[str] = None):
    if not target_ip:
        return {
            "success": False,
            "message": "Error: IP address required for Ansible command.",
            "file_path": None,
        }

    motd_text = (banner_message or "").strip()

    if motd_text:
        returncode, _ = _run_playbook(
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

    returncode, output = _run_playbook("motd_get_cisco_router_playbook.yml", target_ip)

    if returncode == 0:
        motd_value = _extract_motd_from_output(output)
        message = (
            f"{motd_value}"
            if motd_value
            else "Error: No MOTD configured."
        )
        success = bool(motd_value)
        return {
            "success": success,
            "message": message,
            "file_path": None,
        }

    return {
        "success": False,
        "message": "Error: Unable to read MOTD.",
        "file_path": None,
    }
