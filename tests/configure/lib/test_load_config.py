
from test_state_manager import JobTestCase


class TestJsonImport(JobTestCase):
    mock_servers = {
            'example01': {
                'fqdn': 'example01.mycompany.com',
                'nids': ["192.168.0.1@tcp"]
            },
            'example02': {
                'fqdn': 'example02.mycompany.com',
                'nids': ["192.168.0.2@tcp"]
            }
    }

    def test_import(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "../../sample_data/example.json")
        from configure.lib.load_config import load_file
        load_file(path)

        from configure.models import ManagedHost
        example01 = ManagedHost.objects.get(address = 'example01')
        example02 = ManagedHost.objects.get(address = 'example02')

        from configure.models import ManagedFilesystem, ManagedMgs, ManagedMdt, ManagedOst
        from configure.models import ManagedTargetMount

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
