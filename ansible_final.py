import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import textfsm


BASE_DIR = Path(__file__).resolve().parent
PLAYBOOK_DIR = BASE_DIR / "ansible" / "playbooks"
INVENTORY_TEMPLATE = BASE_DIR / "ansible" / "host"
ANSIBLE_CFG = BASE_DIR / "ansible" / "ansible.cfg"
TEXTFSM_TEMPLATE_DIR = BASE_DIR / "textfsm_templates"
MOTD_TEMPLATE = TEXTFSM_TEMPLATE_DIR / "cisco_ios_show_banner_motd.template"
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


def _load_ansible_json(stdout: str) -> Optional[dict]:
    text = (stdout or "").strip()
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for line in text.splitlines():
            candidate = line.strip()
            if not candidate:
                continue
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    return None


def _extract_banner_lines(task_data: dict) -> list[str]:
    hosts = task_data.get("hosts", {})
    lines: list[str] = []

    for host_result in hosts.values():
        stdout_lines = host_result.get("stdout_lines")
        if stdout_lines:
            first_entry = stdout_lines[0]
            if isinstance(first_entry, list):
                lines.extend(first_entry)
            elif isinstance(first_entry, str):
                lines.extend(stdout_lines)
            continue

        stdout_value = host_result.get("stdout")
        if isinstance(stdout_value, list):
            lines.extend("\n".join(stdout_value).splitlines())
        elif isinstance(stdout_value, str):
            lines.extend(stdout_value.splitlines())

        msg_value = host_result.get("msg")
        if isinstance(msg_value, str):
            lines.extend(msg_value.splitlines())

    return [line for line in lines if line.strip()]


def _parse_motd_with_textfsm(text: str) -> str:
    if not text or not MOTD_TEMPLATE.exists():
        return text.strip()

    with MOTD_TEMPLATE.open() as template_file:
        fsm = textfsm.TextFSM(template_file)
        parsed_rows = fsm.ParseText(text)

    if not parsed_rows or "BANNER_LINE" not in fsm.header:
        return text.strip()

    line_index = fsm.header.index("BANNER_LINE")
    parsed_lines = [row[line_index].strip() for row in parsed_rows if row[line_index].strip()]
    return "\n".join(parsed_lines).strip()


def _extract_motd_from_output(stdout: str) -> str:
    data = _load_ansible_json(stdout)
    if not data:
        return ""

    banner_lines: list[str] = []
    plays = data.get("plays", [])

    for play_data in plays:
        tasks = play_data.get("tasks", [])
        for task_data in tasks:
            task_name = task_data.get("task", {}).get("name", "")
            if task_name == "Retrieve MOTD banner":
                banner_lines.extend(_extract_banner_lines(task_data))
            if task_name == "Report MOTD banner" and not banner_lines:
                banner_lines.extend(_extract_banner_lines(task_data))

    if not banner_lines:
        return ""

    return _parse_motd_with_textfsm("\n".join(banner_lines))


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

    returncode, stdout, _ = _run_playbook("motd_get_cisco_router_playbook.yml", target_ip)

    if returncode == 0:
        motd_value = _extract_motd_from_output(stdout)
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
        "message": "Error: No MOTD configured.",
        "file_path": None,
    }
