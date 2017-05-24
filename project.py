import math
import json
import clustering
import numpy as np
import solution
import fetch
import os
import test as test_f


class Project:
    def __init__(self, **kwargs):
        self.tests = {}
        self.all_solutions = {}
        self.name = 'NO NAME'
        self.cached_solutions = None
        self.skip_count = 0
        self.clusters = {}
        self.cluster_size = 0
        self.dimentions = None
        self.output = None
        self.is_tl_hidden = True
        self.is_rt_hidden = True
        self.is_wa_hidden = True
        self.is_changed = False
        self.sources_path = ''
        self.tests_path = ''

        if 'file' in kwargs:
            data = json.load(kwargs['file'])
            self.clusters = data['clusters']
            self.all_solutions = dict((e['name']['file'], solution.Solution(self, obj=e)) for e in data['solutions'])
            self.tests = dict((e['name'], test_f.Test(obj=e)) for e in data['tests'])
            self.is_tl_hidden = data.get('is_tl_hidden', True)
            self.is_rt_hidden = data.get('is_rt_hidden', True)
            self.is_wa_hidden = data.get('is_wa_hidden', True)
            self.cluster_size = data.get('cluster_size', 0)
            self.name = data.get('name', 'NO NAME')
            self.sources_path = data.get('sources_path',
                                         os.path.split(list(self.all_solutions.values())[0].filepath)[0])
            self.tests_path = data.get('tests_path',
                                       os.path.split(list(self.tests.values())[0].name)[0])

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
            self.is_changed = True
            self.drop_cache()

    def get_solutions(self):
        if self.cached_solutions is not None:
            return self.cached_solutions

        solutions = self.all_solutions
        if self.is_tl_hidden:
            solutions = dict((k, s) for k, s in solutions.items() if len(s.tl) == 0)

        if self.is_rt_hidden:
            solutions = dict((k, s) for k, s in solutions.items() if len(s.rt) == 0)

        if self.is_wa_hidden:
            solutions = dict((k, s) for k, s in solutions.items() if s.meta['status'] == 'PASSED_TESTS')

        self.cached_solutions = solutions
        return self.cached_solutions

    def drop_cache(self):
        self.cached_solutions = None
        self.is_changed = True

    def current_cluster_name(self, count=None):
        if count is None:
            count = self.cluster_size
        return "{}_{}_{}_{}".format(self.is_rt_hidden, self.is_wa_hidden, self.is_tl_hidden, count)

    def update_current_cluster_name(self, count):
        self.cluster_size = count

    def get_clusters(self):
        if self.cluster_size == 0:
            return []
        return self.clusters[self.current_cluster_name()]

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
        return len(list(self.get_solutions().values()))

    def cluster_count(self):
        return max(len(self.get_clusters()), 1)

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
        labels = [data.index(e) for e in labels]

        return labels

    def get_dimentions(self):
        if self.dimentions is None:
            self.dimentions = self.calculate_dimentions()

        #print('get_dimentions', self.dimentions)
        return self.dimentions

    def get_test_id(self, testname):
        assert testname in self.tests, 'Cannot find test for file {}'.format(testname)

        return self.tests[testname].id

    def clusterize(self, count):
        #if count == len(self.clusters):
        #    return
        if self.current_cluster_name(count) in self.clusters:
            self.update_current_cluster_name(count)
            self.is_changed = True
            return


        self.update_current_cluster_name(count)
        labels = clustering.clusterize(self, kmax=count)
        labels = self.sort_labels(labels)
        self.is_changed = True
        cluster_name = self.current_cluster_name()
        self.clusters[cluster_name] = [{
                             'id': e,
                             'name': 'cluster {}'.format(e),
                             'description': '',
                             'elements': [],
                         } for e in range(max(labels)+1)]
        for idx, label in enumerate(labels):
            self.clusters[cluster_name][label]['elements'].append(idx)

    def get_labels(self):
        labels = [0 for i in range(len(self.get_times()))]
        for cluster in self.get_clusters():
            for idx in cluster['elements']:
                labels[idx] = cluster['id']

        return labels

    def get_cluster(self, idx):
        return list(map(lambda x: x[0], filter(lambda x: x[1] == idx, zip(self.get_solutions().values(),
                                                                          self.get_labels()))))

    def get_cluster_info(self, idx):
        return self.get_clusters()[idx]

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
            file_md5 = test_f.md5(testname)

            if testname not in self.tests:
                test = test_f.Test(name=testname, id=self.get_count_tests(), file_md5=file_md5)
                self.tests[testname] = test
                self.is_changed = True
                new_tests.append(test)
            else:
                test = self.tests[testname]
                if test.md5 != file_md5:
                    new_tests.append(test)
                    self.is_changed = True
                    test.md5 = file_md5
                    for solution_name in self.all_solutions.keys():
                        solution = self.all_solutions[solution_name]
                        solution.times[test.id] = None
                        if test.id in solution.rt:
                            solution.rt.remove(test.id)
                        if test.id in solution.tl:
                            solution.tl.remove(test.id)

        return new_tests

    def update_sources(self, sources):
        new_souces = []
        for source in sources:
            if source['file'] not in self.all_solutions:
                new_souces.append(source)
        return new_souces

    def get_solution(self, source):
        if source['file'] not in self.all_solutions:
            s = solution.Solution(self, filename=source['file'])
            self.all_solutions[source['file']] = s
            self.drop_cache()

        return self.all_solutions[source['file']]

    def get_sources(self):
        result = []
        for e in self.all_solutions.values():
            result.append(e.get_source())
        return result

    def save(self):
        assert self.output is not None
        fetch.is_running.clear()
        file = open(self.output, 'w')
        file.seek(0)
        file.truncate()
        json.dump({
            'name': self.name,
            'is_tl_hidden': self.is_tl_hidden,
            'is_rt_hidden': self.is_rt_hidden,
            'is_wa_hidden': self.is_wa_hidden,
            'cluster_size': self.cluster_size,
            'tests': [t.dump() for t in self.tests.values()],
            'solutions': [s.dump() for s in self.all_solutions.values()],
            'clusters': self.clusters,
        }, file, sort_keys=True, indent=4)
        file.flush()
        file.close()
        self.is_changed = False
        fetch.is_running.set()



