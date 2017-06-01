# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


# import so that this module can be imported in pure python environments as well as on Linux.
# Doing it this way means that rpm_lib can mocked.
try:
    import rpm as rpm_lib
except:
    try:
        # Allow an override in local settings, because I want to get real output I run it on a remote linux node from my mac.
        # I have this in my local_settings.py : Chris
        # class rpm_lib(object):
        #     @classmethod
        #     def labelCompare(cls, a, b):
        #         from subprocess import Popen, PIPE
        #         result = Popen(["ssh", "lotus-33",  "python -c \"import rpm\nimport sys\nsys.stdout.write(str(rpm.labelCompare(('%s', '%s', '%s'), ('%s', '%s', '%s'))))\"" % (a[0], a[1], a[2], b[0], b[1], b[2])], stdout=PIPE).communicate()[0]
        #         return int(result
        from local_settings import rpm_lib
    except:
        class rpm_lib(object):
            @classmethod
            def labelCompare(cls, a, b):
                return cmp(a, b)


class VersionInfo(object):
    """
    A convenient way of storing package version information that can be printed and compared with ease.

    At present this class is not serializable and so cannot be converted easily into json. This highlights
    a limitation of our current use of plain json for messages in that all but the basic types have to be
    discarded during their transportation.
    """
    def __init__(self, epoch, version, release, arch):
        self.epoch = epoch
        self.version = version
        self.release = release
        self.arch = arch

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "epoch='%s', version='%s', release='%s', arch='%s'" % (self.epoch, self.version, self.release, self.arch)

    def __cmp__(self, other):
        return rpm_lib.labelCompare((self.epoch, self.version, self.release), (other.epoch, other.version, other.release))
