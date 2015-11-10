# coding:utf8
u'''
Copyright (c) 2015, viewstar000
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

-----------------------------------

## CASE TREE

 *  API
     *  Method：
         *  GET
         *  POST
     *  调用模式：
         *  调用方 -> 被调用方
         *  同步   -> 同步
         *  同步   -> 异步
         *  异步   -> 同步
         *  异步   -> 异步
     *  参数模式：
         *  序列化
         *  RAW模式
 *  SIGNAL
     *  GET
     *  POST
     *  同步
     *  异步
         *  excludes
     *  参数模式
     *  RAW模式

## API

| POST | SYNC -> SYNC   | JSON | checked |
| POST | SYNC -> SYNC   | RAW  | checked |
| POST | SYNC -> ASYNC  | JSON | checked |
| POST | SYNC -> ASYNC  | RAW  | checked |
| POST | ASYNC -> SYNC  | JSON | checked |
| POST | ASYNC -> SYNC  | RAW  | checked |
| POST | ASYNC -> ASYNC | JSON | checked |
| POST | ASYNC -> ASYNC | RAW  | checked |
| GET  | SYNC -> SYNC   | JSON | checked |
| GET  | SYNC -> SYNC   | RAW  | checked |
| GET  | SYNC -> ASYNC  | JSON | checked |
| GET  | SYNC -> ASYNC  | RAW  | checked |
| GET  | ASYNC -> SYNC  | JSON | checked |
| GET  | ASYNC -> SYNC  | RAW  | checked |
| GET  | ASYNC -> ASYNC | JSON | checked |
| GET  | ASYNC -> ASYNC | RAW  | checked |

## SIGNAL

| POST | SYNC -> SYNC   |          | JSON | checked |
| POST | SYNC -> SYNC   |          | RAW  | checked |
| POST | SYNC -> ASYNC  |          | JSON | checked |
| POST | SYNC -> ASYNC  |          | RAW  | checked |
| POST | ASYNC -> SYNC  |          | JSON | checked |
| POST | ASYNC -> SYNC  |          | RAW  | checked |
| POST | ASYNC -> ASYNC |          | JSON | checked |
| POST | ASYNC -> ASYNC |          | RAW  | checked |
| POST | ASYNC -> ASYNC | excludes | JSON | checked |
| POST | ASYNC -> ASYNC | excludes | RAW  | checked |
| GET  | SYNC -> SYNC   |          | JSON | checked |
| GET  | SYNC -> SYNC   |          | RAW  | checked |
| GET  | SYNC -> ASYNC  |          | JSON | checked |
| GET  | SYNC -> ASYNC  |          | RAW  | checked |
| GET  | ASYNC -> SYNC  |          | JSON | checked |
| GET  | ASYNC -> SYNC  |          | RAW  | checked |
| GET  | ASYNC -> ASYNC |          | JSON | checked |
| GET  | ASYNC -> ASYNC |          | RAW  | checked |
| GET  | ASYNC -> ASYNC | excludes | JSON | checked |
| GET  | ASYNC -> ASYNC | excludes | RAW  | checked |

'''

import json
import time

from urllib import urlopen, urlencode

HOST = 'localhost:8678'

def GET(uri, data = None, **params):

    if not isinstance(data, (str, unicode)):
        data = json.dumps(data)
    params['--req-data'] = data
    excludes = params.get('excludes', [])
    if 'excludes' in params:
        del params['excludes']
    params  = params.items()
    for ex in excludes:
        params.append(('excludes', ex))
    params  = urlencode(params)
    url     = 'http://'+HOST+'/'+uri.strip('/')+'?'+params
    r       = urlopen(url)
    print url
    return r.getcode(), r.read()


def POST(uri, data = None, **params):

    if not isinstance(data, (str, unicode)):
        data = json.dumps(data)
    excludes = params.get('excludes', [])
    if 'excludes' in params:
        del params['excludes']
    params  = params.items()
    for ex in excludes:
        params.append(('excludes', ex))
    params  = urlencode(params)
    url     = 'http://'+HOST+'/'+uri.strip('/')+'?'+params
    r       = urlopen(url, data)
    print url, data
    return r.getcode(), r.read()


