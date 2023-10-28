import logging
import re
import typing
from pathlib import Path

from . import utils

logger = logging.getLogger(__name__)


def get_interfaces() -> typing.Dict[str, dict]:
    ifaces: typing.Dict[str, dict] = {}
    second_pass_ifaces: typing.List[typing.Dict[str, str]] = []
    vlan_ifaces: typing.List[str] = utils.get_vlan_interfaces()

    # First pass - process the detected physical interfaces
    for iface_name in utils.get_ifaces():
        iface_path: Path = utils.inject_file_root("sys/class/net", iface_name)
        iface_abspath: Path = iface_path.resolve()
        iface_path_str = str(iface_abspath)
        iface_type = utils.find_iface_type(iface_name)
        macaddr = utils.get_first_line(iface_path / "address").strip()

        if "15100000.ethernet" in iface_path_str and "eth1" in iface_path_str:
            # LAN port
            utils.append_iface(ifaces, iface_name, "eth", "eth", "LAN", macaddr)
        elif "15100000.ethernet" in iface_path_str and "eth0" in iface_path_str:
            # WAN port
            utils.append_iface(ifaces, iface_name, "eth", "eth", "WAN", macaddr)
        elif "18000000.wifi" in iface_path_str:
            if "-sta" in iface_path_str:
                if_type = "wwan"
            else:
                if_type = "wifi"

            if "phy0-" in iface_path_str:
                label = "2G"
            else:
                label = "5G"

            utils.append_iface(ifaces, iface_name, if_type, "pci", label, macaddr)
        elif "virtual" in iface_path_str:
            # virtual ifaces (loopback, bridges, ...) - we don't care about these
            #
            # `utils.get_ifaces` can return interfaces in random order, so interfaces with VLAN assigned
            # will be processed in second pass to ensure that its parent interface exists and is already processed.
            if iface_name in vlan_ifaces:
                second_pass_ifaces.append({"name": iface_name, "macaddr": macaddr})
        else:
            logger.warning("unknown interface type: %s", iface_name)

    # Second pass - process virtual interfaces with VLAN assigned.
    utils.process_vlan_interfaces(ifaces, second_pass_ifaces)

    return ifaces
