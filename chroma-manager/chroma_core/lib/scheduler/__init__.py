#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


"""
Registered job scheduler plugins.
slurm_job_id, job_id, lsb_jobid, loadl_step_id, pbs_jobid, procname_uid

Modules will be loaded dynamically as needed.
Plugins must implement fetch function as documented.
Plugins should also document the available metadata fields.
"""

import importlib
from chroma_core.services import log_register

FIELDS = 'id',
log = log_register('metrics')


def fetch(ids):
    """Given an iterable of job ids, return an interable of associated metadata dicts.
    Ids will be unique and requested in batch whenever possible.
    Plugins are responsible for any caching necessary for performance.
    """
    for id in ids:
        yield {'id': id}


def metadata(jobid_var, field, job_ids):
    """Dispatch set of job_ids to the appropriate plugin.
    Return mapping of job_ids to the requested field.
    """
    job_ids = set(job_ids)
    try:
        module = importlib.import_module('.' + jobid_var.lower(), __package__)
    except ImportError:
        log.warn("Scheduler module %s not found", jobid_var)
        return {}
    if hasattr(module, 'FIELDS') and field not in module.FIELDS:
        log.warn("Scheduler module %s doesn't support field %s", jobid_var, field)
    values = getattr(module, 'fetch')(job_ids)
    return dict((job_id, value[field]) for job_id, value in zip(job_ids, values) if field in value)
