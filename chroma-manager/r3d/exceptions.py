## Copyright 2011 Whamcloud, Inc.
## Authors: Michael MacDonald <mjmac@whamcloud.com>


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
