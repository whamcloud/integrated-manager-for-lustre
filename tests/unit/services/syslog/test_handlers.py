from chroma_core.services.syslog.parser import (
    admin_client_eviction_handler,
    client_connection_handler,
    server_security_flavor_handler,
    client_eviction_handler,
)
from chroma_core.models.event import ClientConnectEvent
from tests.unit.chroma_core.helpers import synthetic_host
from tests.unit.chroma_core.helpers import load_default_profile
from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase


examples = {
    client_connection_handler: [
        {
            "lustre_pid": 5629,
            "message": " Lustre: 5629:0:(ldlm_lib.c:877:target_handle_connect()) lustre-MDT0000: connection from 26959b68-1208-1fca-1f07-da2dc872c55f@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994929 last 0",
        },
        {
            "lustre_pid": 27559,
            "message": " Lustre: 27559:0:(ldlm_lib.c:871:target_handle_connect()) lustre-OST0001: connection from 26959b68-1208-1fca-1f07-da2dc872c55f@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994930 last 0",
        },
        {
            "lustre_pid": 9150,
            "message": " Lustre: 9150:0:(ldlm_lib.c:871:target_handle_connect()) lustre-OST0000: connection from 26959b68-1208-1fca-1f07-da2dc872c55f@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994930 last 0",
        },
        {
            "lustre_pid": 31793,
            "message": " Lustre: 31793:0:(ldlm_lib.c:877:target_handle_connect()) MGS:            connection from e5232e74-1e61-fad1-b59b-6e4a7d674016@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994928 last 0",
        },
    ],
    admin_client_eviction_handler: [
        {
            "message": " Lustre: 2689:0:(genops.c:1379:obd_export_evict_by_uuid()) lustre-OST0001: evicting 26959b68-1208-1fca-1f07-da2dc872c55f at adminstrative request",
            "lustre_pid": 2689,
        }
    ],
    client_eviction_handler: [
        {
            "message": " LustreError: 0:0:(ldlm_lockd.c:356:waiting_locks_callback()) ### lock callback timer expired after 101s: evicting client at 0@lo ns: mdt-ffff8801cd5be000 lock: ffff880126f8f480/0xe99a593b682aed45 lrc: 3/0,0 mode: PR/PR res: 8589935876/10593 bits 0x3 rrc: 2 type: IBT flags: 0x4000020 remote: 0xe99a593b682aecea expref: 14 pid: 3636 timeout: 4389324308'",
            "lustre_pid": 3636,
        },
        {
            "message": " LustreError: 0:0:(ldlm_lockd.c:356:waiting_locks_callback()) ### lock callback timer expired after 151s: evicting client at 10.10.6.127@tcp ns: mdt-ffff880027554000 lock: ffff8800345b9480/0x7e9e6dc241f05651 lrc: 3/0,0 mode: PR/PR res: 8589935619/19678 bits 0x3 rrc: 2 type: IBT flags: 0x4000020 remote: 0xebc1380d8b532fd7 expref: 5104 pid: 23056 timeout: 4313115550",
            "lustre_pid": 23056,
        },
    ],
}


class TestHandlers(IMLUnitTestCase):
    def setUp(self):
        super(TestHandlers, self).setUp()
        load_default_profile()
        self.host = synthetic_host("myaddress")

    def test_server_security_flavor_handler(self):
        ssfh_examples = [
            {
                "message": " Lustre: 5629:0:(sec.c:1474:sptlrpc_import_sec_adapt()) import lustre-MDT0000->NET_0x20000c0a87ada_UUID netid 20000: select flavor null"
            },
            {
                "message": "Lustre: 20380:0:(sec.c:1474:sptlrpc_import_sec_adapt()) import MGC192.168.122.105@tcp->MGC192.168.122.105@tcp_0 netid 20000: select flavor null"
            },
        ]
        # These will not create events, but should also not raise exceptions
        for example in ssfh_examples:
            server_security_flavor_handler(example["message"], None)

        # TODO: test doing a client connection and then one of these, to see it get correlated

    def test_client_connection_handler(self):
        for example in examples[client_connection_handler]:
            client_connection_handler(example["message"], self.host)
            event = ClientConnectEvent.objects.latest("id")
            self.assertEqual(event.lustre_pid, example["lustre_pid"])

    def test_admin_client_eviction_handler(self):
        for example in examples[admin_client_eviction_handler]:
            admin_client_eviction_handler(example["message"], self.host)
            event = ClientConnectEvent.objects.latest("id")
            self.assertEqual(event.lustre_pid, example["lustre_pid"])

    def test_client_eviction_handler(self):
        for example in examples[client_eviction_handler]:
            client_eviction_handler(example["message"], self.host)
            event = ClientConnectEvent.objects.latest("id")
            self.assertEqual(event.lustre_pid, example["lustre_pid"])
