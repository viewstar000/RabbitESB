#coding:utf8
'''
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

---------------------------

## 服务DEMO

述语定义：

 *  **服务**：      相当于Interface，服务的抽像定义，用于对服务提供者进行归类和行为约束。
 *  **服务提供者**： 相当于实现了某个Inteface的Class，服务的具体实现，从属于某个特定的服务定义并遵从相应的行为约束。
 *  **服务API**：   相当于Method，服务提供者对外暴露的功能接口。
 *  **Model**：     业务模型的抽像定义，用于事件进行归类和行为约束
 *  **Signal**：    事件定义，一个事件必须从属某个Model，事件可以有参数。事件与API调用区别在于API调用是点对点的，默认为同步调用。事件为一对多的，默认为异步方式。

服务整体框架：
    
 *  所有服务
     +  服务A
         -  服务提供者A
             *  API: Services.A.A.abc(...)
             *  API: Services.A.A.bcd(...)
             *  ……
         -  服提供供者B
             *  API: Services.A.B.abc(...)
             *  API: Services.A.B.bcd(...)
             *  ……
         -  ……
     + 服务B
         -  服务提供者A
             *  API: Services.B.A.abc(...)
             *  API: Services.B.A.bcd(...)
             *  ……
         -  服提供供者B
             *  API: Services.B.B.abc(...)
             *  API: Services.B.B.bcd(...)
             *  ……
         -  ……
     +  ……
 *  所有MODEL
     +  Model_A
         -  Signal: Signals.Model_A.signal_a
         -  Signal: Signals.Model_A.signal_b
     +  Model_B
         -  Signal: Signals.Model_B.signal_a
         -  Signal: Signals.Model_B.signal_b
     +  ……




'''

import urllib

from esb import *

@ServiceProvider
class IDCreatorService(object):
    u'''服务声明，服务IDCreatorService的默认提供者'''

    ID = 0

    def create_id(self, tag):
        u'''服务API: Services.IDCreatorService.IDCreatorService.create_id(tag) -> str '''

        self.ID += 1
        return '%s%s%s' % (abs(hash(tag)), int(time.time() * 1000000), self.ID)

    @signal_slot('IDMapper.reset')
    def reset(self, reset_to = 0):
        u'''事件响应：订阅IDMapper.reset事件'''

        self.ID = reset_to


@ServiceProvider('Cache')
class DemoCacheService(object): 
    u'''服务声明，为服务Cache添加一个服务提供者DemoCacheService

    API与Signal的定义与IDCreatorService类似。
    '''
    
    CACHE = {}

    def get(self, key, default = None):

        return self.CACHE.get(key, default)

    @signal_slot('CACHE.update')
    def set(self, key, value):

        self.CACHE[key] = value
        return {'key': key, 'value':value}

    @signal_slot('CACHE.remove')
    def remove(self, key):

        if key in self.CACHE:
            del self.CACHE[key]


@ServiceProvider(Services.Cache)
class DemoCacheEXService(object): 
    u'''服务声明，为服务Cache添加另一个服务提供者DemoCacheEXService

    与DemoCacheService不同之处在于，DemoCacheEXService使用另一个模式来实现API，这里称之为pass_raw模式'''
    
    HOST    = 'localhost:8678'
    CACHE   = {}

    @pass_raw
    def get(self, params, data):
        u'''使用pass_raw模式实现一个API

        params : 一些控制参数，比如传输协协议等
        data   : 原始数据包
        '''

        # 对数据进行解包
        kwargs = unpack_data(params.protocol, data)
        # CACHE操作
        result = self.CACHE.get(kwargs['key'], kwargs.get('default', None))
        # 数据封包
        result = pack_data(params.protocol, result)

        # 模拟同步调用异步
        # 默认情况，系统以同步方式调用API，并把API的返回结果发送回调用者
        # 但有时，服务提供者的API可能是异步执行的。即，API会立即结束，但不返回有效的结果，而是在后台处理完成后，通过回调的方式将结果返回给调用方
        # 在这种情况下，可以通过调用ServiceReplyProxy的方法，将回调结果发送给调用方，而不需要调用方单独提供回调接口。
        # 在调用者看来，API好像仍然是同步执行的一样。
        if params.wait_response and params.reply_to:
            # 通过RESTFul API调用ServiceReplyProxy
            # (params.reply_to, params.routing_key, params.correlation_id) 唯一确定了一次API调用
            url = 'http://' + self.HOST + '/Reply/%s/%s/%s' % (params.reply_to, params.routing_key, params.correlation_id)
            url += '?' + urllib.urlencode({'protocol' : params.protocol})
            urllib.urlopen(url, result).read()
            raise NotDoneYet()
        else:
            return params, result

    @pass_raw
    @signal_slot(Signals.CACHE.update)
    def set(self, params, data):
        u'''使用pass_raw模式实现一个事件监听器

        代码的模式与API类似'''

        kwargs  = unpack_data(params.protocol, data)
        key     = kwargs['key']
        value   = kwargs['value']

        self.CACHE[key] = value
        result  = {'key': key, 'value':self.CACHE[key]}
        result = pack_data(params.protocol, result)
        if params.wait_response and params.reply_to:
            url = 'http://' + self.HOST + '/Reply/%s/%s/%s' % (params.reply_to, params.routing_key, params.correlation_id)
            url += '?' + urllib.urlencode({'protocol' : params.protocol, '--req-data':result})
            urllib.urlopen(url).read()
            raise NotDoneYet()
        else:
            return params, result 

    @pass_raw
    @signal_slot(Signals.CACHE.remove)
    def remove(self, params, data):

        kwargs  = unpack_data(params.protocol, data)
        key     = kwargs['key']
        if key in self.CACHE:
            del self.CACHE[key]
        result = pack_data(params.protocol, None)
        if params.wait_response and params.reply_to:
            url = 'http://' + self.HOST + '/Reply/%s/%s/%s' % (params.reply_to, params.routing_key, params.correlation_id)
            url += '?' + urllib.urlencode({'protocol' : params.protocol, '--req-data':result})
            urllib.urlopen(url).read()
            raise NotDoneYet()
        else:
            return params, result 



if __name__ == '__main__':

    init_protocol()
    main_loop()
