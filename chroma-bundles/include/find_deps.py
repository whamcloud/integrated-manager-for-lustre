#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2017 Intel Corporation All Rights Reserved.
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
    missing_deps = []
    all_pkg_names = []

    def __init__(self):
        self.yb = yum.YumBase()
        self.yb.preconf.debuglevel = 0
        self.yb.preconf.errorlevel = 0

        if not self.yb.setCacheDir(force = True, reuse = False):
            print >>sys.stderr, "Can't create a tmp. cachedir. "
            sys.exit(1)

    def req2pkgs(self, req, depth=0):
        global __req2pkgs

        req = str(req)
        if req in self.__req2pkgs:
            return self.__req2pkgs[req]

        providers = []
        print >>sys.stderr, "%srequires %s:" % (' ' * depth, req)
        try:
            matches = self.yb.searchPackageProvides([req])
            print >>sys.stderr, "%sprovided by %s:" % (' ' * depth, matches)
            if not matches:
                return []
            providers = matches.keys()
        except yum.Errors.YumBaseError:
            print >>sys.stderr, "No package provides %s" % req
            return []

        self.__req2pkgs[req] = providers
        return providers

    def _find_deps(self, pkg, excludes, depth=0):
        # not interested in installed packages, just what's in the repo
        if pkg.__class__.__name__ == "RPMInstalledPackage":
            return
        if pkg in self.all_deps:
            return
        print >>sys.stderr, "%spackage %s:" % (' ' * depth, pkg)
        depth += 1
        self.all_deps.append(pkg)
        for tup in pkg.returnPrco('requires'):
            name = yum.misc.prco_tuple_to_string(tup)
            if name.startswith("rpmlib("):
                continue
            pkgs = [p for p in self.req2pkgs(name, depth - 1)
                    if not p.__class__.__name__ == "RPMInstalledPackage"]
            #print "pkgs = %s" % pkgs
            if pkgs:
                for npkg in pkgs:
                    if npkg.name in excludes:
                        continue
                    if npkg.name in self.all_pkg_names:
                        self._find_deps(npkg, excludes, depth)
                    else:
                        if npkg.name not in self.missing_deps:
                            print >>sys.stderr, "adding to missing_deps 1"
                            self.missing_deps.append(npkg.name)
            else:
                if name.find(' ') > -1:
                    name = name[0:name.find(' ')]
                if name not in self.all_pkg_names:
                    print >>sys.stderr, "adding to missing_deps 2"
                    self.missing_deps.append(name)

        #print "missing_deps: %s:" % self.missing_deps
        return

    def disable_all_repos(self):
        for repo in self.yb.repos.findRepos("*"):
            # these are hardcoded to the distro defaults and our own
            # infrastructure right now
            # these probably need to be externally specified
            if repo.id != "base" and repo.id != "core-0" and \
               repo.id != "updates" and repo.id != "updates-centos7.3-x86_64" and \
               repo.id != "extras" and repo.id != "extras-centos7.3-x86_64" and \
               repo.id != "addon-epel7-x86_64" and repo.id != "epel" and \
               repo.id != "copr-be.cloud.fedoraproject.org_results_managerforlustre_manager-for-lustre_epel-7-x86_64_":
                repo.disable()

    def add_repo(self, repo, num):
        repopath = os.path.normpath(repo)
        newrepo = yum.yumRepo.YumRepository("repo%s" % num)
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

    def get_deps(self, search_repos, pkg_list, excludes):
        self.disable_all_repos()
        x = 0
        for search_repo in search_repos:
            self.add_repo(search_repo, x)
            x += 1
        self.set_archlist(None)

        for pkg in self.get_matching_pkgs(pkg_list):
            self._find_deps(pkg, excludes)

        return self.all_deps, self.missing_deps

repos = [os.path.abspath(path) for path in sys.argv[1].split(" ")]

pkgs = sys.argv[2].split(" ")

if len(sys.argv) > 3:
    excludes = sys.argv[3].split(" ")
else:
    excludes = []

yumdepfinder = YumDepFinder()
deps, missing_deps = yumdepfinder.get_deps(repos, pkgs, excludes)

if missing_deps:
    print >>sys.stderr, "final missing_deps: %s" % missing_deps
    print '\n'.join(missing_deps)
    sys.exit(1)

print '\n'.join(["%s-%s-%s.%s" % (p.name, p.version, p.release, p.arch)
                for p in deps if p.repoid == "repo0"])
sys.exit(0)
