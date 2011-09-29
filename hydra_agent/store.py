
import simplejson as json
import os
import errno

LIBDIR = "/var/lib/hydra"

def store_init():
    try:
        os.makedirs(LIBDIR)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise e

def _json_path(label):
    return os.path.join(LIBDIR, label)

def store_get_target_info(label):
    try:
        file = open(_json_path(label), 'r')
        j = json.load(file)
        file.close()
    except IOError, e:
        raise RuntimeError("Failed to read target data for '%s', is it configured? (%s)" % (label, e))

    return j

def store_remove_target_info(label):
    try:
        os.unlink(_json_path(label))
    except OSError, e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise e

def store_write_target_info(label, info):
    # Save the metadata for the mount (may throw an IOError)
    file = open(_json_path(label), 'w')
    json.dump(info, file)
    file.close()
    
