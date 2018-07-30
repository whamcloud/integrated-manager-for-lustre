# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


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
