"""L2VPN Main Module."""
import inspect
from typing import List, NamedTuple, Tuple, Type

import ncs
from ncs.application import Service
from resource_manager.id_allocator import id_read, id_request

INDENTATION = " "
USER = "admin"

LOOPBACK_ID = "1"

PW_ID_POOL = "PW_ID_POOL"
SERVICE_ID_POOL = "SERVICE_ID_POOL"
SDP_ID_POOL = "{device}_SDP_ID_POOL"
SUB_INTF_ID_POOL = "{device}_{if_size}_{if_number}_SUB_INTF_ID_POOL"
CVLAN_ID_POOL = "{device}_{if_size}_{if_number}_CVLAN_ID_POOL"
SVLAN_ID_POOL = "{device}_{if_size}_{if_number}_SVLAN_ID_POOL"


class ResourceManagerError(Exception):
    """Resource manager errors."""


class IdInfo(NamedTuple):
    """Id class for resource-manager id-allocation."""

    idname: str
    pool: str
    xpath: str
    alloc: str
    requested_id: int


def read_allocated_id(root: Type[ncs.maagic.Root], pool: str, allocation_name: str, log: Type[ncs.log.Log]) -> int:
    """Read allocated ID from specific pool."""
    log.debug("Function ##" + INDENTATION + inspect.stack()[0][3])
    try:
        allocated_id = id_read(USER, root, pool, allocation_name)
        if not allocated_id.isdigit():
            raise ResourceManagerError(allocated_id)
        log.info(f"Pool: {pool} - Allocation: {allocation_name} - Id: {allocated_id}")
    except LookupError as err:
        raise LookupError(f"\n{pool} - {allocation_name} - failed with:\n\n{err}\n") from err
    return allocated_id


def get_rm_endpoint_sdp_id_parameters(endpoint_name: str, devices: List[str]) -> List[Tuple[str, str, str]]:
    """Get endpoint sdp id pool and allocation names."""
    sdp_id_parameters: List = []
    for remote_device in devices:
        if endpoint_name != remote_device:
            sdp_pool = SDP_ID_POOL.format(device=endpoint_name)
            sdp_alloc_name = f"to_{remote_device}"
            sdp_id_parameters.append((remote_device, sdp_pool, sdp_alloc_name))
    return sdp_id_parameters


def get_rm_pe_interface_subif_id_parameters(
    elan_kpath: str, endpoint_name: str, pe_interface: Type[ncs.maagic.ListElement]
) -> Tuple[str, str]:
    """Get pe-interface subif id pool and allocation names."""
    subif_pool = SUB_INTF_ID_POOL.format(
        device=endpoint_name, if_size=pe_interface.if_size, if_number=pe_interface.if_number
    )
    subif_alloc_name = elan_kpath
    return subif_pool, subif_alloc_name


def get_rm_pe_interface_cvlan_id_parameters(
    elan_kpath: str, endpoint_name: str, pe_interface: Type[ncs.maagic.ListElement], c_vlan_id: int
) -> Tuple[str, str]:
    """Get pe-interface cvlan id pool and allocation names."""
    cvlan_pool = CVLAN_ID_POOL.format(
        device=endpoint_name, if_size=pe_interface.if_size, if_number=pe_interface.if_number
    )
    cvlan_alloc_name = elan_kpath + "_" + str(c_vlan_id)
    return cvlan_pool, cvlan_alloc_name


def get_rm_pe_interface_svlan_id_parameters(
    endpoint_name: str, pe_interface: Type[ncs.maagic.ListElement]
) -> Tuple[str, str]:
    """Get pe-interface svlan id pool and allocation names."""
    svlan_id = pe_interface.s_vlan_id
    svlan_pool = SVLAN_ID_POOL.format(
        device=endpoint_name, if_size=pe_interface.if_size, if_number=pe_interface.if_number
    )
    svlan_alloc_name = f"INTERFACE_SVLAN_ID_{svlan_id}"
    return svlan_pool, svlan_alloc_name


def get_device_loopback_ip_address(root: Type[ncs.maagic.Root],
                                   device_name: str) -> str:
    """Get device mpls loopback ip address."""
    device = root.ncs__devices.device[device_name]
    if device.platform.name == "ios-xr":
        return device.config.cisco_ios_xr__interface.Loopback[
            LOOPBACK_ID].ipv4.address.ip
    elif device.platform.name == "huawei-vrp":
        pass

