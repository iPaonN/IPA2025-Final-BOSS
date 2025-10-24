import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

requests.packages.urllib3.disable_warnings()

api_url = os.getenv("API_URL")

# the RESTCONF HTTP headers, including the Accept and Content-Type
# Two YANG data formats (JSON and XML) work with RESTCONF
headers = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json"
}
basicauth = (os.getenv("userNAME"), os.getenv("passWORD"))

# def debug_env():
#     print("=== Environment Debug ===")
#     print(f"API_URL: {os.getenv('API_URL')}")
#     print(f"USERNAME: {os.getenv('userNAME')}")
#     print(f"PASSWORD: {os.getenv('passWORD')}")
#     print(f"Basic Auth Tuple: {(os.getenv('userNAME'), '*' * len(os.getenv('passWORD', '')) if os.getenv('passWORD') else 'None')}")
#     print("========================")


def create():
    # debug_env()
    yangConfig = {
        "ietf-interfaces:interface": {
            "name": "Loopback66070112",
            "description": "Created via RESTCONF",
            "type": "iana-if-type:softwareLoopback",
            "ietf-ip:ipv4": {
                "address": [
                    {
                        "ip": "172.1.12.1",
                        "netmask": "255.255.255.0"
                    }
                ]
            }
        }
    }

    resp = requests.post(
        api_url + "data/ietf-interfaces:interfaces",
        data=json.dumps(yangConfig),
        auth=basicauth,
        headers=headers,
        verify=False
        )

    if(resp.status_code >= 200 and resp.status_code <= 299):
        print("STATUS OK: {}".format(resp.status_code))
        return "Interface 66070112 created successfully."
    elif resp.status_code == 409:
        print('Cannot create: Interface loopback 66070112 {}'.format(resp.text))
        return "Cannot create: Interface loopback 66070112 : Interface 66070112 already exists."
    else:
        print('Error. Status Code: {}'.format(resp.status_code))
        return "Create failed."


def delete():
    resp = requests.delete(
        api_url + "data/ietf-interfaces:interfaces/interface=Loopback66070112",
        auth=basicauth,
        headers=headers,
        verify=False
        )

    if(resp.status_code >= 200 and resp.status_code <= 299):
        print("STATUS OK: {}".format(resp.status_code))
        return "Interface Loopback 66070112 deleted successfully."
    else:
        print('Error. Status Code: {}'.format(resp.status_code))
        return "Cannot delete: Interface loopback 66070112."

def enable():
    yangConfig = {
        "ietf-interfaces:interface": {
            "name": "Loopback66070112",
            "enabled": True
        }
    }

    resp = requests.patch(
        api_url + "data/ietf-interfaces:interfaces/interface=Loopback66070112",
        data=json.dumps(yangConfig),
        auth=basicauth,
        headers=headers,
        verify=False
        )

    if(resp.status_code >= 200 and resp.status_code <= 299):
        print("STATUS OK: {}".format(resp.status_code))
        return "Interface loopback 66070112 enabled successfully."
    else:
        print('Error. Status Code: {}'.format(resp.status_code))
        return "Cannot enable : Interface loopback 66070112."


def disable():
    yangConfig = {
        "ietf-interfaces:interface": {
            "name": "Loopback66070112",
            "enabled": False
        }
    }

    resp = requests.patch(
        api_url + "data/ietf-interfaces:interfaces/interface=Loopback66070112",
        data=json.dumps(yangConfig),
        auth=basicauth,
        headers=headers,
        verify=False
        )

    if(resp.status_code >= 200 and resp.status_code <= 299):
        print("STATUS OK: {}".format(resp.status_code))
        return "Interface loopback 66070112 shutdowned successfully."
    else:
        print('Error. Status Code: {}'.format(resp.status_code))
        return "Cannot shutdown : Interface loopback 66070112."


def status():
    api_ch4k_status = api_url + "data/ietf-interfaces:interfaces-state"

    resp = requests.get(
        api_ch4k_status,
        auth=basicauth,
        headers=headers,
        verify=False
        )

    if(resp.status_code >= 200 and resp.status_code <= 299):
        print("STATUS OK: {}".format(resp.status_code))

        #Used an AI to help write this part for parsing JSON response. --> Start
        response_json = resp.json()
        interfaces = response_json.get("ietf-interfaces:interfaces-state", {}).get("interface", [])
        loopback = next((i for i in interfaces if i.get("name") == "Loopback66070112"), None)

        if not loopback:
            return "No Interface loopback 66070112."

        admin_status = loopback.get("admin-status")
        oper_status = loopback.get("oper-status")

        if admin_status == 'up' and oper_status == 'up':
            return "Interface loopback 66070112 is currently enabled."
        elif admin_status == 'down' and oper_status == 'down':
            return "Interface loopback 66070112 is currently disabled."
        # <-- End

    elif(resp.status_code == 404):
        print("STATUS NOT FOUND: {}".format(resp.status_code))
        return "No Interface loopback 66070112."
    else:
        print('Error. Status Code: {}'.format(resp.status_code))
        return "Cannot get status : Interface loopback 66070112."
