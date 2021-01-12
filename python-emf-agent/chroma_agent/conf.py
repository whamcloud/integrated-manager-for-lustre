# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import os

ENV_PATH = "/etc/emf"


def set_server_url(url):
    if not os.path.exists(ENV_PATH):
        os.makedirs(ENV_PATH)

    with open("{}/manager-url.conf".format(ENV_PATH), "w+") as f:
        f.write("EMF_MANAGER_URL={}\n".format(url))


def remove_server_url():
    os.unlink("{}/manager-url.conf".format(ENV_PATH))


def set_emf_profile(name, repos, packages):
    """
    Setup /etc/emf/profile.conf
    """
    if not os.path.exists(ENV_PATH):
        os.makedirs(ENV_PATH)

    with open("{}/profile.conf".format(ENV_PATH), "w+") as f:
        if name:
            f.write("EMF_PROFILE_NAME={}\n".format(name))
        if repos:
            f.write("EMF_PROFILE_REPOS={}\n".format(",".join(repos)))
        if packages:
            f.write("EMF_PROFILE_PACKAGES={}\n".format(",".join(packages)))


def remove_emf_profile():
    os.unlink("{}/profile.conf".format(ENV_PATH))
