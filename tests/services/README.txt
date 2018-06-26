
/tests/services/
================

Tests in this folder are those which run a subset of the manager services and
drive them via their external interfaces (i.e. the network).

If your test requires a fully running chroma instance including all the services and
agents, then it belongs in /tests/integration/ rather than here.

If your test does not involve running a standalone service process, but rather operates
on individual classes, then it belongs in /tests/unit/ rather than here.

 - John S. 2013-01-14
