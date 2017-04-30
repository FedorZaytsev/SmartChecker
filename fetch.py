import os
import re
import subprocess
import numpy as np
import threading
import json
import queue
from settings import *
import tempfile
import hashlib
import project


def list_files(dir):
    r = []
    for root, dirs, files in os.walk(dir):
        for name in files:
            r.append(os.path.join(dir, name))

    return r


def parse_filename(filename):
    data = list(filter(len, re.split("\((.*?)\)", filename)))
    if len(data) != 5:
        return None
    return {'username':data[0], 'date':data[1], 'status': data[2], 'plagiat': data[3], 'ext':data[4]}


def get_sources(foldername):
    files = []

    for filepath in list_files(foldername):
        path = os.path.split(filepath)[0]
        filename = os.path.split(filepath)[1]
        metadata = parse_filename(filename)
        if metadata is None:
            continue
        files.append({'file':filepath, 'filename': filename, 'meta':metadata})

    return files


def filter_sources(sources):
    return list(filter(lambda el: el['meta']['status'] == 'PASSED_TESTS' or
                                  el['meta']['status'] == 'FAILED_TESTS', sources))


def get_tests(testsfolder):
    lst = list(filter(lambda name: name[-2:] != '.a', list_files(testsfolder)))

    return sorted(lst, key=lambda x: int(os.path.basename(x)))


def kill_process(pid):
    print('killing process', pid)
    try:
        proc = subprocess.Popen(['pkill', '-TERM', '-P', str(pid)])
        output, err = proc.communicate(timeout=10)
        if proc.returncode != 0:
            print("Fatal! Cannot kill pid {}".format(pid))
            return subprocess.CalledProcessError(proc.returncode, ' '.join(proc.args))
    except subprocess.TimeoutExpired as err:
        print("FATAL! KILL PROCESS TIMEOUT")


#mytemp = open('./temp.temp', 'r+', errors='ignore')

def call_process(command, input=None, timeout=None):
    proc = subprocess.Popen(command,
                            stderr=subprocess.STDOUT, stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                            universal_newlines=True, errors='ignore')
    #                        stderr=output, stdout=output, stdin=subprocess.PIPE, universal_newlines=True)

    output = ''
    errors = ''
    try:
        output, errors = proc.communicate(timeout=timeout, input=input)
    except subprocess.TimeoutExpired as error:
        kill_process(proc.pid)
        raise error

    data = output
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(output=data, cmd=command, returncode=proc.returncode)

    return data


def compile_source(file, output):
    opts = config['compiler']

    params = list(filter(len, opts['options'].split(' ')))
    output_path = os.path.join(output, file['meta']['username'])
    command = [opts['name'], *params, '-o', output_path, file['file']]
    print('compiling', command)

    try:
        output = call_process(command, timeout=30)
    except subprocess.CalledProcessError as error:
        print("Cannot compile program with name {}".format(file['file']))
        print("Reason:\n{}".format(output))
        raise error
    except subprocess.TimeoutExpired as error:
        print("Timeout expired while compiled program with name", file['name'])
        raise error



def parse_time(text):
    def time2ms(time):
        #m = int(time[:time.find('m')])
        #s = float(time[time.find('m')+1:-1])

        #return m*60*1000+s*1000
        return float(time)*1000

    #text = text.decode("utf-8", "ignore")

    result = {}
    for el in filter(len, text.split('\n')):
        if el.find("Segmentation fault") != -1 or el.find("Abort") != -1:
            raise subprocess.CalledProcessError(output=el, cmd='time', returncode=1)
        els = list(filter(len, el.split(' ')))
        if len(els) == 2:
            try:
                result[els[0]] = time2ms(els[1])
            except ValueError as e:
                print('Error!', e)
                result[els[0]] = 0
        #else:
        #    print("error in parse_time", text)

    return result['user']


def run_test(path, program_name, test):
    filepath = os.path.join(path, program_name)

    command = ['time', '-p', filepath]
    test_data = open(test['name'], 'r').read()

    output = call_process(command, timeout=config['tests'].getfloat('timeout'), input=test_data)
    return parse_time(output)


