#!/usr/bin/env python

from hydra_agent.audit import LocalLustreAudit

if __name__ == '__main__':
    print LocalLustreAudit().audit_info()
