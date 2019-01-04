# import mock

from django.db import models
from django.test import TestCase
from django.db import connection
from django.utils.unittest import skip


from chroma_core.models import SparseModel


# class TestSparseBase(SparseModel):
#     is_sparse_base = True
#     table_name = 'chroma_core.'
#
#
# class TestSparseChild1(SparseModel):
#     class Meta:
#         app_label = 'chroma_core'
#         db_table = TestSparseBase.table_name
#     pass
#
#
# class TestSparseChild2(SparseModel):
#     pass


@skip("Skip until we write these")
class TestSparseModel(TestCase):
    class MockModel:
        pass

    def setUp(self):
        models.Model = self.MockModel
        pass

    def tearDown(self):
        pass
        connection.use_debug_cursor = False

    def no_test_creation(self):
        sparse_base = self.TestSparseChild1()
        self.assertEqual(type(sparse_base), self.TestSparseChild1)

        sparse_child1 = SparseModel(self.TestSparseChild1.__class__.__name__)
        self.assertEqual(type(sparse_child1), self.TestSparseChild1)

        sparse_child1 = SparseModel(self.TestSparseChild2.__class__.__name__)
        self.assertEqual(type(sparse_child1), self.TestSparseChild2)
