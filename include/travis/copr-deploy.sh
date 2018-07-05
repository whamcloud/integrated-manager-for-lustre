#!/bin/bash -xe

prepare() {

    # shellcheck disable=SC2154
    openssl aes-256-cbc -K "$encrypted_253525cedcf6_key" -iv "$encrypted_253525cedcf6_iv" -in include/copr-mfl.enc -out include/copr-mfl -d
    curl -O https://raw.githubusercontent.com/m3t/travis_wait/master/travis_wait
    chmod 755 travis_wait

}

build() {

    echo 'travis_fold:start:yum'
    yum -y install epel-release
    yum -y install rpm-build rpmdevtools copr-cli yum-utils git make python-setuptools npm
    echo 'travis_fold:end:yum'
    cd "${1:-/build}"
    make DRYRUN=false iml_copr_build

}

build_srpm() {
    echo 'travis_fold:start:yum'
    yum -y install epel-release
    yum -y install rpm-build rpmdevtools copr-cli yum-utils git make python-setuptools npm
    echo 'travis_fold:end:yum'
    cd "${1:-/build}"
    make DRYRUN=false UNPUBLISHED=true iml_copr_build
}

# default action to build for backward compatibility
action=${1:-build}

$action
