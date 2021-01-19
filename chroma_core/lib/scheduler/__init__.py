# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""
Registered job scheduler plugins:
slurm_job_id, job_id, lsb_jobid, loadl_step_id, pbs_jobid, procname_uid.

Modules will be loaded dynamically as needed.
Plugins must implement fetch function as documented.
Plugins should also document the available metadata fields.
"""

import importlib
from chroma_core.services import log_register

FIELDS = ("id",)
log = log_register("metrics")


def fetch(ids):
    """Given an iterable of job ids, return an interable of associated metadata dicts.
    Ids will be unique and requested in batch whenever possible.
    Plugins are responsible for any caching necessary for performance.
    """
    for id in ids:
        yield {"id": id}


def metadata(jobid_var, field, job_ids):
    """Dispatch set of job_ids to the appropriate plugin.
    Return mapping of job_ids to the requested field.
    """
    job_ids = set(job_ids)
    try:
        module = importlib.import_module("." + jobid_var.lower(), __package__)
    except ImportError:
        log.warn("Scheduler module %s not found", jobid_var)
        return {}
    if hasattr(module, "FIELDS") and field not in module.FIELDS:
        log.warn("Scheduler module %s doesn't support field %s", jobid_var, field)
    values = getattr(module, "fetch")(job_ids)
    return dict((job_id, value[field]) for job_id, value in zip(job_ids, values) if field in value)
