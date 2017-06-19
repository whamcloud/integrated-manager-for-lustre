
# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
import errno
import multiprocessing
import json
import base64
import tempfile
from chroma_agent.log import daemon_log


class ConfigKeyExistsError(Exception):
    def __init__(self, section, key):
        self.section = section
        self.key = key

    def __str__(self):
        return "The key '%s' already exists in section '%s'. Please use update() if that's what you intended." % (self.key, self.section)


class InvalidConfigIdentifier(Exception):
    def __init__(self, ident):
        self.ident = ident

    def __str__(self):
        return "section and key must be strings, not '%s'" % self.ident


class ConfigStore(object):
    def _create_path(self, path):
        try:
            os.makedirs(path, 0755)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        return path

    def _encode_key(self, key):
        return base64.urlsafe_b64encode(self._ck_str(key))

    def _decode_key(self, key):
        return base64.urlsafe_b64decode(key)

    def _ck_str(self, input):
        if not isinstance(input, basestring):
            raise InvalidConfigIdentifier(input)
        return input

    def _safe_unlink(self, path):
        try:
            os.unlink(path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise e

    def __init__(self, path):
        self.path = path
        self._lock = multiprocessing.RLock()

        self._create_path(self.path)

    @property
    def lock(self):
        return self._lock

    @property
    def sections(self):
        with self._lock:
            return sorted([os.path.basename(e)
                           for e in os.listdir(self.path)
                           if os.path.isdir(os.path.join(self.path, e))])

    def get_section_keys(self, section):
        dir = os.path.join(self.path, self._ck_str(section))

        with self._lock:
            if not section in self.sections:
                return []
            else:
                return [self._decode_key(e) for e in os.listdir(dir)]

    def get_section(self, section):
        with self._lock:
            return dict([(key, self.get(section, key))
                         for key in self.get_section_keys(section)])

    def get_all(self):
        with self._lock:
            return dict([(section, self.get_section(section))
                         for section in self.sections])

    def delete_section(self, section):
        dir = os.path.join(self.path, self._ck_str(section))

        with self._lock:
            for key in self.get_section_keys(section):
                self.delete(section, key)
            os.rmdir(dir)

    def clear(self):
        with self._lock:
            for section in self.sections:
                self.delete_section(section)

    def set(self, section, key, value, update=False):
        safe_key = self._encode_key(key)

        with self._lock:
            dir = self._create_path(os.path.join(self.path,
                                                 self._ck_str(section)))

            if not update and key in self.get_section_keys(section):
                raise ConfigKeyExistsError(section, key)

            tmp_fd, tmp_name = tempfile.mkstemp(dir=dir)
            try:
                with os.fdopen(tmp_fd, "w") as f:
                    json.dump(value, f)
                os.rename(tmp_name, os.path.join(dir, safe_key))
            finally:
                # clean up if necessary
                self._safe_unlink(tmp_name)

    def update(self, section, key, value):
        self.set(section, key, value, update=True)

    def get(self, section, key):
        dir = os.path.join(self.path, self._ck_str(section))
        safe_key = self._encode_key(key)

        with self._lock:
            try:
                with open(os.path.join(dir, safe_key), "r") as f:
                    return json.load(f)
            except IOError as e:
                if e.errno == errno.ENOENT:
                    if not section in self.sections:
                        raise TypeError("Invalid config section: '%s'" % section)
                    elif not key in self.get_section_keys(section):
                        raise KeyError("Invalid key '%s' for config section '%s'"
                                       % (key, section))
                raise
            except Exception as e:
                daemon_log.warn("Json error %s, file was %s" % (e, os.path.join(dir, safe_key)))
                daemon_log.warn("File contents %s" % open(os.path.join(dir, safe_key), "r").read())
                raise

    def delete(self, section, key):
        dir = os.path.join(self.path, self._ck_str(section))
        safe_key = self._encode_key(key)

        with self._lock:
            self._safe_unlink(os.path.join(dir, safe_key))

    # #####################################
    # Some self accessors to common entries
    # #####################################
    @property
    def profile_managed(self):
        """
        :return: True if profile is managed False if not or no profile
        """
        try:
            return self.get('settings', 'profile').get('managed', False)
        except (KeyError, TypeError):
            return False
