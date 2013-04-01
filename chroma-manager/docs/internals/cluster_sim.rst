
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
  (virtualenv) chroma$ cluster-sim register --username debug --password chr0m4_d3bug

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

To run benchmarking against the simulator, first ensure the simulator_controller plugin is loaded.
Append 'simulator_controller' to INSTALLED_STORAGE_PLUGINS in {\local_}settings,
and append 'SITE_ROOT/chroma-manager/tests/plugins' to the python path.

::

  sys.path.append(os.path.join(os.path.dirname(__file__), 'tests/plugins'))
  INSTALLED_STORAGE_PLUGINS = [..., 'simulator_controller']

Configure the simulator with 0 servers, skipping the register step as there are no servers to register.
The benchmark process will add servers itself as necesary.

::

  (virtualenv) chroma$ cluster-sim setup --server_count 0
  (virtualenv) chroma$ cluster-sim run

Then begin the benchmarking in a separate shell.  See the help for various limit commands,
and note the reset command is also handy for cleaning up the database, e.g., removing hosts.

::

  (virtualenv) chroma$ cluster-sim-benchmark {reset,filesystem_size_limit,...}


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
