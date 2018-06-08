-- polytest/models.py --
from polymorphic.models import *

from django.db import connection
def queries():
  print len(connection.queries)
  connection.queries = []

class Base(models.Model):
  __metaclass__ = PolymorphicMetaclass

class Derived(Base):
  pass

class DowncastBase(models.Model):
  __metaclass__ = DowncastMetaclass

class DowncastDerived(DowncastBase):
  pass 


>>> from polytest.models import *

>>> ### Example1: PolymorphicMetaclass (queries return base class objects, which can be downcast())

>>> Derived().save()
>>> queries()
4

>>> Base.objects.all()
[<Base: Base object>]
>>> queries()
1

>>> Base.objects.all()[0].downcast()
<Derived: Derived object>
>>> queries()
3

>>> ### Example2: DowncastMetaclass (queries automatically downcast all objects)
 
>>> DowncastDerived().save()
>>> queries()
4

>>> DowncastBase.objects.all()
[<DowncastDerived: DowncastDerived object>]
>>> queries()
3

>>> ### Example3: Comparing queries with multiple objects in result

>>> [Derived().save() for i in range(9)]
[None, None, None, None, None, None, None, None, None]
>>> queries()
27

>>> Base.objects.all()
[<Base: Base object>, <Base: Base object>, <Base: Base object>, <Base: Base object>, <Base: Base object>, <Base: Base object>, <Base: Base object>, <Base: Base object>, <Base: Base object>, <Base: Base object>]
>>> queries()
1

>>> [DowncastDerived().save() for i in range(9)]
[None, None, None, None, None, None, None, None, None]
>>> queries()
27

>>> DowncastBase.objects.all()
DowncastBase.objects.all()
[<DowncastDerived: DowncastDerived object>, <DowncastDerived: DowncastDerived object>, <DowncastDerived: DowncastDerived object>, <DowncastDerived: DowncastDerived object>, <DowncastDerived: DowncastDerived object>, <DowncastDerived: DowncastDerived object>, <DowncastDerived: DowncastDerived object>, <DowncastDerived: DowncastDerived object>, <DowncastDerived: DowncastDerived object>, <DowncastDerived: DowncastDerived object>]
>>> queries()
21