def get_elan_id_info_list(elan: Type[ncs.maagic.ListElement], log: Type[ncs.log.Log]) -> List[IdInfo]:
    """Create id information list for requesting ids."""
    log.debug("Function ##" + INDENTATION + inspect.stack()[0][3])
    elan_xpath = f'/l2vpn/elan[name="{elan.name}"]'
    elan_kpath = getattr(elan, "_path")
    pw_id_alloc_name = service_id_alloc_name = elan_kpath
    id_info: List[IdInfo] = []

    devices = [endpoint.name for endpoint in elan.endpoint]

    def add_id_info(info_type, pool, alloc_name):
        id_info.append(IdInfo(info_type, pool, elan_xpath, alloc_name, -1))

    for endpoint in elan.endpoint:
        endpoint_name = endpoint.device
        for sdp_id_parameter in get_rm_endpoint_sdp_id_parameters(endpoint_name, devices):
            sdp_pool, sdp_alloc_name = sdp_id_parameter[1], sdp_id_parameter[2]
            add_id_info("sdp_id", sdp_pool, sdp_alloc_name)

        for pe_interface in endpoint.pe_interface:
            subif_pool, subif_alloc_name = get_rm_pe_interface_subif_id_parameters(
                elan_kpath, endpoint_name, pe_interface
            )
            add_id_info("subif_id", subif_pool, subif_alloc_name)

            if pe_interface.encapsulation and pe_interface.encapsulation.string in ("dot1q",):
                for c_vlan_id in pe_interface.c_vlan_id:
                    cvlan_pool, cvlan_alloc_name = get_rm_pe_interface_cvlan_id_parameters(
                        elan_kpath, endpoint_name, pe_interface, c_vlan_id
                    )
                    add_id_info("cvlan_id", cvlan_pool, cvlan_alloc_name)
            elif pe_interface.encapsulation and pe_interface.encapsulation.string in ("dot1ad", "dot1q-2tags"):
                svlan_pool, svlan_alloc_name = get_rm_pe_interface_svlan_id_parameters(endpoint_name, pe_interface)
                add_id_info("svlan_id", svlan_pool, svlan_alloc_name)

    add_id_info("pw_id", PW_ID_POOL, pw_id_alloc_name)
    add_id_info("service_id", SERVICE_ID_POOL, service_id_alloc_name)
    log.info("Resource-manager requested id list is created.")
    return id_info


# ------------------------
# SERVICE CALLBACK
# ------------------------
class ElanServiceCallback(Service):
    """Service callback handler for the elan service"""

    @Service.create
    def cb_create(self, tctx, root, service, proplist):
        """Service create callback."""
        self.log.debug("Function ##" + INDENTATION + inspect.stack()[0][3])
        self.log.info("Service create(service=", getattr(service, "_path"), ")")
        self.allocate_ids(root, service)

    def allocate_ids(self, root: Type[ncs.maagic.Root], elan: Type[ncs.maagic.ListElement]):
        """Allocate ids for elan service."""
        self.log.debug("Function ##" + INDENTATION + inspect.stack()[0][3])
        idinfos: List[IdInfo] = get_elan_id_info_list(elan, self.log)
        for idinfo in idinfos:
            id_request(
                elan,
                idinfo.xpath,
                USER,
                idinfo.pool,
                idinfo.alloc,
                False,
                idinfo.requested_id,
                alloc_sync=True,
                root=root,
            )
        self.log.info("Ids are requested from resource-manager.")

    def create_operational_nodes(self, root: Type[ncs.maagic.Root], elan: Type[ncs.maagic.ListElement]) -> None:
        """Set or create operational nodes."""
        elan_kpath = getattr(elan, "_path")
        elan_name = elan.name
        pw_id_alloc_name = service_id_alloc_name = elan_kpath
        elan.pw_id = read_allocated_id(root, PW_ID_POOL, pw_id_alloc_name, self.log)
        self.log.info(f"Elan {elan_name} operational pw-id leaf is setted.")
        elan.service_id = read_allocated_id(root, SERVICE_ID_POOL, service_id_alloc_name, self.log)
        self.log.info(f"Elan {elan_name} operational service-id leaf is setted.")

        devices = [endpoint.name for endpoint in elan.endpoint]

        for endpoint in elan.endpoint:
            endpoint_name = endpoint.device
            for remote_device, sdp_pool, sdp_alloc_name in get_rm_endpoint_sdp_id_parameters(endpoint_name, devices):
                remote_peer = endpoint.l2vpn__remote_peer.create(remote_device)
                remote_peer.sdp_id = read_allocated_id(root, sdp_pool, sdp_alloc_name, self.log)
                remote_peer.address = ""

    def apply_template(self, elan: Type[ncs.maagic.ListElement]) -> None:
        """Configure elan service on devices."""
        self.log.debug("Function ##" + INDENTATION + inspect.stack()[0][3])
        template = ncs.template.Template(elan)
        tvars = ncs.template.Variables()
        tvars.add("SERVICE_NAME", elan.name)
        tvars.add("PW_ID", elan.pw_id)
        tvars.add("MTU", elan.mtu)
        self.log.info("Template l2vpn-elan-xr|vrp-interface is started to apply.")
        template.apply("l2vpn-elan-xr-interface", tvars)
        template.apply("l2vpn-elan-vrp-interface", tvars)
        self.log.info("Template l2vpn-elan-xr|vrp-interface is applied.")
        self.log.info("Template l2vpn-elan-xr|vrp-bridge-domain is started to apply.")
        template.apply("l2vpn-elan-xr-bridge-domain", tvars)
        template.apply("l2vpn-elan-vrp-bridge-domain", tvars)
        self.log.info("Template l2vpn-elan-xr|vrp-bridge-domain is applied.")


# ---------------------------------------------
# COMPONENT THREAD THAT WILL BE STARTED BY NCS.
# ---------------------------------------------
class Main(ncs.application.Application):
    """L2vpn main class."""

    def setup(self):
        """Register service and actions."""
        self.log.info("Main RUNNING")

        # elan service egisteration
        self.register_service("elan-servicepoint", ElanServiceCallback)

    def teardown(self):
        """Teardown."""
        self.log.info("Main FINISHED")
