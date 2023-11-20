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
