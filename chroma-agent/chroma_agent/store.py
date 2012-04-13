
import simplejson as json
import os
import errno


class AgentStore(object):
    server_conf_mtime = None
    _dir_setup = False

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
    def server_conf_changed(cls):
        if bool(cls.server_conf_mtime) != os.path.exists(cls._json_path(cls.SERVER_CONF_FILE)):
            # If it's come into or out of existence
            return True

        if cls.server_conf_mtime:
            # If it existed last time we checked, is it modified?
            try:
                mtime = os.path.getmtime(cls._json_path(cls.SERVER_CONF_FILE))
            except IOError, e:
                # It ceased to exist during this function
                if e.errno == errno.ENOENT:
                    return True

            if mtime != cls.server_conf_mtime:
                return True
            else:
                return False

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
