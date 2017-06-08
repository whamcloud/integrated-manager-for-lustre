# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


AGENTRPCWRAPPERVERSION = 1


def agent_error(value):
    return {'wrapper_version': AGENTRPCWRAPPERVERSION,
            'error': value}


def agent_result(value):
    return {'wrapper_version': AGENTRPCWRAPPERVERSION,
            'result': value}


def agent_ok_or_error(error):
    '''
    If error != None then return it as the error else return result_ok
    :param value: error or None
    :return:agent_error or agent_result_ok
    '''
    if error:
        return agent_error(error)
    else:
        return agent_result_ok

agent_result_ok = agent_result(True)


def agent_result_is_error(result):
    return 'error' in result


def agent_result_is_ok(result):
    return 'result' in result
