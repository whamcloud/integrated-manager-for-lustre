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


from django.db import transaction
from django.middleware.transaction import TransactionMiddleware
from tastypie import http


class TastypieTransactionMiddleware(TransactionMiddleware):
    """

    HYD-813
    Cope with tastypie's behaviour of serializing exceptions
    for the benefit of the client: this doesn't look like an
    error to stock TransactionMiddleware so we have to customize it.

    https://github.com/toastdriven/django-tastypie/issues/85
    """

    def process_response(selfself, request, response):
        if transaction.is_managed():
            if transaction.is_dirty():
                successful = not isinstance(response, http.HttpApplicationError)
                if successful:
                    transaction.commit()
                else:
                    transaction.rollback()

            transaction.leave_transaction_management()

        return response
