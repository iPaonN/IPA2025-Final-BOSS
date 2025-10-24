import netmiko
from pprint import pprint
import os

device_ip = os.getenv("DEVICE_IP")
username = os.getenv("userNAME")
password = os.getenv("passWORD")

device_params = {
    "device_type": "cisco_ios",
    "ip": device_ip,
    "username": username,
    "password": password,
}


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
