import re
import os
import json
from settings import *


def parse_filename(filename):
    data = list(filter(len, re.split("\((.*?)\)", filename)))
    assert len(data) == 6, 'Unknown file name {}'.format(filename)
    return {'username':data[1], 'date':data[2], 'status': data[3], 'plagiat': data[4], 'ext':data[5]}


def safe_set(lst, idx, value):
    if idx >= len(lst):
        for i in range(len(lst), idx+1):
            lst.append(None)
    lst[idx] = value


class Solution:
    def __init__(self, project, filename=None, obj=None):
        self.project = project
        self.times = []
        self.rt = []
        self.tl = []

        if filename is not None:
            self.filepath = filename
            self.filename = os.path.split(filename)[1]
            self.meta = parse_filename(filename)

        if obj is not None:
            self.filepath = obj['name']['file']
            self.filename = obj['name']['filename']
            self.meta = obj['name']['meta']

            self.times = obj['tests']['time']
            self.rt = obj['tests']['rt']
            self.tl = obj['tests']['tl']

    def set_test(self, test, time=None, timeout=None, runtime=None):
        test_id = self.project.get_test_id(test.name)

        if timeout is not None:
            self.tl.append(test_id)
            time = float(config['tests']['timeout']) * 1000

        if runtime is not None:
            self.rt.append(test_id)
            time = float(config['tests']['timeout']) * 1000

        safe_set(self.times, test_id, time)
        self.project.drop_cache()

    def dump(self):
        return {
            'name': {
                'file': self.filepath,
                'filename': self.filename,
                'meta': self.meta,
            },
            'tests': {
                'time': self.times,
                'tl': self.tl,
                'rt': self.rt,
            }
        }

    def get_source(self):
        return {
            'file': self.filepath,
            'filename': self.filename,
            'meta': self.meta,
        }


    def __repr__(self):
        return json.dumps(self.dump(), indent=2, sort_keys=True)




