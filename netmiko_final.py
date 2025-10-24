import netmiko
from pprint import pprint
import os
from pathlib import Path
from typing import Optional

import textfsm

device_ip = os.getenv("DEVICE_IP")
username = os.getenv("userNAME")
password = os.getenv("passWORD")

device_params = {
    "device_type": "cisco_ios",
    "ip": device_ip,
    "username": username,
    "password": password,
}

BASE_DIR = Path(__file__).resolve().parent
TEXTFSM_TEMPLATE_DIR = BASE_DIR / "textfsm_templates"
MOTD_TEMPLATE = TEXTFSM_TEMPLATE_DIR / "cisco_ios_show_banner_motd.template"


def _build_device_params(target_ip: Optional[str] = None) -> dict:
    params = device_params.copy()
    if target_ip:
        params["ip"] = target_ip
    if not params.get("ip"):
        raise ValueError("Device IP not provided for Netmiko connection.")
    if not params.get("username") or not params.get("password"):
        raise ValueError("Device credentials are not set for Netmiko connection.")
    return params


def _parse_motd(output: str) -> str:
    text = (output or "").strip()
    if not text:
        return ""

    if not MOTD_TEMPLATE.exists():
        return text

    try:
        with MOTD_TEMPLATE.open() as template_file:
            fsm = textfsm.TextFSM(template_file)
            parsed_rows = fsm.ParseText(text)
    except Exception as exc:
        print(f"TextFSM MOTD parse error: {exc}")
        return text

    if not parsed_rows or "BANNER_LINE" not in fsm.header:
        return text

    col_idx = fsm.header.index("BANNER_LINE")
    lines = [row[col_idx].strip() for row in parsed_rows if row[col_idx].strip()]
    return "\n".join(lines).strip()


def motd_banner(target_ip: Optional[str] = None) -> str:
    params = _build_device_params(target_ip)
    with netmiko.ConnectHandler(**params) as ssh:
        output = ssh.send_command("show banner motd")
    return _parse_motd(output)


def gigabit_status():
    ans = ""
    with netmiko.ConnectHandler(**device_params) as ssh:
        up = down = admin_down = 0
        result = ssh.send_command("show ip interface brief", use_textfsm=True)

        # TextFSM returns a list of dicts; if it is not available we fall back to manual parsing.
        if isinstance(result, str):
            parsed = []
            for line in result.splitlines():
                if not line or line.lower().startswith("interface"):
                    continue
                if not line.startswith("GigabitEthernet"):
                    continue
                parts = line.split()
                if len(parts) < 6:
                    continue
                parsed.append(
                    {
                        "interface": parts[0],
                        "status": parts[4],
                        "protocol": parts[5],
                    }
                )
        else:
            parsed = result

        statuses = []
        for interface in parsed:
            name = interface.get("interface") or interface.get("intf") or interface.get("Interface", "")
            if not name.startswith("GigabitEthernet"):
                continue
            status = (interface.get("status") or interface.get("Status") or "").lower()
            if status == "administratively down":
                admin_down += 1
            elif status == "up":
                up += 1
            elif status == "down":
                down += 1
            statuses.append(f"{name} {status or 'unknown'}")

        status_line = ", ".join(statuses) if statuses else "No GigabitEthernet interfaces found"
        summary_line = f"-> {up} up, {down} down, {admin_down} administratively down"
        ans = f"{status_line} {summary_line}".strip()
        pprint(ans)
        return ans
