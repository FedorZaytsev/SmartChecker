import math
import json
import clustering
import numpy as np
import functools


class Project:
    def __init__(self, **kwargs):
        if 'file' in kwargs:
            data = json.load(kwargs['file'])
            self.count_tests = data['count_tests']
            self.clusters = data['clusters']
            self.data = data['data']
            self.tests = data['tests']
            self.dimentions = self.calculate_dimentions()
            self.skip_count = 30
            print('dimentions', self.dimentions)


    def drop_rt(self):
        self.data = list(filter(lambda el: len(el['tests']['rt']) == 0, self.data))

    def drop_tl(self):
        self.data = list(filter(lambda el: len(el['tests']['tl']) == 0, self.data))

    def drop_test_failed(self):
        self.data = list(filter(lambda el: el['name']['meta']['status'] == 'PASSED_TESTS', self.data))

    def size(self):
        return len(self.data)

    def cluster_count(self):
        if len(self.clusters) == 0:
            return 1
        return len(self.clusters)

    def calculate_dimentions(self):
        def default(val):
            if math.isnan(val):
                return 1.0
            return val

        data = sorted(
            [
                {'i': i,
                 'av': default(np.median(list(filter(lambda e: e != 1.0, [el['tests']['time'][i] for el in
                                                                          self.data]))))
                 } for i in range(self.count_tests)
            ],
            key=lambda x: x['av'], reverse=True
        )
        print('calculate_dimentions', data)
        return data

    def sort_labels(self, labels):
        uniq, count = np.unique(labels, return_counts=True)
        data = list(map(lambda x: x[0], sorted(zip(uniq, count), key=lambda e: e[1], reverse=True)))
        print('data', data)
        labels = [data.index(e) for e in labels]
        print('labels', labels)

        return labels



    def clusterize(self, count):
        labels = clustering.clusterize(self, kmax=count)
        labels = self.sort_labels(labels)
        self.clusters = [{
                             'id': e,
                             'name': 'cluster {}'.format(e),
                             'description': '',
                             'elements': [],
                         } for e in range(max(labels)+1)]
        for idx, label in enumerate(labels):
            self.clusters[label]['elements'].append(idx)

    def get_labels(self):
        labels = [0 for i in range(len(self.get_times()))]
        for cluster in self.clusters:
            for idx in cluster['elements']:
                labels[idx] = cluster['id']

        return labels



    def get_cluster(self, idx):
        return list(map(lambda x: x[0], filter(lambda x: x[1] == idx, zip(self.data, self.get_labels()))))

    def get_cluster_info(self, idx):
        return self.clusters[idx]

    def get_times_by_test(self, idx):
        time = list(map(lambda x: x['tests']['time'][self.skip_count:],
                        filter(lambda x: not x['tests']['tl'], self.get_cluster(idx))))

        return [[el[key - self.skip_count] for el in time] for key in range(self.skip_count, self.count_tests)]

    def get_times(self):
        return list(map(lambda x: x['tests']['time'][self.skip_count:], self.data))

    #def get_cluster_count(self):
    #    return np.unique(self.data.get_labels())

    def save(self, output):
        json.dump({
            'count_tests': self.count_tests,
            'data': self.data,
            'clusters': self.clusters,
        }, output, sort_keys=True, indent=4)