def assert_api_success((ret_code, result)):

    assert ret_code == 200, ('ERROR', ret_code, result)
    return json.loads(result)

def assert_async_api_success((ret_code, result)):

    assert ret_code == 200, ('ERROR', ret_code, result)
    assert result == 'OK', result

def assert_signal_success((ret_code, result)):

    assert ret_code == 200, ('ERROR', ret_code, result)
    assert result == 'OK', result

def assert_sync_signal_success((ret_code, result)):

    assert ret_code == 200, ('ERROR', ret_code, result)
    return json.loads(result)


def test_POST_API_sync_to_sync_and_async():

    result = assert_api_success(POST('/Services/IDCreatorService/IDCreatorService/create_id', {'tag':'324'}))
    assert int(result), result

    result = assert_api_success(POST('/Services/Cache/DemoCacheService/set', {'key':'324', 'value':'hahahaha'}))
    assert result, ret_code

    result = assert_api_success(POST('/Services/Cache/DemoCacheService/get', {'key':'324'}))
    assert result == "hahahaha", result
    
    result = assert_api_success(POST('/Services/Cache/DemoCacheEXService/set', {'key':'324', 'value':'wwwwwwww'}))
    assert result, result

    result = assert_api_success(POST('/Services/Cache/DemoCacheEXService/get', {'key':'324'}))
    assert result == "wwwwwwww", result


def test_GET_API_sync_to_sync_and_async():

    result = assert_api_success(GET('/Services/IDCreatorService/IDCreatorService/create_id', {'tag':'324'}))
    assert int(result), result

    result = assert_api_success(GET('/Services/Cache/DemoCacheService/set', {'key':'324', 'value':'hahahaha'}))
    assert result, ret_code

    result = assert_api_success(GET('/Services/Cache/DemoCacheService/get', {'key':'324'}))
    assert result == "hahahaha", result
    
    result = assert_api_success(GET('/Services/Cache/DemoCacheEXService/set', {'key':'324', 'value':'wwwwwwww'}))
    assert result, result

    result = assert_api_success(GET('/Services/Cache/DemoCacheEXService/get', {'key':'324'}))
    assert result == "wwwwwwww", result


def test_POST_API_async_to_async():

    assert_async_api_success(POST('/Services/IDCreatorService/IDCreatorService/create_id', {'tag':'324'}, wait_response = ''))
    assert_async_api_success(POST('/Services/Cache/DemoCacheService/set', {'key':'324', 'value':'hahahaha'}, wait_response = ''))
    result = assert_api_success(POST('/Services/Cache/DemoCacheService/get', {'key':'324'}))
    assert result == "hahahaha", result
    
    assert_async_api_success(POST('/Services/Cache/DemoCacheEXService/set', {'key':'324', 'value':'wwwwwwww'}, wait_response = ''))
    result = assert_api_success(POST('/Services/Cache/DemoCacheEXService/get', {'key':'324'}))
    assert result == "wwwwwwww", result


def test_GET_API_async_to_async():

    assert_async_api_success(GET('/Services/IDCreatorService/IDCreatorService/create_id', {'tag':'324'}, wait_response = ''))
    assert_async_api_success(GET('/Services/Cache/DemoCacheService/set', {'key':'324', 'value':'hahahaha'}, wait_response = ''))
    result = assert_api_success(GET('/Services/Cache/DemoCacheService/get', {'key':'324'}))
    assert result == "hahahaha", result
    
    assert_async_api_success(GET('/Services/Cache/DemoCacheEXService/set', {'key':'324', 'value':'wwwwwwww'}, wait_response = ''))
    result = assert_api_success(GET('/Services/Cache/DemoCacheEXService/get', {'key':'324'}))
    assert result == "wwwwwwww", result


