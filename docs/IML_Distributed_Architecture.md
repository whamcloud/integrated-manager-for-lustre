[**Intel® Manager for Lustre\* Developer Resources Table of Contents**](README.md)

### The current setup

IML is composed of a series of modules and services. Many modules are hosted as [separate repositories](https://github.com/intel-hpdd), and many are hosted in a [single repo](https://github.com/intel-hpdd/intel-manager-for-lustre).

For brevity, we will refer to the separate repos as just _repos_, and the intel-manager-for-lustre repo as a 
_monorepo_

#### Repos

Each repo is a separate entry under the [Intel HPDD organization](https://github.com/intel-hpdd).

Many of the repos utilize [travis](https://travis-ci.org/) to run their automated tests. Travis is a general hosted CI platform where unit / integration tests can be run. Here is an [example](https://travis-ci.org/intel-hpdd/view-server/jobs/257382690). They also are published individually by travis on a public facing package registry; here is an [example](https://yarnpkg.com/en/package/@iml/view-server).

The larger repos may depend on smaller repos for reusable code. In this way, they build complex apps out of small pieces. Here is an [example](https://github.com/intel-hpdd/view-server/blob/52a1006fa24712362fc3eb833591c50ef86e4402/package.json#L25-L30) of a module depending on other versioned modules.

These modules can be thought of as a [tree](http://npm.anvaka.com/#/view/2d/%2540iml%252Frealtime). The leaves and lower nodes consist of useful functionality that is consumed by the root of the tree. 

In addition to publishing in a language specific package registry, the root nodes are usually published using a tool called [COPR](https://pagure.io/copr/copr). This allows OS level aggregation and installation.

#### Root Repos publish workflow

    ┌─────────────────────────────────────┐
    │                                     │
    │          Push code to repo          │
    │                                     │
    └─────────────────────────────────────┘
                       │
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │                                     │
    │         Pass Travis testing         │
    │                                     │
    └─────────────────────────────────────┘
                       │
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │                                     │
    │             Code Review             │
    │                                     │
    └─────────────────────────────────────┘
                       │
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │                                     │
    │          Gatekeeper lands           │
    │                                     │
    └─────────────────────────────────────┘
                       │
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │                                     │
    │ Bump version + publish using Travis │
    │                                     │
    └─────────────────────────────────────┘
                       │
                       │
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │            Add / update             │
    │manager-for-lustre-dependencies repo │
    │            with package.            │
    └─────────────────────────────────────┘
                       │
                       │
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │                                     │
    │             Pass build.             │
    │                                     │
    └─────────────────────────────────────┘
                       │
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │                                     │
    │           Publish on Copr           │
    │                                     │
    └─────────────────────────────────────┘