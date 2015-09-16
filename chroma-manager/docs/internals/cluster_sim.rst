
cluster-sim
------------

Introduction
____________

The cluster simulator impersonates a number of chroma-agent instances, while maintaining
a consistent state for shared resources such as storage devices and the clustering (corosync)
layer.  The simulator can reflect all the interactions that the manager controls, such as
target failover.

Setup
_____

Use `setup.py develop` to get the simulator module and command line into your
virtualenv.  You will need to do this for both the agent and the simulator, because
the simulator is based on the agent components.

::
  
  (virtualenv) chroma-agent$ python setup.py develop
  (virtualenv) chroma-agent$ cd ../cluster-sim
  (virtualenv) cluster-sim$ python setup.py develop

.. warning::

    Because the simulator interacts with the manager via HTTPS, be careful what your
    `https_proxy` environment variable is set to before proceeding to the following
    sections.

Use in development
__________________

::

  (virtualenv) chroma$ cluster-sim setup --server_count 8
  (virtualenv) chroma$ cluster-sim register --username admin --password lustre

After registration, the simulator will continue running to participate in the server
setup procedure (otherwise you'd see lots of failed jobs in the manager).  You can
ctrl-c it at any time, and bring your simulated setup back to life at any time with
the `run` command.

::

  (virtualenv) chroma$ cluster-sim run

You'll notice a cluster_sim/ folder is created with some .json files in it -- this is
the state of your simulated system, which was initialized by the `setup` command.

.. note::

        The `register` command needs your REST API credentials in order to acquire
        a server registration token.  No other interaction with the REST API is done by
        the simulator.



Use in automated tests
______________________

When running `tests/integration/` you can use the cluster simulator to take the place of
real storage servers.  Use the `tests/simulator.json` configuration file (and make sure
that you have done a `setup.py develop` of the simulator so that the test code can
find the module).

For the simulator-driven mode to work, all tests must interact with the system exclusively
via the REST API and the `RemoteOperations` class.  There are specializations of this class
for physical test systems (operating via SSH) and for the simulator.


Use in benchmarking
______________________

The simulator includes a benchmark tool, which measures the performance
limits of the manager server by instantiating a simulator instance, and then
driving the manager through a series of operations (such as filesystem creations)
using the REST API.

Clearly the load that the simulator can drive on the manager is limited by
the simulator's own performance.  To get the best out of the simulator benchmark, run it
on a separate server to the manager so that they are not competing for resources.

The simulator benchmark includes adding simulated storage controllers via the
storage plugin API.  To enable this, a special simulator-specific storage plugin
is included in the manager source tree, called ``simulator_controller``.  You must
enable this plugin before running the benchmark.  On the manager server, append
'simulator_controller' to INSTALLED_STORAGE_PLUGINS in {\local_}settings, and append
'SITE_ROOT/chroma-manager/tests/plugins' to the python path.  These paths are for running
the manager in development mode (from a git tree) -- for a production mode manager, copy
the plugin from a git tree to the manager server and modify the paths appropriately.

::

  sys.path.append(os.path.join(os.path.dirname(__file__), 'tests/plugins'))
  INSTALLED_STORAGE_PLUGINS.append('simulator_controller')

Once the manager server is up and running with the plugin installed, you can run the
simulator benchmark.  The script will be in your path if you are in a virtualenv and have
run ``python setup.py develop`` in ``cluster-sim``.

The benchmark tool includes various routines, you can list them with ``--help``.  For example,
to run the ``filesystem_size_limit`` routine, simply pass it to the benchmark script as the
first argument:

::

 $ cluster-sim-benchmark filesystem_size_limit

By default, the benchmark script looks for a manager server at localhost:8000, and uses
the default development username and password.  You can customize these for use with a
production mode instance using ``--url``, ``--password`` and ``--username`` arguments.

The benchmark script will generally clean up after itself, but if some hosts or controllers
are left behind in your manager instance, you can explicitly request a cleanup by running:

::

 $ cluster-sim-benchmark reset




Implementation details
______________________

Fakes
=====

When extending the simulator to reflect new chroma features or tests, you will need to
look at the `Fake` classes.

.. autoclass:: cluster_sim.fake_devices.FakeDevices
.. autoclass:: cluster_sim.fake_server.FakeServer
.. autoclass:: cluster_sim.fake_device_plugins.FakeDevicePlugins
.. autoclass:: cluster_sim.fake_action_plugins.FakeActionPlugins
.. autoclass:: cluster_sim.fake_cluster.FakeCluster
.. autoclass:: cluster_sim.fake_client.FakeClient

ClusterSimulator
================

The overall operation of all the per-server and global classes that make up the simulator
is controlled by `ClusterSimulator`.

.. autoclass:: cluster_sim.simulator.ClusterSimulator
