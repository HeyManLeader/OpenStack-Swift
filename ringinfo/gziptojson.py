#!/usr/bin/env python
# -*-coding:utf-8-*-
# Author: xujianfeng_sx@qiyi.com
# Time  : 2016-7-20

from hashlib import md5

from swift.common.utils import json, get_logger, HASH_PATH_SUFFIX, HASH_PATH_PREFIX
from swift.common.ring.ring import Ring
from swift.common.swob import Response
from swift.proxy.controllers.base import Controller


"""
pipeline = catch_errors proxy-logging cache ringinfo proxy-server

[filter:ringinfo]
use = egg:ringinfo#ringinfo
"""


class GzipToJsonController(Controller):
    """Base WSGI controller for ring info requests."""
    server_type = 'RingInfo'

    def __init__(self, app, conf):
        Controller.__init__(self, app)
        self.conf = conf
        self.logger = get_logger(conf, log_route='ringinfo')
        self.swift_dir = self.conf.get('swift_dir', '/etc/swift')
        self.object_ring = Ring(self.swift_dir, ring_name='object')
        self.container_ring = Ring(self.swift_dir, ring_name='container')
        self.account_ring = Ring(self.swift_dir, ring_name='account')

    def _to_dict(self):
        return {
            'swift_hash_path_prefix': HASH_PATH_PREFIX,
            'swift_hash_path_suffix': HASH_PATH_SUFFIX,
            'object': {
                'devs': self.object_ring._devs,
                'replica2part2dev_id': [item.tolist() for item in self.object_ring._replica2part2dev_id],
                'part_shift': self.object_ring._part_shift
            },
            'container': {
                'devs': self.container_ring._devs,
                'replica2part2dev_id': [item.tolist() for item in self.container_ring._replica2part2dev_id],
                'part_shift': self.container_ring._part_shift
            },
            'account': {
                'devs': self.account_ring._devs,
                'replica2part2dev_id': [item.tolist() for item in self.account_ring._replica2part2dev_id],
                'part_shift': self.account_ring._part_shift
            }
        }

    def _reload(self):
        self.object_ring._reload()
        self.container_ring._reload()
        self.account_ring._reload()

    def _ringinfo_md5(self, json_file):
        calc_hash = md5()
        calc_hash.update(json_file)
        calc_hash_value = calc_hash.hexdigest()
        return calc_hash_value

    def GET(self, req):
        """
        Load ring data from .gz files.
        """

        self._reload()
        ring_info = self._to_dict()
        gz_file_to_ring_info = json.dumps(ring_info, sort_keys=True)
        ring_info_json_md5 = self._ringinfo_md5(gz_file_to_ring_info)

        resp = Response(request=req)
        resp.etag = ring_info_json_md5
        resp.content_length = len(gz_file_to_ring_info)
        resp.body = gz_file_to_ring_info
        resp.status_init = 200
        resp.content_type = 'application/json; charset=UTF-8'
        return resp