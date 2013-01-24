
Commands, Jobs, Steps and Actions
---------------------------------

.. epigraph::

    Or, how I stopped worrying and learned to love ambiguous naming

    -- anon


Users issue commands, which are broken down into jobs, jobs run a series of steps, and
steps running actions.  These are more or less synonymous nouns, but they do represent
a hierarchy of distinct objects.  This section aims to cast some light on this hierarchy.

Terms
_____

Command
    A user-originated expression goal for the state of the system.  Usually corresponds with
    a single mouse click in the user interface.  For example, the user might command that a
    filesystem should go down.  Commands are persisted in the database.

Job
    Individual changes to components in the system, which can depend on one another and
    happen in parallel with each other.  For example, to start a single Lustre target.  A 
    command is associated with zero or more jobs, and a job is associated with 1 or more
    commands.  A job is shared by more than one command if the commands have overlapping
    intent, for example if there is a command to start a target, and a command to start
    the target's filesystem, there will be only one 'start target' job, associated with
    both of these commands.  To extend our example, the command to start a filesystem would
    have a job for starting each target in the filesystem.  Jobs are persisted in the database,
    but always as a subclass of Job (for example StartTargetJob).

Step
    A job executes zero or more steps.  Steps happen sequentially within a job, and a step
    only runs if its predecessor succeeds.  Steps allow the manager to provide finer-grained
    feedback to the user about the progress of an individual job.  Steps are not persisted,
    but the outcome of each step run is persisted in StepResult.

Action
    A step may execute zero or more actions: these are calls out to the agent, to functions
    provided by Action Plugins.  Actions are invoked using ``AgentRpc.call``.  Actions are
    not persisted.

Example: Starting a filesystem
_______________________________

The API consumer (usually the web interface) starts a filesystem by doing a PUT to their
filesystem (say /api/filesystem/1/) which modifies the ``state`` attribute.

Part 1: in the API request handler process
==========================================

The FilesystemResource class inherits from StatefulModelResource, which handles the PUT
by calling ``Command.set_state``, passing the object (the ManagedFilesystem instance) and
the desired state (will be ``available`` to start a filesystem).

``Command.set_state`` calls ``JobSchedulerClient.command_set_state``, which in turn
uses ``JobSchedulerRpc`` to run ``JobScheduler.set_state``.

.. note::
    There is some unnecessary indirection here: it would make sense for Command.set_state
    to be replaced with direct calls to JobSchedulerClient.command_set_state.


Part 2: in the RPC handling thread of the job_scheduler service (JobSchedulerRpc)
=================================================================================

In ``JobScheduler.set_state``, ``CommandPlan.command_set_state`` is invoked to created
the ``Command`` object and any required ``Job`` objects (0 jobs are created if a the set_state
is requesting something which is already the case).  Then, ``JobScheduler._run_next`` is
called to see which jobs are ready to run (i.e. not depending on any not-yet-run jobs), and
execute them by spawning threads (RunJobThread).

The RPC handler completes, returning the ID of the created ``Command`` to the caller, while
the RunJobThread instances continue to run.  The caller can now poll the ``/api/command/``
API resource using the ID they were returned, to wait for their new ``Command`` to complete.

Part 3: in the thread for running a particular job (RunJobThread)
=================================================================

``RunJobThread`` iterates over the steps returned by the ``get_steps`` method of a Job, calling
the ``run`` method of each step, and then persisting progress information for the ``Job`` using
the ``StepResult`` model.

When all the steps are complete, ``RunJobThread`` calls back to its parent ``JobScheduler``, invoking
the ``complete_job`` method, which marks the ``Job`` as complete, for each ``Command`` associated with the Job,
if all its Jobs are complete, marks that ``Command`` as complete.  If any other Jobs were waiting
for this ``Job`` to complete, then they are started in the completion handler via another call
to ``_run_next``.
