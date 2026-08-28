"""Minimal ePBS builder stub: receives builder preferences and logs them.

Stands in for a real builder (ethpandaops/buildoor) so a local enclave can observe the last hop
of the Gloas direct-builder flow: validator client -> beacon node -> builder. It implements only
what the beacon node calls during preference submission, per builder-specs #165 / beacon-APIs #630:

    POST /eth/v1/builder/builder_preferences/{validator_pubkey}   -> 202 Accepted

202 is the ONLY status the Lighthouse builder client treats as success, so every other code, 200
included, is a failure on its side.

Deliberately NOT a builder: it serves no bids and signs nothing, so block production still falls
back to the local or p2p payload. It also does not verify the BLS signature on the request auth;
that check belongs to buildoor, whose ethereum-package launcher is currently too old to run any
buildoor build new enough to implement this endpoint. What it does give is the full submitted
payload on stdout, which is what proves the preference was published ahead of time, for which
proposer, and with which auth data.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PREFERENCES_PREFIX = "/eth/v1/builder/builder_preferences/"


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""

        if not self.path.startswith(PREFERENCES_PREFIX):
            print("UNEXPECTED POST path=%s" % self.path, flush=True)
            self.send_response(404)
            self.end_headers()
            return

        pubkey = self.path[len(PREFERENCES_PREFIX):]
        version = self.headers.get("Eth-Consensus-Version")
        try:
            payload = json.loads(body)
            auth = (payload.get("auth") or {}).get("message") or {}
            prefs = payload.get("preferences") or {}
            print(
                "PREFERENCE ACCEPTED pubkey=%s slot=%s auth_data=%s max_execution_payment=%s version=%s"
                % (
                    pubkey,
                    auth.get("slot"),
                    auth.get("data"),
                    prefs.get("max_execution_payment"),
                    version,
                ),
                flush=True,
            )
        except (ValueError, AttributeError) as err:
            # Still 202: the point of the stub is to observe delivery, and failing here would make
            # a parsing quirk look like a delivery failure on the beacon-node side.
            print(
                "PREFERENCE UNPARSEABLE pubkey=%s version=%s err=%s body=%r"
                % (pubkey, version, err, body[:400]),
                flush=True,
            )

        self.send_response(202)
        self.end_headers()

    def do_GET(self):
        # Bid requests land here during block production. Refusing them is correct for a stub:
        # the proposal falls back to the local or p2p payload, which is the no-builder behaviour.
        print("UNEXPECTED GET path=%s" % self.path, flush=True)
        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt, *args):
        # Silence the default per-request access log; the lines above are the signal.
        pass


if __name__ == "__main__":
    # THREADING is required, not a nicety. The beacon node fans out to builders concurrently
    # (join_all over the entries) with a 1s per-submission timeout
    # (DEFAULT_SUBMIT_TIMEOUT_MILLIS). A single-threaded HTTPServer serialises those requests, so
    # a batch of ~6 or more times out on the beacon-node side even though the stub logged and
    # accepted every one. The validator client then treats the whole chunk as failed, marks none
    # of it sent, and re-sends it, which shows up as duplicate deliveries and looks exactly like a
    # dedup bug in Anchor. Observed on the 2026-08-27 run before this was threaded.
    print("builder stub listening on 0.0.0.0:8080", flush=True)
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
