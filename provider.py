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
from proxy import *

log = Logger('Service-Provider')

class NotDoneYet(Exception):pass

PROVIDER_LIST   = {}

@defer.inlineCallbacks
def init_providers(connection):

    for provider_class in PROVIDER_LIST.itervalues():

        log.info('Register %s' % (provider_class))
        service_name        = provider_class.__service_name__
        provider_name       = provider_class.__provider_name__
        provider_instance   = provider_class()

        channel = yield connection.channel()
        yield channel.exchange_declare(exchange='Service' + service_name, type='topic', durable=True)
        yield channel.queue_declare(queue='Provider' + provider_name, durable=True)
        yield channel.queue_bind(exchange='Service' + service_name, queue='Provider' + provider_name, routing_key='Services.'+service_name+'.'+provider_name+'.#')
        yield channel.basic_qos(prefetch_count=1)

        for name, attr in provider_class.__dict__.iteritems():
            if callable(attr) and hasattr(attr, 'slots') and attr.slots:
                for (model_name, signal_name) in attr.slots:
                    log.info('RegisterSignalSlot: %s.%s -> %s' % (model_name, signal_name, attr))
                    yield channel.exchange_declare(exchange='ServiceModel' + model_name, type='topic', durable=True)
                    yield channel.queue_bind(exchange='ServiceModel' + model_name, queue='Provider' + provider_name, routing_key='Signals.'+model_name+'.'+signal_name)
                    yield channel.queue_bind(exchange='ServiceModel' + model_name, queue='Provider' + provider_name, routing_key='Signals.'+model_name+'.'+signal_name+'.'+provider_name)

        queue_object, consumer_tag = yield channel.basic_consume(queue='Provider' + provider_name, no_ack=True)
        l = task.LoopingCall(ServiceCallback(provider_instance), queue_object)
        l.start(0)
        

def ServiceProvider(service = None):

    def wrap(provider_class):
        if not service:
            service_name = provider_class.__name__
        elif not isinstance(service, (str, unicode)):
            service_name = service.__service_name__
        else:
            service_name = service
        provider_class.__service_name__ = service_name
        provider_class.__provider_name__ = provider_class.__name__
        PROVIDER_LIST[(service_name, provider_class.__provider_name__)] = provider_class
        return provider_class

    if service and not isinstance(service, ServiceProxy) and not isinstance(service, (str, unicode)):
        provider = service
        service  = None
        return wrap(provider)
    else:
        return wrap


def signal_slot(signal):

    def wrap(slot):

        if isinstance(signal, (str, unicode)):
            model_name, signal_name = tuple(signal.split('.'))
        else:
            model_name  = signal.__model_name__
            signal_name = signal.__signal_name__
        if hasattr(slot, 'slots'):
            slot.slots.append((model_name, signal_name))
        else:
            slot.slots = [(model_name, signal_name)]
        return slot

    return wrap


def pass_raw(func):

    func.pass_raw = True

    return func  


class ServiceCallback(object):

    log = Logger()

    def __init__(self, provider_instance):

        self.provider   = provider_instance
        self.slots      = {}
        for name, attr in type(self.provider).__dict__.iteritems():
            if callable(attr) and hasattr(attr, 'slots') and attr.slots:
                for slot in attr.slots:
                    self.slots[tuple(slot)] = attr

    @defer.inlineCallbacks
    def __call__(self, queue_object):

        self.log.info('ServiceCallback: wait for new message ...')
        channel, method, properties, body = yield queue_object.get()

        self.log.info('ServiceCallback: Recv Message %s' % (properties.headers,))
        result      = ''
        params      = ServiceParams().from_properties(properties)
        routing_key = params.routing_key.split('.')
        
        if self.provider.__provider_name__ in params.excludes:
            return
        try:
            if len(routing_key) >= 4 and routing_key[0] == 'Services':
                res_params, result = yield self.api_callback(routing_key, params, body)
            elif len(routing_key) >= 3 and routing_key[0] == 'Signals':
                res_params, result = yield self.signal_callback(routing_key, params, body)
            else:
                raise RuntimeError('UnknownRoutingKey: %s' % (params.routing_key,))
        except NotDoneYet:
            raise StopIteration()
        except:
            # TODO find the real stack
            self.log.failure('Callback Error:', level = LogLevel.error)
            E, e, t      = sys.exc_info()
            res_params  = ServiceParams(error = "%s: %s" % (E.__name__, e))
            result      = ''

        res_params.reply_to = params.reply_to
        res_params.correlation_id = params.correlation_id

        if params.reply_to:
            proxy = ServiceReplyProxy()
            yield proxy(params.reply_to, params.routing_key, params.correlation_id, res_params, result)

        if params.callback:
            routing_key                 = params.callback.split('.')
            res_params.wait_response    = False
            res_params.routing_key      = params.callback
            res_params.response_from    = params.routing_key
            res_params.callback         = ''
            if routing_key[0] == 'Services':
                proxy = ServiceAPIProxy(*routing_key[1:4])
            elif routing_key[0] == 'Signals':
                proxy = SignalProxy(*routing_key[1:3])
            else:
                self.log.error('UnknownRoutingKey: %s for callback' % (routing_key,))
                return
            yield proxy(res_params, result)


    @defer.inlineCallbacks
    def api_callback(self, routing_key, params, body):

        result          = ''
        service_name    = routing_key[1]
        provider_name   = routing_key[2]
        api_name        = routing_key[3]

        assert service_name == self.provider.__service_name__ , 'UnknownServiceName: %s' % (service_name,)
        assert provider_name == self.provider.__provider_name__ , 'UnknownProviderName: %s' % (provider_name,)
        assert hasattr(self.provider, api_name) and callable(getattr(self.provider, api_name)) , 'UnknownAPIName: %s' % (api_name,)
        provider_api = getattr(self.provider, api_name)
        
        self.log.info('CallAPI: %s' % (provider_api,))
        if hasattr(provider_api, 'pass_raw') and provider_api.pass_raw:
            self.log.debug('CallAPI: call api in pass_raw mode: {data}', data = body)
            params, result = yield provider_api(params, body)
        else:
            self.log.debug('CallAPI: call api in unpack mode: {data}', data = body)
            result = pack_data(params.protocol, (yield provider_api(**unpack_data(params.protocol, body))))
        self.log.debug('CallAPI: return api result: {data}', data = result)
        defer.returnValue((params, result))

    @defer.inlineCallbacks
    def signal_callback(self, routing_key, params, body):

        result      = ''
        model_name  = routing_key[1]
        signal_name = routing_key[2]

        if (model_name, signal_name) in self.slots:
            slot = self.slots[(model_name, signal_name)]
            self.log.info('CallSlot: %s' % (slot,))
            if hasattr(slot, 'pass_raw') and slot.pass_raw:
                self.log.debug('CallSlot: call slot in pass_raw {data}', data = body)
                params, result = yield slot(self.provider, params, body)
            else:
                self.log.debug('CallSlot: call slot in unpack {data}', data = body)
                result = pack_data(params.protocol, (yield slot(self.provider, **unpack_data(params.protocol, body))))
        else:
            raise RuntimeError('UnsupportSignal: %s.%s' % (model_name, signal_name))
        self.log.debug('CallSlot: return slot result: {data}', data = result)
        defer.returnValue((params, result))


