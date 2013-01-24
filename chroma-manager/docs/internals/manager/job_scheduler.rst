
Job Scheduler Service
=====================

The *Job Scheduler* is the component that handles changes to the system, either initiated by
the user (i.e. via chroma_api) or detected from reports sent by chroma-agent.  It's name comes
from the central use case where an RPC comes from the API asking for the system to be in a
particular state (e.g. filesystem X should be up), and this service is responsible for
orchestrating a series of interdependent jobs to get the system into that state.

Interface
---------

.. automodule:: chroma_core.services.job_scheduler.job_scheduler_client
   :members:
   :undoc-members:

Internals
---------

.. autoclass:: chroma_core.services.job_scheduler.job_scheduler.JobScheduler

.. autoclass:: chroma_core.services.job_scheduler.job_scheduler.RunJobThread

.. autoclass:: chroma_core.services.job_scheduler.command_plan.CommandPlan
