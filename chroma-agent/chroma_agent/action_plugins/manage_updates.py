#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import os
from chroma_agent import shell
from chroma_agent.crypto import Crypto
from chroma_agent.store import AgentStore

REPO_CONTENT = """
[Intel Lustre Manager]
name=Intel Lustre Manager updates
baseurl={0}
enabled=1
gpgcheck=0
sslverify = 1
sslcacert = {1}
sslclientkey = {2}
sslclientcert = {3}
"""

REPO_PATH = "/etc/yum.repos.d/Intel-Lustre-Manager.repo"


def configure_repo(remote_url, repo_path=REPO_PATH):
    crypto = Crypto(AgentStore.libdir())
    open(repo_path, 'w').write(REPO_CONTENT.format(remote_url, crypto.AUTHORITY_FILE, crypto.PRIVATE_KEY_FILE, crypto.CERTIFICATE_FILE))


def unconfigure_repo(repo_path=REPO_PATH):
    if os.path.exists(repo_path):
        os.remove(repo_path)


def update_packages(repo_path=REPO_PATH):
    if os.path.exists(repo_path):
        shell.try_run(['yum', '-y', 'update'])


def restart_server():
    shell.try_run(['reboot'])


ACTIONS = [configure_repo, unconfigure_repo, update_packages, restart_server]
CAPABILITIES = ['manage_updates']
