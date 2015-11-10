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

import sys
import pika
import json
import uuid
import time

from pika import exceptions
from pika.adapters import twisted_connection
from twisted.internet import defer, reactor, protocol, task
from twisted.logger import Logger, LogLevel
from common import *

log = Logger('Service-Proxy')

#########################################################################################

class ServicesProxy(object):

    def __str__(self):

        return 'Services'

    def __getattr__(self, name):

        return ServiceProxy(name)


class ServiceProxy(object):

    def __init__(self, name):

        self.__service_name__ = name

    def __str__(self):

        return self.__service_name__

    def __getattr__(self, name):

        if name == 'default':
            name = self.__service_name__
        return ServiceProviderProxy(self.__service_name__, name)

    def __call__(self, name = 'default'):

        return getattr(self, name)


class ServiceProviderProxy(object):

    def __init__(self, service_name, provider_name):

        self.__service_name__   = service_name
        self.__provider_name__  = provider_name

    def __str__(self):

        return self.__provider_name__


    def __getattr__(self, name):

        return ServiceAPIProxy(self.__service_name__, self.__provider_name__, name)

    def __call__(self):

        return self


class ServiceAPIProxy(object):

    log     = Logger()
    channel = None

    @classmethod
    def init(cls, channel):

        cls.log.info('ServiceAPIProxy: init using %s' % (channel))
        cls.channel = channel

    def __init__(self, service_name, provider_name, api_name):

        self.__service_name__   = service_name
        self.__provider_name__  = provider_name
        self.__api_name__       = api_name

    def __str__(self):

        return self.__api_name__

    @defer.inlineCallbacks
    def __call__(self, *args, **kwargs):

        self.log.info('CallServiceAPI: %s.%s.%s' % (self.__service_name__, self.__provider_name__, self.__api_name__))
        start_time  = time.time()
        params      = None
        pass_raw    = False
        body        = ''

        if len(args) >= 1:
            params  = args[0]
        else:
            params  = ServiceParams()

        if len(args) >= 2:
            pass_raw    = True
            body        = args[1]
        else:
            pass_raw    = False
            body        = pack_data(params.protocol, kwargs)

        params.routing_key  = params.routing_key or 'Services.'+self.__service_name__+'.'+self.__provider_name__+'.'+self.__api_name__
        properties          = params.to_properties()

        if params.wait_response:
            response                    = AsyncResponse(params.routing_key)
            properties.reply_to         = response.queue
            properties.correlation_id   = response.correlation_id

        self.log.debug('CallServiceAPI: send request to %s' % (params.routing_key,))
        self.log.debug('CallServiceAPI: send request pass_raw: %s, routing_key: %s, body: %s ' % (pass_raw, params.routing_key, body))
        yield self.channel.basic_publish(   exchange    = 'Service' + self.__service_name__, 
                                            routing_key = params.routing_key, 
                                            body        = body, 
                                            properties  = properties)
        self.log.debug('CallServiceAPI: Send request DONE')

        if params.wait_response:
            properties, body = yield response.wait()
            use_time = time.time() - start_time
            self.log.info('CallServiceAPI: [PROFILE] Recv API Response in %s ms' % (use_time * 1000, ))
            params = ServiceParams().from_properties(properties)
            if params.error:
                raise RuntimeError('RemoteServiceError: %s' % (params.error,))
            if pass_raw:
                self.log.debug('CallServiceAPI: return result %s in pass_raw mode' % (body,))
                defer.returnValue((params, body))
            else:
                self.log.debug('CallServiceAPI: return result %s in unpack mode' % (body,))
                defer.returnValue(unpack_data(params.protocol, body))

#########################################################################################

class ServiceModelsProxy(object):

    def __init__(self):

        self.models = {}

    def __str__(self):

        return 'ServiceModels'

    def __getattr__(self, name):

        if name not in self.models:
            self.models[name] = ServiceModelProxy(name)
        return self.models[name] 


class ServiceModelProxy(object):

    def __init__(self, name):

        self.__model_name__ = name
        self.signals = {}

    def __str__(self):

        return self.__model_name__

    def __getattr__(self, name):

        if name not in self.signals:
            self.signals[name] = SignalProxy(self.__model_name__, name)
        return self.signals[name] 
        

