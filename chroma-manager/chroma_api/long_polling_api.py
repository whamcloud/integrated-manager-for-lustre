#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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

import json

from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpNotModified

from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from chroma_core.services import log_register

import settings

log = log_register(__name__)


class LongPollingAPI(object):
    long_polling_tables = None                  # The caller must declare a set of long polling tables.

    def handle_long_polling_dispatch(self, request_type, request, **kwargs):
        long_poll_timestamp_seconds = None

        if (self.long_polling_tables is not None) and (request.method.lower() in ['get']):
            log.debug("Long Polling Request: %s" % request.GET)

            # Allow 2 methods so it can be test easily in a browser. Don't us 'last_modified' in request.GET below
            # because QueryDict's seem to not implement in as we would expect.
            if request.GET.get('last_modified') is not None:
                long_poll_timestamp_seconds = int(request.GET['last_modified'])
            elif request.META.get('HTTP_IF_NONE_MATCH') is not None:
                long_poll_timestamp_seconds = int(request.META['HTTP_IF_NONE_MATCH'])

        if long_poll_timestamp_seconds is not None:
            lp_timestamp = JobSchedulerClient.wait_table_change(long_poll_timestamp_seconds,
                                                                [table._meta.db_table for table in self.long_polling_tables],
                                                                settings.LONG_POLL_TIMEOUT_SECONDS)

            if lp_timestamp:
                # We want the super of the thing that called us, because it might have other overloads
                response = super(self.__class__, self).dispatch(request_type, request, **kwargs)

                if request.GET.get('last_modified') is not None:
                    # Expensive but reliable method, this is only used when a user types from a browser
                    # and only works for json, but that is all we support and the real method is the ETag
                    content_data = json.loads(response.content)
                    content_data['meta']['last_modified'] = lp_timestamp
                    response.content = json.dumps(content_data)

                response['ETag'] = lp_timestamp

                log.debug("Long Polling response: %s\n" % response)
            else:
                raise ImmediateHttpResponse(HttpNotModified("Timeout waiting for data change"))
        else:
            # We want the super of the thing that called us, because it might have other overloads
            response = super(self.__class__, self).dispatch(request_type, request, **kwargs)

        return response
