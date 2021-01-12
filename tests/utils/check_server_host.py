import logging

from tests.unit.remote_operations import RealRemoteOperations

logger = logging.getLogger("test")

# This purpose of this file is to begin creating a set of robust tests to fire at a server or host that checkout what
# is alive and what is dead etc. Perhaps it should really just run emf-diagnostics and it can be extended that way.
# Very robust catch everything.


def _check_status(address, additional_check_items):
    logger.debug("*" * 40)
    logger.debug("Checking status of %s" % address)

    check_items = [
        ("Services running", "ps ax | grep python"),
        ("Installed Packages", "rpm -qa"),
        ("Verify Packages", "rpm -Va"),
        ("Network status", "netstat"),
    ] + additional_check_items

    # Catch all exceptions so our caller doesn't have it's exceptions overwritten.
    try:
        remote_ops = RealRemoteOperations(None)

        if remote_ops.host_contactable(address):
            logger.debug("Host %s was contactable via SSH" % address)

            for action, command in check_items:
                logger.debug("#" * 40)

                remote_command_result = remote_ops._ssh_address(address, command, None)

                if remote_command_result.rc == 0:
                    logger.debug("%s on %s\n%s" % (action, address, remote_command_result.stdout.read()))
                else:
                    logger.debug(
                        "Error capturing %s on %s: result %s, stdout %s, stderr %s"
                        % (
                            action,
                            address,
                            remote_command_result.rc,
                            remote_command_result.stdout.read(),
                            remote_command_result.stderr.read(),
                        )
                    )
        else:
            logger.debug("Host %s was not contactable via SSH")
    except:
        pass

    logger.debug("*" * 40)


def check_manager_status(manager):
    try:
        from tests.utils.http_requests import AuthorizedHttpRequests

        user = manager["users"][0]
        chroma_manager = AuthorizedHttpRequests(
            user["username"], user["password"], server_http_url=manager["server_http_url"]
        )
        response = chroma_manager.get("/api/system_status")

        logger.debug("system_status from manager %s is %s\n" % (manager["server_http_url"], response.content))
    except:
        logger.debug("system_status could not be fetched from manager %s\n" % manager["server_http_url"])

    return _check_status(manager["fqdn"], [])


def check_host_status(server):
    return _check_status(server["fqdn"], [("Corosync Config", "cat /etc/corosync/corosync.conf")])


def check_nodes_status(config):
    for server in config["lustre_servers"]:
        check_host_status(server)

        for manager in config["chroma_managers"]:
            check_manager_status(manager)
