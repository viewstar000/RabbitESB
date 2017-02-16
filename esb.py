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

from common import *
from proxy import *
from provider import *

from twisted.logger import Logger, textFileLogObserver, globalLogBeginner

log = Logger('ESB')

@defer.inlineCallbacks
def run(connection):

    log.info('InitESB')
    yield init_providers(connection)
    yield ResponseCallback.get_instance().init(connection)
    yield ServiceAPIProxy.init((yield connection.channel()))
    yield SignalProxy.init((yield connection.channel()))
    yield ServiceReplyProxy.init((yield connection.channel()))

def init_protocol():

    log.info('InitRabbitMQConnection')
    parameters = pika.ConnectionParameters('localhost', 5672)
    cc = protocol.ClientCreator(reactor, twisted_connection.TwistedProtocolConnection, parameters)
    d = cc.connectTCP('localhost', 5672)
    d.addCallback(lambda protocol: protocol.ready)
    d.addCallback(run)
    return d

def main_loop():

    globalLogBeginner.beginLoggingTo([
        textFileLogObserver(open('log/esb.log', 'a'))
    ])
    reactor.run()


if __name__ == '__main__':

    init_protocol()
    main_loop()