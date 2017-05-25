

class Cluster:
    def __init__(self, obj=None, idx=None, name=None, description=None, center=None):
        self.id = idx
        self.name = name
        self.description = description
        self.elements = []
        self.center = center

        if obj is not None:
            self.id = obj['id']
            self.name = obj['name']
            self.description = obj['description']
            self.elements = obj['elements']
            self.center = obj.get('center', None)

    def dump(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'elements': self.elements,
            'center': self.center,
        }

