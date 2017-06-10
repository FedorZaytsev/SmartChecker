import hashlib
import json


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


class Test:
    def __init__(self, name=None, id=None, file_md5=None, obj=None):
        if obj is not None:
            self.name = obj['name']
            self.id = obj['id']
            self.md5 = obj['md5']
        else:
            self.name = name
            self.id = id
            if file_md5 is None:
                self.md5 = md5(name)
            else:
                self.md5 = file_md5

    def dump(self):
        return {
            'name': self.name,
            'id': self.id,
            'md5': self.md5,
        }

    def __repr__(self):
        return json.dumps(self.dump(), indent=2, sort_keys=True)
