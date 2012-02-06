
from tests.unit.chroma_core.helper import JobTestCase


class TestJsonImport(JobTestCase):
    mock_servers = {
            'example01': {
                'fqdn': 'example01.mycompany.com',
                'nodename': 'test01.example01.mycompany.com',
                'nids': ["192.168.0.1@tcp"]
            },
            'example02': {
                'fqdn': 'example02.mycompany.com',
                'nodename': 'test02.example02.mycompany.com',
                'nids': ["192.168.0.2@tcp"]
            }
    }

    def test_export(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "../../../sample_data/example.json")
        from chroma_core.lib.load_config import load_file, save_filesystems
        load_file(path)

        str = save_filesystems(['egfs'])
        import json
        self.maxDiff = None

        saved = json.loads(str)
        saved['hosts'] = saved['hosts'].sort(key = lambda h: h['address'])

        loaded = json.loads(open(path, 'r').read())
        loaded['hosts'] = loaded['hosts'].sort(key = lambda h: h['address'])

        # NB this comparison requires that where there are lists in the
        # output they are put into deterministic order
        self.assertDictEqual(saved, loaded)

    def test_import(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "../../../sample_data/example.json")
        from chroma_core.lib.load_config import load_file
        load_file(path)

        from chroma_core.models import ManagedHost
        example01 = ManagedHost.objects.get(address = 'example01')
        example02 = ManagedHost.objects.get(address = 'example02')

        from chroma_core.models import ManagedFilesystem, ManagedMgs, ManagedMdt, ManagedOst
        from chroma_core.models import ManagedTargetMount

        ManagedFilesystem.objects.get(name = 'egfs')
        mgs = ManagedMgs.objects.get()
        self.assertEqual(ManagedTargetMount.objects.get(target = mgs, host = example01).primary, True)
        self.assertEqual(ManagedTargetMount.objects.get(target = mgs, host = example02).primary, False)
        mdt = ManagedMdt.objects.get()
        self.assertEqual(ManagedTargetMount.objects.get(target = mdt, host = example01).primary, True)
        self.assertEqual(ManagedTargetMount.objects.get(target = mdt, host = example02).primary, False)

        ost = ManagedOst.objects.get()
        self.assertEqual(ManagedTargetMount.objects.get(target = ost, host = example01).primary, True)
        self.assertEqual(ManagedTargetMount.objects.get(target = ost, host = example02).primary, False)

        # Try loading it again, it should succeed but do nothing.
        load_file(path)
        self.assertEqual(ManagedHost.objects.count(), 2)
        # (Using .get() to check there's still only 1 of everything)
        ManagedFilesystem.objects.get()
        mgs = ManagedMgs.objects.get()
        mdt = ManagedMdt.objects.get()
        ost = ManagedOst.objects.get()
