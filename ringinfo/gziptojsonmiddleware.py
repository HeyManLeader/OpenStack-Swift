#!/usr/bin/env python
# -*-coding:utf-8-*-
# Author: xujianfeng_sx@qiyi.com
# Time  : 2016-7-20

from swift.common.utils import get_logger
from swift.common.constraints import check_utf8
from swift.common.swob import HTTPBadRequest, HTTPPreconditionFailed, \
    HTTPServerError, Request, HTTPMethodNotAllowed, HTTPException
from ringinfo.gziptojson import GzipToJsonController


class GzipToJsonMiddleware(object):
    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
        if conf is None:
            self.conf = {}
        self.logger = get_logger(conf, log_route='proxy-server')
        self.controller = GzipToJsonController(app=self.app, conf=self.conf)

    def handler_request(self, req):
        try:
            try:
                if not check_utf8(req.path_info):
                    return HTTPPreconditionFailed(
                        request=req, body='Invalid UTF8 or contains NULL')
            except UnicodeError:
                return HTTPPreconditionFailed(
                    request=req, body='Invalid UTF8 or contains NULL')

            try:
                handler = getattr(self.controller, req.method)
                return handler(req)
            except AttributeError:
                return HTTPMethodNotAllowed(request=req, headers={'Allow': 'GET'})
            return HTTPBadRequest(request=req)
        except HTTPException as error_response:
            return error_response
        except (Exception, Timeout):
            self.logger.exception('ERROR Unhandled exception in request')
            return HTTPServerError(request=req)

    def __call__(self, env, start_response):
        req = Request(env)
        if req.method == 'GET' and req.path == '/ringinfo':
            return self.handler_request(req)(env, start_response)
        else:
            return self.app(env, start_response)


def filter_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)

    def gziptojson_filter(app):
        return GzipToJsonMiddleware(app, conf)

    return gziptojson_filter
