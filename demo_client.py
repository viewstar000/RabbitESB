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
'''


from esb import *

@defer.inlineCallbacks
def main(*args, **kwargs):
    u'''服务调用方DEMO

    基于Twisted框架提供的异步执行机制，详见：[PEP 0342](https://www.python.org/dev/peps/pep-0342/)'''

    # 创建服务代理
    IDCreator = Services.IDCreatorService()

    # 循环调用十次
    for i in range(10):

        # 调用服务API，同步方式，等待结果返回。
        print (yield IDCreator.create_id(tag = 'a')) 

        # 调用服务API，异步方式，不等待结果返回。
        IDCreator.create_id(ServiceParams(wait_response = False), tag = 'a')

        # 触发事件：IDMapper.reset，同步方式，指接收者为IDCreatorService，并等待结果返回
        print (yield Singals.IDMapper.reset(ServiceParams(sync_to = 'IDCreatorService'), reset_to = i))

        # 触发事件：IDMapper.reset，异步方式，发送给除IDCreatorService以外的接收者，不等待结果返回        
        Singals.IDMapper.reset(ServiceParams(excludes = ['IDCreatorService']), reset_to = i)

        # 触发事件：IDMapper.reset，异步方式，发送给所有接收者
        Singals.IDMapper.reset(reset_to = i)


if __name__ == '__main__':
    
    init_protocol().addCallback(main)
    main_loop()