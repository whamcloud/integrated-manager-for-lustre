#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
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


AGENTRPCWRAPPERVERSION = 1


def agent_error(value):
    return {'wrapper_version': AGENTRPCWRAPPERVERSION,
            'error': value}


def agent_result(value):
    return {'wrapper_version': AGENTRPCWRAPPERVERSION,
            'result': value}


def agent_ok_or_error(error):
    """
    If error != None then return it as the error else return result_ok
    :param error: error or None
    :return:agent_error or agent_result_ok
    """
    if error:
        return agent_error(error)
    else:
        return agent_result_ok

agent_result_ok = agent_result(True)


def agent_result_is_error(result):
    return 'error' in result


def agent_result_is_ok(result):
    return 'result' in result
