
from tests.unit.chroma_core.helper import JobTestCaseWithHost, set_state


class TestFSTransitions(JobTestCaseWithHost):
    def setUp(self):
        super(TestFSTransitions, self).setUp()

        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem
        self.mgt = ManagedMgs.create_for_volume(self._test_lun(self.host).id, name = "MGS")
        self.fs = ManagedFilesystem.objects.create(mgs = self.mgt, name = "testfs")
        self.mdt = ManagedMdt.create_for_volume(self._test_lun(self.host).id, filesystem = self.fs)
        self.ost = ManagedOst.create_for_volume(self._test_lun(self.host).id, filesystem = self.fs)

        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'unformatted')
        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'unformatted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'unformatted')

        set_state(self.fs, 'available')

        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'mounted')
        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'mounted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'mounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'available')

    def test_mgs_removal(self):
        """Test that removing an MGS takes the filesystems with it"""
        set_state(self.mgt, 'removed')

    def test_fs_removal(self):
        """Test that removing a filesystem takes its targets with it"""
        from chroma_core.models import ManagedMdt, ManagedOst, ManagedFilesystem
        set_state(self.fs, 'removed')

        with self.assertRaises(ManagedMdt.DoesNotExist):
            ManagedMdt.objects.get(pk = self.mdt.pk)
        self.assertEqual(ManagedMdt._base_manager.get(pk = self.mdt.pk).state, 'removed')
        with self.assertRaises(ManagedOst.DoesNotExist):
            ManagedOst.objects.get(pk = self.ost.pk)
        self.assertEqual(ManagedOst._base_manager.get(pk = self.ost.pk).state, 'removed')
        with self.assertRaises(ManagedFilesystem.DoesNotExist):
            ManagedFilesystem.objects.get(pk = self.fs.pk)

    def test_target_stop(self):
        from chroma_core.models import ManagedMdt, ManagedFilesystem
        set_state(self.mdt, 'unmounted')
        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'unmounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'unavailable')

    def test_target_start(self):
        from chroma_core.models import ManagedMdt, ManagedOst, ManagedFilesystem

        set_state(self.fs, 'stopped')
        set_state(self.mdt, 'mounted')

        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'mounted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'unmounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'stopped')

    def test_stop_start(self):
        from chroma_core.models import ManagedMdt, ManagedOst, ManagedFilesystem
        set_state(self.fs, 'stopped')

        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'unmounted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'unmounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'stopped')

        set_state(self.fs, 'available')

        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'mounted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'mounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'available')
