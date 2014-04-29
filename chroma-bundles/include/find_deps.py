#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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


import os
import sys
import yum


class YumDepFinder(object):
    __req2pkgs = {}
    all_deps = []
    all_pkg_names = []

    def __init__(self):
        self.yb = yum.YumBase()
        self.yb.preconf.debuglevel = 0
        self.yb.preconf.errorlevel = 0

        if not self.yb.setCacheDir(force = True, reuse = False):
            print >>sys.stderr, "Can't create a tmp. cachedir. "
            sys.exit(1)

    def req2pkgs(self, req):
        global __req2pkgs

        req = str(req)
        if req in self.__req2pkgs:
            return self.__req2pkgs[req]

        providers = []
        try:
            matches = self.yb.searchPackageProvides([req])
            providers = matches.keys()
        except yum.Errors.YumBaseError:
            print >>sys.stderr, "No package provides %s" % req
            return []

        self.__req2pkgs[req] = providers
        return providers

    def _find_deps(self, pkgs, excludes):

        for pkg in pkgs:
            # not interested in installed packages, just what's in the repo
            if pkg.__class__.__name__ == "RPMInstalledPackage":
                return
            if pkg in self.all_deps:
                return
            self.all_deps.append(pkg)
            for tup in pkg.returnPrco('requires'):
                name = yum.misc.prco_tuple_to_string(tup)
                if name.startswith("rpmlib("):
                    continue
                pkgs = self.req2pkgs(name)
                if pkgs:
                    for npkg in pkgs:
                        if npkg.name in excludes:
                            continue
                        if npkg.name in self.all_pkg_names:
                            self._find_deps([npkg], excludes)

        return self.all_deps

    def disable_all_repos(self):
        for repo in self.yb.repos.findRepos("*"):
            repo.disable()

    def add_repo(self, repo):
        repopath = os.path.normpath(repo)
        newrepo = yum.yumRepo.YumRepository("repo")
        newrepo.name = repopath
        newrepo.baseurl = "file://" + repopath
        newrepo.basecachedir = self.yb.conf.cachedir
        self.yb.repos.add(newrepo)
        self.yb.repos.enableRepo(newrepo.id)
        self.yb.doRepoSetup()

    def set_archlist(self, archlist):
        self.yb.doSackSetup(archlist = archlist)

    def get_matching_pkgs(self, pkg_list):
        all_pkgs = self.yb.pkgSack.returnNewestByNameArch()
        self.all_pkg_names = [p.name for p in all_pkgs]
        return yum.packages.parsePackages(all_pkgs, pkg_list, casematch = 0)[0]

    def get_deps(self, search_repo, pkg_list, excludes):
        self.disable_all_repos()
        self.add_repo(search_repo)
        self.set_archlist(None)

        exact = self.get_matching_pkgs(pkg_list)

        self._find_deps(exact, excludes)

        return '\n'.join(["%s-%s-%s.%s" % (p.name, p.version, p.release, p.arch)
               for p in self.all_deps])

repo = os.path.abspath(sys.argv[1])

pkgs = sys.argv[2].split(" ")

if len(sys.argv) > 3:
    excludes = sys.argv[3].split(" ")
else:
    excludes = []

yumdepfinder = YumDepFinder()
print yumdepfinder.get_deps(repo, pkgs, excludes)
