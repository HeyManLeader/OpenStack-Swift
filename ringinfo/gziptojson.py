#!/usr/bin/env python
# -*-coding:utf-8-*-
# Author: xujianfeng_sx@qiyi.com
# Time  : 2016-7-20


import array
import cPickle as pickle
from gzip import GzipFile
import struct
from io import BufferedReader
from swift.common.utils import json
from swift.common.ring.ring import RingData
from hashlib import md5
from swift.proxy.controllers.base import Controller
from swift.common.utils import get_logger
from swift.common.swob import HTTPOk, Response

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
        self.ring_files_type = conf.get('ring_files_type')

    def _deserialize_v1(self, gz_file):
        json_len, = struct.unpack('!I', gz_file.read(4))
        ring_dict = json.loads(gz_file.read(json_len))
        ring_dict['replica2part2dev_id'] = []
        partition_count = 1 << (32 - ring_dict['part_shift'])
        for x in xrange(ring_dict['replica_count']):
            ring_dict['replica2part2dev_id'].append(
                list(array.array('H', gz_file.read(2 * partition_count))))
        return ring_dict

    def _to_dict(self, ringdata):
        return {'devs': ringdata.devs,
                'replica2part2dev_id': ringdata._replica2part2dev_id,
                'part_shift': ringdata._part_shift
               }

    def _ringinfo_md5(self, json_file):
        calc_hash = md5()
        calc_hash.update(json_file)
        calc_hash_value = calc_hash.hexdigest()
        return calc_hash_value

    def GET(self, req):
        """
        Load ring data from .gz files.
        """

        ring_info = {}
        for ring_file in self.ring_files_type.keys():
            gz_filename = self.ring_files_type[ring_file]
            gz_file = GzipFile(gz_filename, 'rb')
            # Python 2.6 GzipFile doesn't support BufferedIO
            if hasattr(gz_file, '_checkReadable'):
                gz_file = BufferedReader(gz_file)

            # See if the file is in the new format
            magic = gz_file.read(4)
            if magic == 'R1NG':
                version, = struct.unpack('!H', gz_file.read(2))
                if version == 1:
                    ring_data = self._deserialize_v1(gz_file)
                else:
                    self.logger.error('Unknown ring format version %(val)'.format({'val': version}))
                    raise Exception('Unknown ring format version %(val)'.format(version))
            else:
                # Assume old-style pickled ring
                gz_file.seek(0)
                ring_data = pickle.load(gz_file)
            if not hasattr(ring_data, 'devs'):
                ring_data = RingData(ring_data['replica2part2dev_id'],
                                     ring_data['devs'], ring_data['part_shift'])
            if dict != type(ring_data):
                ring_data = self._to_dict(ring_data)
            ring_info[ring_file] = ring_data

        gz_file_to_ring_info = json.dumps(ring_info, sort_keys=True)
        ring_info_json_md5 = self._ringinfo_md5(gz_file_to_ring_info)

        resp = Response(request=req)
        resp.etag = ring_info_json_md5
        resp.content_length = len(gz_file_to_ring_info)
        resp.body = gz_file_to_ring_info
        resp.status_init = 200
        resp.content_type = 'application/json; charset=UTF-8'
        return resp