class SignalProxy(object):

    log     = Logger()
    channel = None

    @classmethod
    def init(cls, channel):

        cls.log.info('SignalProxy: init using %s' % (channel))
        cls.channel = channel

    def __init__(self, model_name, signal_name):
        
        self.__model_name__     = model_name
        self.__signal_name__    = signal_name
        self.__excludes         = []

    def __str__(self):

        return self.__signal_name__

    @defer.inlineCallbacks
    def __call__(self, *args, **kwargs):

        self.log.info('EmitSignal: %s.%s' % (self.__model_name__, self.__signal_name__))
        start_time  = time.time()
        params      = None
        pass_raw    = False
        body        = ''

        if len(args) >= 1:
            params  = args[0]
        else:
            params  = ServiceParams()

        if len(args) >= 2:
            pass_raw    = True
            body        = args[1]
        else:
            pass_raw    = False
            body        = pack_data(params.protocol, kwargs)

        params.routing_key  = 'Signals.'+self.__model_name__+'.'+self.__signal_name__
        if params.sync_to:
            params.routing_key += '.' + str(params.sync_to)

        properties = params.to_properties()

        if params.sync_to and params.wait_response:
            response                    = AsyncResponse(params.routing_key)
            properties.reply_to         = response.queue
            properties.correlation_id   = response.correlation_id

        self.log.debug('EmitSignal: send signal to %s' % (params.routing_key,))
        self.log.debug('EmitSignal: send signal pass_raw: %s, routing_key: %s, body: %s ' % (pass_raw, params.routing_key, body))
        yield self.channel.basic_publish(   exchange    = 'ServiceModel' + self.__model_name__, 
                                            routing_key = params.routing_key, 
                                            body        = body, 
                                            properties  = properties)
        self.log.debug('EmitSignal: send signal DONE')
        
        if params.sync_to and params.wait_response:
            properties, body    = yield response.wait()
            use_time            = time.time() - start_time
            self.log.info('EmitSignal: [PROFILE] Recv Signal Response in %s ms' % (use_time * 1000, ))
            params = ServiceParams().from_properties(properties)
            if params.error:
                raise RuntimeError('RemoteServiceError: %s' % (params.error,))
            if pass_raw:
                self.log.debug('EmitSignal: return result %s in pass_raw mode' % (body,))
                defer.returnValue((params, body))
            else:
                self.log.debug('EmitSignal: return result %s in unpack mode' % (body,))
                defer.returnValue(unpack_data(params.protocol, body))


#########################################################################################

class ServiceReplyProxy(object):

    log     = Logger()
    channel = None

    @classmethod
    def init(cls, channel):

        cls.log.info('ServiceReplyProxy: init using %s' % (channel))
        cls.channel = channel

    @defer.inlineCallbacks
    def __call__(self, reply_to, routing_key, correlation_id, *args, **kwargs):

        self.log.info('ServiceReplyProxy: %s %s %s' % (reply_to, routing_key, correlation_id))
        params      = None
        pass_raw    = False
        body        = ''

        if len(args) >= 1:
            params  = args[0]
        else:
            params  = ServiceParams()

        if len(args) >= 2:
            pass_raw    = True
            body        = args[1]
        else:
            pass_raw    = False
            body        = pack_data(params.protocol, kwargs)

        params.routing_key          = routing_key
        params.reply_to             = reply_to
        params.correlation_id       = correlation_id
        params.response_from        = params.response_from or routing_key
        properties                  = params.to_properties()
        properties.reply_to         = None
        properties.correlation_id   = params.correlation_id
        
        self.log.debug('ServiceReplyProxy: Send Reply %s to %s for %s' % (properties, params.reply_to, params.correlation_id))
        self.log.debug('ServiceReplyProxy: Send Reply %s to %s' % (body, params.reply_to))
        yield self.channel.basic_publish(   exchange    = '',
                                            routing_key = params.reply_to,
                                            properties  = properties,
                                            body        = body)
        self.log.debug('ServiceReplyProxy: Send Reply DONE')

#########################################################################################