def run_tests(solution, tests, outputfolder, gui_checker_test, gui_error):
    print("running tests for", solution.meta['username'])

    timeout = False
    runtime = False
    for idx_test, test in enumerate(tests):
        average = []
        gui_checker_test(idx_test, len(tests))
        for i in range(int(config['tests']['count'])):

            try:
                average.append(run_test(outputfolder, solution.meta['username'], test))
            except subprocess.TimeoutExpired:
                print("Timeout expired for source {} on test {}".format(solution.filepath, test))
                if not timeout:
                    gui_error("Timeout for {}".format(solution.meta['username']))
                timeout = True

                if config['tests'].getboolean('force_run_after_timeout'):
                    solution.set_test(test, timeout=True)
                else:
                    for j in range(idx_test, len(tests)):
                        solution.set_test(tests[j], timeout=True)
                    return

                break
            except subprocess.CalledProcessError as error:
                print("Error while running program with name {} on test {}. Code {}"
                      .format(solution.filepath, test['name'], error.returncode))
                if not runtime:
                    gui_error("Runtime error for {}".format(solution.meta['username']))
                runtime = True

                if config['tests'].getboolean('force_run_after_timeout'):
                    solution.set_test(test, runtime=True)
                else:
                    for j in range(idx_test, len(tests)):
                        solution.set_test(tests[j], runtime=True)
                    return
                break

        if len(average) != 0:
            solution.set_test(test, time=np.mean(average))


def process_sources(sources, tests, gui_checker, gui_checker_test, gui_error, folder, proj):
    outputfolder = os.path.join(folder, "executables")
    if not os.path.exists(outputfolder):
        os.makedirs(outputfolder)

    for idx, source in enumerate(sources):
        print("Running {} of {}".format(idx, len(sources)))
        gui_checker(idx, len(sources), source)

        solution = proj.get_solution(source)
        try:
            compile_source(source, outputfolder)
        except subprocess.CalledProcessError:
            gui_error("Cannot compile file {}".format(os.path.basename(source['file'])))
            continue

        run_tests(solution, tests, outputfolder, gui_checker_test, gui_error)


def check_folder(folder, gui_checker, gui_checker_test, gui_error, proj):
    print("Taking test from folder {}".format(folder))
    sources = get_sources(os.path.join(folder, 'sources'))
    tests = get_tests(os.path.join(folder, 'tests'))
    tests = proj.update_tests(tests)

    sources = filter_sources(sources)
    progress_counter = len(sources) * len(tests)
    gui_checker_test_l = lambda idx, count: gui_checker_test(idx, count, progress_counter)
    process_sources(sources, tests, gui_checker, gui_checker_test_l, gui_error, folder, proj)



def get_new_sources(project, sources):
    new = []

    old = list(map(lambda x: x['name']['filename'], project.data))

    for source in sources:
        splitted = os.path.split(source)
        if len(splitted) > 1:
            filename = splitted[1]
            if filename not in old:
                new.append(source)

    return new


def is_file_modified(project, testname):
    def find_test(mytest):
        for idx, test in enumerate(project.tests):
            if test['name'] == mytest:
                return test, idx
        return None

    test, idx = find_test(testname)
    if test is None:
        return None, None

    return test['hash'] == md5(testname), idx


def upgrade(folder, gui_checker, gui_checker_test, gui_error, project):
    print("upgrading tests from folder {}".format(folder))
    sources = get_sources(os.path.join(folder, 'sources'))
    outputfolder = os.path.join(folder, "executables")
    tests = get_tests(os.path.join(folder, 'tests'))

    if not os.path.exists(outputfolder):
        os.makedirs(outputfolder)

    new_sources = get_new_sources(project, sources)

    sources = filter_sources(new_sources)
    result = process_sources(sources, tests, gui_checker, gui_checker_test, gui_error, outputfolder, folder)

    return generate_project(result, folder, tests)

