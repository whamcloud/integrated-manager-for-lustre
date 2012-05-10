from chroma_core.models import Systemevents
from chroma_core.models.event import ClientConnectEvent
from tests.unit.chroma_core.helper import JobTestCaseWithHost


class TestHandlers(JobTestCaseWithHost):
    def test_server_security_flavor_handler(self):
        from chroma_core.lib.systemevents import server_security_flavor_handler

        examples = [" Lustre: 5629:0:(sec.c:1474:sptlrpc_import_sec_adapt()) import lustre-MDT0000->NET_0x20000c0a87ada_UUID netid 20000: select flavor null",
         "Lustre: 20380:0:(sec.c:1474:sptlrpc_import_sec_adapt()) import MGC192.168.122.105@tcp->MGC192.168.122.105@tcp_0 netid 20000: select flavor null"]

        # These will not create events, but should also not raise exceptions
        for example in examples:
            server_security_flavor_handler(Systemevents.objects.create(message=example), None)

        # TODO: test doing a client connection and then one of these, to see it get correlated

    def test_client_connection_handler(self):
        from chroma_core.lib.systemevents import client_connection_handler

        examples = [
            {
            "lustre_pid": 5629,
            "message": " Lustre: 5629:0:(ldlm_lib.c:877:target_handle_connect()) lustre-MDT0000: connection from 26959b68-1208-1fca-1f07-da2dc872c55f@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994929 last 0"
            },
            {
            "lustre_pid": 27559,
            "message": " Lustre: 27559:0:(ldlm_lib.c:871:target_handle_connect()) lustre-OST0001: connection from 26959b68-1208-1fca-1f07-da2dc872c55f@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994930 last 0"
            },
            {
            "lustre_pid": 9150,
            "message": " Lustre: 9150:0:(ldlm_lib.c:871:target_handle_connect()) lustre-OST0000: connection from 26959b68-1208-1fca-1f07-da2dc872c55f@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994930 last 0"
            },
            {
            "lustre_pid": 31793,
            "message": " Lustre: 31793:0:(ldlm_lib.c:877:target_handle_connect()) MGS:            connection from e5232e74-1e61-fad1-b59b-6e4a7d674016@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994928 last 0"
            }
        ]

        for example in examples:
            client_connection_handler(Systemevents.objects.create(message=example['message']), self.host)
            event = ClientConnectEvent.objects.latest('id')
            self.assertEqual(event.lustre_pid, example['lustre_pid'])

    def test_admin_client_eviction_handler(self):
        from chroma_core.lib.systemevents import admin_client_eviction_handler

        examples = [
            {
                'message': " Lustre: 2689:0:(genops.c:1379:obd_export_evict_by_uuid()) lustre-OST0001: evicting 26959b68-1208-1fca-1f07-da2dc872c55f at adminstrative request",
                'lustre_pid': 2689
            }
        ]

        for example in examples:
            admin_client_eviction_handler(Systemevents.objects.create(message=example['message']), self.host)
            event = ClientConnectEvent.objects.latest('id')
            self.assertEqual(event.lustre_pid, example['lustre_pid'])

    def test_client_eviction_handler(self):
        from chroma_core.lib.systemevents import client_eviction_handler

        examples = [
            {
                'message': " LustreError: 0:0:(ldlm_lockd.c:356:waiting_locks_callback()) ### lock callback timer expired after 101s: evicting client at 0@lo ns: mdt-ffff8801cd5be000 lock: ffff880126f8f480/0xe99a593b682aed45 lrc: 3/0,0 mode: PR/PR res: 8589935876/10593 bits 0x3 rrc: 2 type: IBT flags: 0x4000020 remote: 0xe99a593b682aecea expref: 14 pid: 3636 timeout: 4389324308'",
                'lustre_pid': 3636
            }
        ]

        for example in examples:
            client_eviction_handler(Systemevents.objects.create(message=example['message']), self.host)
            event = ClientConnectEvent.objects.latest('id')
            self.assertEqual(event.lustre_pid, example['lustre_pid'])
