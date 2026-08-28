BUILDER_STUB_SERVICE_NAME = "builder-stub"
BUILDER_STUB_PORT = 8080

# Started only when a params file sets `anchor_builder_definitions: true`, and must be running
# before the Anchor operators so the beacon node's first fan-out has somewhere to land.
#
# The service name and port below are load-bearing: they form the URL in
# nodes/anchor/config/builder_definitions.yml, and that exact string is what the operators sign
# as their default request-auth data.
def start(plan):
    return plan.add_service(
        name = BUILDER_STUB_SERVICE_NAME,
        description = "Starting the ePBS builder stub (receives builder preferences)",
        config = ServiceConfig(
            image = "python:3.12-alpine",
            entrypoint = ["python3"],
            cmd = ["/opt/stub/server.py"],
            files = {
                "/opt/stub": plan.upload_files("./server.py"),
            },
            ports = {
                "http": PortSpec(
                    number = BUILDER_STUB_PORT,
                    transport_protocol = "TCP",
                    application_protocol = "http",
                ),
            },
        ),
    )
