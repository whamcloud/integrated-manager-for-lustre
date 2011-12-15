
import simplejson as json
import os
import errno


class AgentStore(object):
    LIBDIR = "/var/lib/hydra"

    @classmethod
    def _json_path(cls, name):
        return os.path.join(cls.LIBDIR, name)

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
        except IOError, e:
            if e.errno == errno.ENOENT:
                # Return none if no server conf exists
                return None
            else:
                raise
        return j

    @classmethod
    def remove_server_conf(cls):
        cls._unlink_if_exists(os.path.join(cls.LIBDIR, cls.SERVER_CONF_FILE))

    @classmethod
    def set_server_conf(cls, conf):
        file = open(cls._json_path(cls.SERVER_CONF_FILE), 'w')
        json.dump(conf, file)
        file.close()

    @classmethod
    def setup(cls):
        try:
            os.makedirs(AgentStore.LIBDIR)
        except OSError, e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise e

    @classmethod
    def get_target_info(cls, name):
        try:
            file = open(cls._json_path(name), 'r')
            j = json.load(file)
            file.close()
        except IOError, e:
            raise RuntimeError("Failed to read target data for '%s', is it configured? (%s)" % (name, e))

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
    
