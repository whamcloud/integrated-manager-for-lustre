#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydraapi.requesthandler import RequestHandler


class Handler(RequestHandler):
    def get(self, request, id = None, recent = False):
        """Return a list of dicts representing Jobs, or a single dict if 'id' is specified.
           If the 'recent' parameter is set, return jobs which are incomplete or which ran in the last hour"""
        from chroma_core.models import Job
        from datetime import timedelta, datetime
        from django.db.models import Q

        # TODO: paginated version of this call will be needed
        filter_args = []
        filter_kwargs = {}
        if recent:
            # FIXME: 'recent' is a hack for the benefit of dumb UI sidebar code
            filter_args.append(~Q(state = 'complete') | Q(created_at__gte=datetime.now() - timedelta(hours=24)))

        jobs = Job.objects.filter(*filter_args, **filter_kwargs).order_by('-created_at')
        return [j.to_dict() for j in jobs]

    def put(self, request, id):
        """Modify a Job (setting 'state' field to 'pause', 'cancel', or 'resume' is the
        only allowed input e.g. {'state': 'pause'}"""
        # FIXME: 'resume' isn't actually a state that job will ever have,
        # it causes a paused job to bounce back into a state like 'pending' or 'tasked'
        # - there should be a better way of representing this operation
        new_state = request.data['state']

        assert new_state in ['pause', 'cancel', 'resume']
        from django.shortcuts import get_object_or_404
        from chroma_core.models import Job
        job = get_object_or_404(Job, id = id).downcast()
        if new_state == 'pause':
            job.pause()
        elif new_state == 'cancel':
            job.cancel()
        else:
            job.resume()

        return job.to_dict()
