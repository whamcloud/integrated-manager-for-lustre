#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import threading
import sys
import traceback
from django.db import transaction
from chroma_core.lib.job import job_log
import dateutil.parser


class SerializedCalls(object):
    @classmethod
    def call(cls, fn_name, *args, **kwargs):
        from chroma_core.lib.state_manager import StateManager
        with transaction.commit_manually():
            transaction.commit()

        with transaction.commit_on_success():
            sm = StateManager()
            fn = getattr(sm, fn_name)
            return fn(*args, **kwargs)


class RunJobThread(threading.Thread):
    def __init__(self, job_id):
        super(RunJobThread, self).__init__()
        self.job_id = job_id

    def run(self):
        job_log.info("Job %d: run_job" % self.job_id)

        from chroma_core.models import Job, StepResult
        job = Job.objects.get(pk = self.job_id)

        # This can happen if we lose power after calling .complete but before returning,
        # celery will re-call our unfinished task.  Everything has already been done, so
        # just return to let celery drop the task.
        if job.state == 'complete':
            return None

        job = job.downcast()
        try:
            steps = job.get_steps()
        except Exception, e:
            job_log.error("Job %d run_steps encountered an error" % job.id)
            exc_info = sys.exc_info()
            job_log.error('\n'.join(traceback.format_exception(*(exc_info or sys.exc_info()))))
            complete_job(job, errored = True)
            return None

        if job.started_step:
            job_log.warning("Job %d restarting, started, finished=%s,%s" % (job.id, job.started_step, job.finished_step))
            if job.started_step != job.finished_step:
                step_klass, step_args = steps[job.started_step]
                if step_klass.idempotent:
                    job_log.info("Job %d step %d will be re-run (it is idempotent)" % (job.id, job.started_step))
                else:
                    job_log.error("Job %d step %d is dirty and cannot be re-run (it is not idempotent, marking job errored." % (job.id, job.started_step))
                    complete_job(job, errored = True)
                    return None
            else:
                job_log.info("Job %d will re-start from step %d" % (job.id, job.started_step + 1))

            # If we're picking up after a previous run crashed, go back and mark
            # any incomplete StepResults as complete.
            job.stepresult_set.filter(state = 'incomplete').update(state = 'crashed')

        step_index = 0
        finish_step = -1
        while step_index < len(steps):
            job.started_step = step_index
            job.save()
            klass, args = steps[step_index]

            result = StepResult(
                step_klass = klass,
                args = args,
                step_index = step_index,
                step_count = len(steps),
                job = job)
            result.save()

            step = klass(job, args, result)

            from chroma_core.lib.agent import AgentException
            try:
                job_log.debug("Job %d running step %d" % (job.id, step_index))
                step.run(args)
                job_log.debug("Job %d step %d successful" % (job.id, step_index))

                result.state = 'success'
            except AgentException, e:
                job_log.error("Job %d step %d encountered an agent error" % (job.id, step_index))
                complete_job(job, errored = True)

                result.backtrace = e.agent_backtrace
                # Don't bother storing the backtrace to invoke_agent, the interesting part
                # is the backtrace inside the AgentException
                result.state = 'failed'
                result.save()

                return None

            except Exception:
                job_log.error("Job %d step %d encountered an error" % (job.id, step_index))
                exc_info = sys.exc_info()
                backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
                job_log.error(backtrace)
                complete_job(job, errored = True)

                result.backtrace = backtrace
                result.state = 'failed'
                result.save()

                return None
            finally:
                result.save()

            finish_step = step_index
            step_index += 1

        job_log.info("Job %d finished %d steps successfully" % (job.id, finish_step + 1))
        complete_job(job, errored = False)

        return None


def run_next():
    from chroma_core.models.jobs import Job
    runnable_jobs = Job.get_ready_jobs()

    job_log.info("run_next: %d runnable jobs of (%d pending, %d tasked)" % (
        len(runnable_jobs),
        Job.objects.filter(state = 'pending').count(),
        Job.objects.filter(state = 'tasked').count()))

    for job in runnable_jobs:
        start_job(job)


def start_job(job):
    from chroma_core.models.jobs import Job
    from chroma_core.lib.job import job_log
    job_log.info("Job %d: Job.run %s" % (job.id, job.description()))
    # Important: multiple connections are allowed to call run() on a job
    # that they see as pending, but only one is allowed to proceed past this
    # point and spawn tasks.

    # All the complexity of StateManager's dependency calculation doesn't
    # matter here: we've reached our point in the queue, all I need to check now
    # is - are this Job's immediate dependencies satisfied?  And are any deps
    # for a statefulobject's new state satisfied?  If so, continue.  If not, cancel.

    try:
        deps_satisfied = job._deps_satisfied()
    except Exception:
        # Catchall exception handler to ensure progression even if Job
        # subclasses have bugs in their get_deps etc.
        job_log.error("Job %s: exception in dependency check: %s" % (job.id,
                                                                     '\n'.join(traceback.format_exception(*(sys.exc_info())))))
        complete_job(job, cancelled = True)
        return

    if not deps_satisfied:
        job_log.warning("Job %d: cancelling because of failed dependency" % job.id)
        complete_job(job, cancelled = True)
        # TODO: tell someone WHICH dependency
        return

    # Set state to 'tasked'
    # =====================
    updated = Job.objects.filter(pk = job.id, state = 'pending').update(state = 'tasking')

    if not updated:
        # Someone else already started this job, bug out
        job_log.debug("Job %d already started running, backing off" % job.id)
        return
    else:
        assert(updated == 1)
        job_log.debug("Job %d pending->tasking" % job.id)
        job.state = 'tasking'

    RunJobThread(job.id).start()
    job.state = 'tasked'
    job.save()
    job_log.debug("Job %d tasking->tasked (%s)" % (job.id, job.task_id))


def complete_job(job, errored = False, cancelled = False):
    from chroma_core.models.jobs import StateChangeJob
    from chroma_core.lib.job import job_log
    success = not (errored or cancelled)
    if success and isinstance(job, StateChangeJob):
        new_state = job.state_transition[2]
        obj = job.get_stateful_object()
        obj.set_state(new_state, intentional = True)
        job_log.info("Job %d: StateChangeJob complete, setting state %s on %s" % (job.pk, new_state, obj))

    job_log.info("Job %s completing (errored=%s, cancelled=%s)" %
                 (job.id, errored, cancelled))
    job.state = 'completing'
    job.errored = errored
    job.cancelled = cancelled
    job.save()

    SerializedCalls.call('complete_job', job.pk)
    run_next()


class JobScheduler(object):
    def set_state(self, object_ids, message, run):
        """ RPC Call, the result will be passed
        to the client.
        """
        rc = SerializedCalls.call('command_set_state', object_ids, message)
        if run:
            run_next()
        return rc

    def notify_state(self, content_type, object_id, time_serialized, new_state, from_states):
        time = dateutil.parser.parse(time_serialized)
        rc = SerializedCalls.call('notify_state', content_type, object_id, time, new_state, from_states)
        run_next()
        return rc

    def run_jobs(self, job_dicts, message):
        result = SerializedCalls.call('command_run_jobs', job_dicts, message)
        run_next()
        return result
