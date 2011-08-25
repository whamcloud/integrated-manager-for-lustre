#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydra_agent.audit import LocalLustreAudit

if __name__ == '__main__':
    print LocalLustreAudit().audit_info()
