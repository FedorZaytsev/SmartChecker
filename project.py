import math
import json
import clustering
import numpy as np
import functools
import hashlib
import solution


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

class Project:
    def __init__(self, **kwargs):
        self.tests = {}
        self.all_solutions = {}
        self.cached_solutions = None
        self.skip_count = 0
        self.clusters = {}
        self.dimentions = None
        self.is_tl_hidden = True
        self.is_rt_hidden = True
        self.is_wa_hidden = True

        if 'file' in kwargs:
            data = json.load(kwargs['file'])
            self.clusters = dict((e['id'], e) for e in data['clusters'])
            self.all_solutions = dict((e['name']['file'], solution.Solution(self, obj=e)) for e in data['solutions'])
            self.tests = dict((e['name'], e) for e in data['tests'])

        if 'output' in kwargs:
            self.output = kwargs['output']

    def change_hidden_flags(self, tl=None, rt=None, wa=None):
        print('change_hidden_flags', tl, rt, wa)
        if tl is not None:
            self.is_tl_hidden = tl
        if rt is not None:
            self.is_rt_hidden = rt
        if wa is not None:
            self.is_wa_hidden = wa

        if tl is not None or rt is not None or wa is not None:
            self.drop_cache()

    def get_solutions(self):
        if self.cached_solutions is not None:
            return self.cached_solutions

        solutions = self.all_solutions
        print(self.is_tl_hidden, self.is_rt_hidden, self.is_wa_hidden)
        print('solutions0', len(list(solutions.keys())))
        if self.is_tl_hidden:
            solutions = dict((k, s) for k, s in solutions.items() if len(s.tl) == 0)

        print('solutions1', len(list(solutions.keys())))
        if self.is_rt_hidden:
            solutions = dict((k, s) for k, s in solutions.items() if len(s.rt) == 0)

        print('solutions2', len(list(solutions.keys())))
        if self.is_wa_hidden:
            solutions = dict((k, s) for k, s in solutions.items() if s.meta['status'] == 'PASSED_TESTS')

        print('solutions3', len(list(solutions.keys())))
        self.cached_solutions = solutions
        return self.cached_solutions

    def drop_cache(self):
        print("Project cache dropped")
        self.cached_solutions = None

    def drop_rt(self):
        assert False
        self.solutions = dict((k, s) for k, s in self.solutions.items() if len(s.rt) == 0)

    def drop_tl(self):
        assert False
        self.solutions = dict((k, s) for k, s in self.solutions.items() if len(s.tl) == 0)

    def drop_test_failed(self):
        assert False
        self.solutions = dict((k, s) for k, s in self.solutions.items() if s.meta['status'] == 'PASSED_TESTS')

    def is_tl_occured(self):
        for solution in self.all_solutions:
            if len(solution.tl) > 0:
                return True
        return False

    def is_rt_occured(self):
        for solution in self.all_solutions:
            if len(solution.rt) > 0:
                return True
        return False

    def size(self):
        return len(list(self.all_solutions.values()))

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
                 'av': default(np.median(
                     list(filter(lambda e: e != 1.0, [s.times[i] for s in self.get_solutions().values()]))))
                 } for i in range(self.get_count_tests())
            ],
            key=lambda x: x['av'], reverse=True
        )

        return data


    def sort_labels(self, labels):
        uniq, count = np.unique(labels, return_counts=True)
        data = list(map(lambda x: x[0], sorted(zip(uniq, count), key=lambda e: e[1], reverse=True)))
        print('data', data)
        labels = [data.index(e) for e in labels]
        print('labels', labels)

        return labels

    def get_dimentions(self):
        if self.dimentions is None:
            self.dimentions = self.calculate_dimentions()

        print('get_dimentions', self.dimentions)
        return self.dimentions

    def get_test_id(self, testname):
        assert testname in self.tests, 'Cannot find test for file {}'.format(testname)

        return self.tests[testname]['id']

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
        return list(map(lambda x: x[0], filter(lambda x: x[1] == idx, zip(self.get_solutions().values(),
                                                                          self.get_labels(

        )))))

    def get_cluster_info(self, idx):
        return self.clusters[idx]

    def get_count_tests(self):
        return len(list(self.tests))

    def get_times_by_test(self, idx):
        #print('cluster {} got {}'.format(idx, self.get_cluster(idx)))
        time = list(map(lambda x: x.times[self.skip_count:], self.get_cluster(idx)))

        return [[el[key - self.skip_count] for el in time] for key in range(self.skip_count, self.get_count_tests())]

    def get_times(self):
        return list(map(lambda s: s.times[self.skip_count:], self.get_solutions().values()))

    def update_tests(self, tests):
        new_tests = []
        for testname in tests:
            file_md5 = md5(testname)

            if testname not in self.tests:
                test = self.new_test(testname, self.get_count_tests(), file_md5=file_md5)
                self.tests[testname] = test
                new_tests.append(test)
            else:
                test = self.tests[testname]
                if test['md5'] != file_md5:
                    new_tests.append(test)
                    test['md5'] = file_md5
                    for solution in self.all_solutions:
                        solution.tests['time'][test['id']] = None

        return new_tests

    def new_test(self, testname, id, file_md5=None):
        if file_md5 is None:
            file_md5 = md5(testname)

        return {
            'name': testname,
            'md5': file_md5,
            'id': id,
        }

    def get_solution(self, source):
        if source['file'] not in self.all_solutions:
            s = solution.Solution(self, filename=source['file'])
            self.all_solutions[source['file']] = s
            self.drop_cache()

        return self.all_solutions[source['file']]

    def save(self):
        assert self.output is not None
        self.output.seek(0)
        self.output.truncate()
        json.dump({
            'tests': list(self.tests.values()),
            'solutions': [s.dump() for s in self.all_solutions.values()],
            'clusters': list(self.clusters.values()),
        }, self.output, sort_keys=True, indent=4)
        self.output.flush()



