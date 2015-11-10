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

from twisted.web import server, resource, static
from twisted.logger import Logger, LogLevel
from twisted.internet import reactor
from esb import *

log = Logger('Http-Proxy')

class ServiceRequest(object):

    def __init__(self, request):

        self.req    = request
        self.path   = request.path.strip('/').split('/')
        self.kwargs = {}
        self.data   = ''

        for k, v in request.args.iteritems():
            if k.startswith('--'):
                continue
            elif k == 'excludes':
                self.kwargs[k] = v
            else:
                self.kwargs[k] = ','.join(v)

        if '--req-data' in request.args:
            self.data = ''.join(request.args['--req-data'])
        else:
            self.data = request.content.read()


class ServiceResponse(object):

    def __init__(self, request,  res_defer):

        self.request    = request
        self.defer      = res_defer
        self.defer.addCallback(self.on_response)
        self.defer.addErrback(self.on_error_response)

    def on_response(self, response):

        if response:
            params, data = response
        else:
            data = 'OK'
        self.request.write(data)
        self.request.finish()


    def on_error_response(self, failure):

        log.failure('Response Error', failure, LogLevel.error)
        self.request.setResponseCode(500)
        self.request.write('<code>Error: %s</code>\n' % failure.getErrorMessage())
        self.request.write('<code><pre>%s</pre></code>\n' % failure.getTraceback())
        self.request.finish()


class RootResource(resource.Resource):

    isLeaf = False

    def getChild(self, name, request):

        if name == '':
            return self
        return resource.Resource.getChild(self, name, request)

    def render_GET(self, request):

        request.setHeader("content-type", "text/plain")
        return "welcome"


class ServiceResource(resource.Resource):
    """
        POST http://host:port/Services/ServiceName/ServiceProviderName/ApiName?extra_params=XXXX
             BODY: {'arg1':'xxx', 'arg2':'eeee'}
        or
        GET  http://host:port/Services/ServiceName/ServiceProviderName/ApiName?--req-data={'arg1':'xxx', 'arg2':'eeee'}&extra_params=XXXX
    """

    isLeaf = True

    def render(self, request):

        req     = ServiceRequest(request)
        proxy   = ServiceAPIProxy(*req.path[1:4])
        params  = ServiceParams(**req.kwargs)
        res     = ServiceResponse(request, proxy(params, req.data))        
        return server.NOT_DONE_YET


class SignalResource(resource.Resource):
    """
        POST http://host:port/Signals/ModelName/SignalName?extra_params=XXXX
             BODY: {'arg1':'xxx', 'arg2':'eeee'}
        or
        GET  http://host:port/Signals/ModelName/SignalName?--req-data={'arg1':'xxx', 'arg2':'eeee'}&extra_params=XXXX
    """

    isLeaf = True

    def render(self, request):
        
        req     = ServiceRequest(request)
        proxy   = SignalProxy(*req.path[1:3])
        params  = ServiceParams(**req.kwargs)
        res     = ServiceResponse(request, proxy(params, req.data))        
        return server.NOT_DONE_YET


class ReplyResource(resource.Resource):
    """
        POST http://host:port/Reply/reply_to/routing_key/correlation_id?extra_params=XXXX
             BODY: {'arg1':'xxx', 'arg2':'eeee'}
        or
        GET  http://host:port/Reply/reply_to/routing_key/correlation_id?--req-data={'arg1':'xxx', 'arg2':'eeee'}&extra_params=XXXX
    """

    isLeaf = True

    def render(self, request):
        
        req     = ServiceRequest(request)
        proxy   = ServiceReplyProxy()
        params  = ServiceParams(**req.kwargs)
        res     = ServiceResponse(request, proxy(*(req.path[1:4] + [params, req.data])))        
        return server.NOT_DONE_YET
        

def init_http_server(*args):

    log.info('InitHttpServer: %s' % (args,))
    root = RootResource()
    root.putChild('Services', ServiceResource())
    root.putChild('Signals', SignalResource())
    root.putChild('Reply', ReplyResource())
    #root.putChild('static', static.File(r'static'))
    reactor.listenTCP(8678, server.Site(root, logPath="log/access.log"))


if __name__ == '__main__':
    
    init_protocol().addCallback(init_http_server)
    main_loop()