class ServiceParams(object):

    def __init__(self, 
                protocol        = 'JSON', 
                routing_key     = '', 
                excludes        = [], 
                response_from   = '',
                callback        = '', 
                error           = '',
                wait_response   = True, 
                sync_to         = None, 
                correlation_id  = None, 
                reply_to        = None):

        self.protocol       = protocol
        self.routing_key    = routing_key
        self.excludes       = excludes
        self.response_from  = response_from     # for inner use
        self.callback       = callback
        self.error          = error
        self.wait_response  = wait_response
        self.sync_to        = sync_to
        self.correlation_id = correlation_id
        self.reply_to       = reply_to

    def to_properties(self):

        headers = {
            'protocol'      : self.protocol,
            'routing_key'   : self.routing_key,
            'excludes'      : ','.join(map(str, self.excludes)),
            'response_from' : self.response_from,
            'callback'      : self.callback,
            'error'         : self.error,
        }
        props   = {
            'headers'   : headers,
        }
        return pika.BasicProperties(**props)

    def from_properties(self, properties):

        self.protocol       = properties.headers.get('protocol', 'JSON')
        self.routing_key    = properties.headers.get('routing_key', '')
        self.excludes       = properties.headers.get('excludes', '').split(',')
        self.response_from  = properties.headers.get('response_from', '')
        self.callback       = properties.headers.get('callback', '')
        self.error          = properties.headers.get('error', '')
        self.correlation_id = properties.correlation_id
        self.reply_to       = properties.reply_to
        return self


class ResponseCallback(object):

    log             = Logger()
    __callback_map  = {}
    __instance      = None
    __channel       = None
    __queue         = None

    @classmethod
    def get_instance(cls):

        if not cls.__instance:
            cls.__instance = cls()
        return cls.__instance

    @classmethod
    def get_response(cls, response_from, correlation_id = None):

        callback        = defer.Deferred()
        correlation_id  = correlation_id or str(uuid.uuid4())
        cls.__callback_map[(response_from, correlation_id)] = callback
        return response_from, correlation_id, cls.__queue.method.queue, callback

    @defer.inlineCallbacks
    def init(self, connection):

        self.log.info('ResponseCallback: init using %s' % (connection))
        ResponseCallback.__channel = yield connection.channel()
        self.log.info('ResponseCallback: init queue using %s' % (ResponseCallback.__channel))
        ResponseCallback.__queue   = yield ResponseCallback.__channel.queue_declare(exclusive=True)
        self.log.info('ResponseCallback: queue inited %s' % (ResponseCallback.__queue))
        yield ResponseCallback.__channel.basic_qos(prefetch_count=1)

        queue_object, consumer_tag = yield ResponseCallback.__channel.basic_consume(queue = ResponseCallback.__queue.method.queue, no_ack=True)
        l = task.LoopingCall(self.callback, queue_object)
        l.start(0)

    @defer.inlineCallbacks
    def callback(self, queue_object):

        self.log.info('ResponseCallback: wait for new message ...')
        channel, method, properties, body = yield queue_object.get()

        self.log.info('ResponseCallback: Recv Response %s, %s' % (properties.correlation_id, properties.headers, ))
        self.log.debug('ResponseCallback: Recv Response %s, %s' % (properties, body, ))
        headers         = properties.headers
        response_from   = headers.get('response_from', '')
        correlation_id  = properties.correlation_id

        if (response_from, correlation_id) in ResponseCallback.__callback_map:
            callback = ResponseCallback.__callback_map[(response_from, correlation_id)]
            del ResponseCallback.__callback_map[(response_from, correlation_id)]
            self.log.info('ResponseCallback: triger callback for reponse from %s with %s' % (response_from, correlation_id))
            callback.callback((properties, body))
        else:
            self.log.warn('ResponseCallback: callback for reponse from %s with %s not exists !' % (response_from, correlation_id))


class AsyncResponse(object):

    def __init__(self, response_from, correlation_id = None):

        self.response_from, self.correlation_id, self.queue, self.callback = ResponseCallback.get_response(response_from, correlation_id)

    def wait(self):

        return self.callback

Signals     = ServiceModelsProxy()
Services    = ServicesProxy()