def test_POST_SIGNAL_async_to_async():

    assert_signal_success(POST('/Signals/IDMapper/reset', {'reset_to': 10}))

    assert_signal_success(POST('/Signals/CACHE/update', {'key': 10, 'value':1234134}))
    time.sleep(0.1)
    result = assert_api_success(POST('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 1234134, result
    result = assert_api_success(POST('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 1234134, result

    assert_signal_success(POST('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)
    result = assert_api_success(POST('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == None, result
    result = assert_api_success(POST('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == None, result


def test_GET_SIGNAL_async_to_async():

    assert_signal_success(GET('/Signals/IDMapper/reset', {'reset_to': 10}))

    assert_signal_success(GET('/Signals/CACHE/update', {'key': 10, 'value':56345645}))
    time.sleep(0.1)
    result = assert_api_success(GET('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 56345645, result
    result = assert_api_success(GET('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 56345645, result

    assert_signal_success(GET('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)
    result = assert_api_success(GET('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == None, result
    result = assert_api_success(GET('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == None, result


def test_POST_SIGNAL_async_to_async_with_excludes():

    assert_signal_success(POST('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)

    assert_signal_success(POST('/Signals/CACHE/update', {'key': 10, 'value':2345245}, excludes = ['DemoCacheEXService']))
    time.sleep(0.1)
    result = assert_api_success(POST('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 2345245, result
    result = assert_api_success(POST('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == None, result

    assert_signal_success(POST('/Signals/CACHE/update', {'key': 10, 'value':734563456}, excludes = ['DemoCacheService']))
    time.sleep(0.1)
    result = assert_api_success(POST('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 2345245, result
    result = assert_api_success(POST('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 734563456, result

    assert_signal_success(POST('/Signals/CACHE/remove', {'key': 10}, excludes = ['DemoCacheService', 'DemoCacheEXService']))
    time.sleep(0.1)
    result = assert_api_success(POST('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 2345245, result
    result = assert_api_success(POST('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 734563456, result

    assert_signal_success(POST('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)


def test_GET_SIGNAL_async_to_async_with_excludes():

    assert_signal_success(GET('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)

    assert_signal_success(GET('/Signals/CACHE/update', {'key': 10, 'value':2345245}, excludes = ['DemoCacheEXService']))
    time.sleep(0.1)
    result = assert_api_success(GET('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 2345245, result
    result = assert_api_success(GET('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == None, result

    assert_signal_success(GET('/Signals/CACHE/update', {'key': 10, 'value':734563456}, excludes = ['DemoCacheService']))
    time.sleep(0.1)
    result = assert_api_success(GET('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 2345245, result
    result = assert_api_success(GET('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 734563456, result

    assert_signal_success(GET('/Signals/CACHE/remove', {'key': 10}, excludes = ['DemoCacheService', 'DemoCacheEXService']))
    time.sleep(0.1)
    result = assert_api_success(GET('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 2345245, result
    result = assert_api_success(GET('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 734563456, result

    assert_signal_success(GET('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)


def test_POST_SIGNAL_sync_to_sync_and_async():

    assert_signal_success(POST('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)

    assert_sync_signal_success(POST('/Signals/CACHE/update', {'key': 10, 'value':2345245}, sync_to = 'DemoCacheService'))
    time.sleep(0.1)
    result = assert_api_success(POST('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 2345245, result
    result = assert_api_success(POST('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == None, result

    assert_sync_signal_success(POST('/Signals/CACHE/update', {'key': 10, 'value':734563456}, sync_to = 'DemoCacheEXService'))
    time.sleep(0.1)
    result = assert_api_success(POST('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 2345245, result
    result = assert_api_success(POST('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 734563456, result

    assert_signal_success(POST('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)


def test_GET_SIGNAL_sync_to_sync_and_async():

    assert_signal_success(GET('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)

    assert_sync_signal_success(GET('/Signals/CACHE/update', {'key': 10, 'value':2345245}, sync_to = 'DemoCacheService'))
    time.sleep(0.1)
    result = assert_api_success(GET('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 2345245, result
    result = assert_api_success(GET('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == None, result

    assert_sync_signal_success(GET('/Signals/CACHE/update', {'key': 10, 'value':734563456}, sync_to = 'DemoCacheEXService'))
    time.sleep(0.1)
    result = assert_api_success(GET('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 2345245, result
    result = assert_api_success(GET('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 734563456, result

    assert_signal_success(GET('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)


def test_POST_API_async_to_sync_with_callback():

    assert_signal_success(POST('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)

    assert_async_api_success(POST('/Services/Cache/DemoCacheService/set', {'key':10, 'value':38947341}, wait_response = '', callback='Services.Cache.DemoCacheEXService.set'))
    time.sleep(0.1)
    result = assert_api_success(POST('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 38947341, result
    result = assert_api_success(POST('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 38947341, result


    assert_async_api_success(POST('/Services/Cache/DemoCacheEXService/set', {'key':10, 'value':23498572}, wait_response = '', callback='Signals.CACHE.update'))
    time.sleep(0.1)
    result = assert_api_success(POST('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 23498572, result
    result = assert_api_success(POST('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 23498572, result

    assert_signal_success(POST('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)


def test_GET_API_async_to_sync_with_callback():

    assert_signal_success(GET('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)

    assert_async_api_success(GET('/Services/Cache/DemoCacheService/set', {'key':10, 'value':38947341}, wait_response = '', callback='Services.Cache.DemoCacheEXService.set'))
    time.sleep(0.1)
    result = assert_api_success(GET('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 38947341, result
    result = assert_api_success(GET('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 38947341, result


    assert_async_api_success(GET('/Services/Cache/DemoCacheEXService/set', {'key':10, 'value':23498572}, wait_response = '', callback='Signals.CACHE.update'))
    time.sleep(0.1)
    result = assert_api_success(GET('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 23498572, result
    result = assert_api_success(GET('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 23498572, result

    assert_signal_success(GET('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)


def test_POST_SIGNAL_async_to_sync_with_callback():

    assert_signal_success(POST('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)

    assert_signal_success(POST('/Signals/CACHE/update', {'key':10, 'value':38947341}, wait_response = '', sync_to='DemoCacheService', callback='Services.Cache.DemoCacheEXService.set'))
    time.sleep(0.1)
    result = assert_api_success(POST('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 38947341, result
    result = assert_api_success(POST('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 38947341, result


    assert_signal_success(POST('/Signals/CACHE/update', {'key':10, 'value':23498572}, wait_response = '', sync_to='DemoCacheEXService', callback='Signals.CACHE.update'))
    time.sleep(0.1)
    result = assert_api_success(POST('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 23498572, result
    result = assert_api_success(POST('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 23498572, result

    assert_signal_success(POST('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)


def test_GET_SIGNAL_async_to_sync_with_callback():

    assert_signal_success(GET('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)

    assert_signal_success(GET('/Signals/CACHE/update', {'key':10, 'value':38947341}, wait_response = '', sync_to='DemoCacheService', callback='Services.Cache.DemoCacheEXService.set'))
    time.sleep(0.1)
    result = assert_api_success(GET('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 38947341, result
    result = assert_api_success(GET('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 38947341, result


    assert_signal_success(GET('/Signals/CACHE/update', {'key':10, 'value':23498572}, wait_response = '', sync_to='DemoCacheEXService', callback='Signals.CACHE.update'))
    time.sleep(0.1)
    result = assert_api_success(GET('/Services/Cache/DemoCacheService/get', {'key':10}))
    assert result == 23498572, result
    result = assert_api_success(GET('/Services/Cache/DemoCacheEXService/get', {'key':10}))
    assert result == 23498572, result

    assert_signal_success(GET('/Signals/CACHE/remove', {'key': 10}))
    time.sleep(0.1)


def test_POST_unknown_api():

    ret_code, result = POST('/Services/Cache/DemoCacheService/abc', {'a':'b'})
    print ret_code, result
    assert ret_code != 200

