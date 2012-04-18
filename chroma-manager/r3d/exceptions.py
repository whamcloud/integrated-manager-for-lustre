#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


class R3dError(RuntimeError):
    pass


class BadTimeString(R3dError):
    pass


class BadUpdateString(R3dError):
    pass


class BadUpdateTime(R3dError):
    pass


class BadSearchTime(R3dError):
    pass
