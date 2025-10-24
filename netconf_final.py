import os
from contextlib import contextmanager
from typing import Optional

from ncclient import manager
import xmltodict


netconf_host = ""
NETCONF_PORT = 830
NETCONF_USERNAME = os.getenv("userNAME")
NETCONF_PASSWORD = os.getenv("passWORD")


@contextmanager
def _connect(host: Optional[str] = None):
    target_host = host or netconf_host
    if not target_host:
        raise ValueError("NETCONF host is not specified.")

    with manager.connect(
        host=target_host,
        port=NETCONF_PORT,
        username=NETCONF_USERNAME,
        password=NETCONF_PASSWORD,
        hostkey_verify=False,
        allow_agent=False,
        look_for_keys=False,
        timeout=30,
    ) as connection:
        yield connection


def create(host: Optional[str] = None):
    netconf_config = """
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>Loopback66070112</name>
      <description>Created via NETCONF</description>
      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:softwareLoopback</type>
      <enabled>true</enabled>
      <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip">
        <address>
          <ip>172.1.12.1</ip>
          <netmask>255.255.255.0</netmask>
        </address>
      </ipv4>
    </interface>
  </interfaces>
</config>
"""

    try:
        with _connect(host) as connection:
            reply = connection.edit_config(target="running", config=netconf_config)
        print(reply.xml)
        if "<ok/>" in reply.xml:
            return "Interface 66070112 created successfully by using Netconf."
        return "Create failed using Netconf."
    except Exception as exc:
        print(f"NETCONF create error: {exc}")
        return "Create failed using Netconf."


def delete(host: Optional[str] = None):
    netconf_config = """
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" nc:operation="delete">
      <name>Loopback66070112</name>
    </interface>
  </interfaces>
</config>
"""

    try:
        with _connect(host) as connection:
            reply = connection.edit_config(target="running", config=netconf_config)
        print(reply.xml)
        if "<ok/>" in reply.xml:
            return "Interface Loopback 66070112 deleted successfully using Netconf."
        return "Cannot delete: Interface loopback 66070112 using Netconf."
    except Exception as exc:
        print(f"NETCONF delete error: {exc}")
        return "Cannot delete: Interface loopback 66070112 using Netconf."


def enable(host: Optional[str] = None):
    netconf_config = """
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>Loopback66070112</name>
      <enabled>true</enabled>
    </interface>
  </interfaces>
</config>
"""

    try:
        with _connect(host) as connection:
            reply = connection.edit_config(target="running", config=netconf_config)
        print(reply.xml)
        if "<ok/>" in reply.xml:
            return "Interface loopback 66070112 enabled successfully (check by Netconf)."
        return "Cannot enable : Interface loopback 66070112 (check by Netconf)."
    except Exception as exc:
        print(f"NETCONF enable error: {exc}")
        return "Cannot enable : Interface loopback 66070112 (check by Netconf)."


def disable(host: Optional[str] = None):
    netconf_config = """
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>Loopback66070112</name>
      <enabled>false</enabled>
    </interface>
  </interfaces>
</config>
"""

    try:
        with _connect(host) as connection:
            reply = connection.edit_config(target="running", config=netconf_config)
        print(reply.xml)
        if "<ok/>" in reply.xml:
            return "Interface loopback 66070112 shutdowned successfully (check by Netconf)."
        return "Cannot shutdown : Interface loopback 66070112 (check by Netconf)."
    except Exception as exc:
        print(f"NETCONF disable error: {exc}")
        return "Cannot shutdown : Interface loopback 66070112 (check by Netconf)."


def status(host: Optional[str] = None):
    netconf_filter = """
<filter>
  <interfaces-state xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>Loopback66070112</name>
    </interface>
  </interfaces-state>
</filter>
"""

    try:
        with _connect(host) as connection:
            reply = connection.get(filter=netconf_filter)
        print(reply.xml)
        reply_dict = xmltodict.parse(reply.xml)

        interfaces_state = reply_dict.get("rpc-reply", {}).get("data", {}).get("interfaces-state", {})
        interface = interfaces_state.get("interface")

        if not interface:
            return "No Interface loopback 66070112 (check by Netconf)."

        if isinstance(interface, list):
            interface = next((item for item in interface if item.get("name") == "Loopback66070112"), None)

        if not interface:
            return "No Interface loopback 66070112 (check by Netconf)."

        admin_status = interface.get("admin-status")
        oper_status = interface.get("oper-status")

        if admin_status == "up" and oper_status == "up":
            return "Interface loopback 66070112 is currently enabled (check by Netconf)."
        if admin_status == "down" and oper_status == "down":
            return "Interface loopback 66070112 is currently disabled (check by Netconf)."
        return "Cannot get status : Interface loopback 66070112 (check by Netconf)."
    except Exception as exc:
        print(f"NETCONF status error: {exc}")
        return "Cannot get status : Interface loopback 66070112 (check by Netconf)."
