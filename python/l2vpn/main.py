"""L2VPN Main Module."""
import ncs
from ncs.application import Service


# ------------------------
# SERVICE CALLBACK
# ------------------------
class ElanServiceCallback(Service):
    """Service callback handler for the elan service"""

    @Service.create
    def cb_create(self, tctx, root, service, proplist):
        """Service create callback."""
        self.log.info("Service create(service=", getattr(service, "_path"), ")")
        template = ncs.template.Template(service)
        tvars = ncs.template.Variables()
        tvars.add("SERVICE_NAME", service.name)
        tvars.add("PW_ID", service.pw_id)
        tvars.add("MTU", service.mtu)
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
