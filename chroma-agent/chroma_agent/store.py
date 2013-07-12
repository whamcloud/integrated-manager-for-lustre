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


import simplejson as json
import os
import errno


class AgentStoreException(Exception):
    pass


class AgentStore(object):
    server_conf_mtime = None
    _dir_setup = False
    AgentStoreException = AgentStoreException

    @classmethod
    def libdir(cls):
        LIBDIR = "/var/lib/chroma"
        if not cls._dir_setup:
            try:
                os.makedirs(LIBDIR)
            except OSError, e:
                if e.errno == errno.EEXIST:
                    pass
                else:
                    raise e
        return LIBDIR

    @classmethod
    def _json_path(cls, name):
        """Get a fully qualified filename for a configuration file,

        >>> AgentStore._json_path('server_conf')
        "/var/lib/chroma/server_conf"

        """
        return os.path.join(cls.libdir(), name)

    @classmethod
    def _unlink_if_exists(cls, path):
        try:
            os.unlink(path)
        except OSError, e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise e

    SERVER_CONF_FILE = "server_conf"

    @classmethod
    def get_server_conf(cls):
        try:
            f = open(cls._json_path(cls.SERVER_CONF_FILE))
            j = json.load(f)
            f.close()
            cls.server_conf_mtime = os.path.getmtime(cls._json_path(cls.SERVER_CONF_FILE))
        except IOError, e:
            if e.errno == errno.ENOENT:
                # Return none if no server conf exists
                cls.server_conf_mtime = None
                return None
            else:
                raise
        except ValueError:
            # Malformed JSON indicates a part-written file, behave as if it doesn't exist
            # and don't set server_conf_mtime, so that caller will retry
            return None
        return j

    @classmethod
    def remove_server_conf(cls):
        cls._unlink_if_exists(cls._json_path(cls.SERVER_CONF_FILE))

    @classmethod
    def set_server_conf(cls, conf):
        file = open(cls._json_path(cls.SERVER_CONF_FILE), 'w')
        json.dump(conf, file)
        file.close()

    @classmethod
    def get_target_info(cls, name):
        try:
            file = open(cls._json_path(name), 'r')
            j = json.load(file)
            file.close()
        except IOError, e:
            raise AgentStoreException("Failed to read target data for '%s', is it configured? (%s)" % (name, e))

        return j

    @classmethod
    def remove_target_info(cls, name):
        cls._unlink_if_exists(cls._json_path(name))

    @classmethod
    def set_target_info(cls, name, info):
        """Save the metadata for the mount (may throw an IOError)"""
        file = open(cls._json_path(name), 'w')
        json.dump(info, file)
        file.close()
