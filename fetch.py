import re
import threading
import subprocess
import numpy as np
from settings import *
import tempfile


is_running = threading.Event()
stop_flag = threading.Event()


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
    files = list(filter(lambda name: name[-2:] != '.a', list_files(testsfolder)))

    lst = []
    for file in files:
        try:
            int(os.path.basename(file))
        except ValueError:
            pass
        else:
            lst.append(file)

    return sorted(lst, key=lambda x: int(os.path.basename(x)))


def call_process(cmd, timeout=10, input='/dev/null', output=False, error=False):
    assert cmd != ''

    curr = os.getcwd()
    stdout = os.path.join(curr, 'stdout')
    stderr = os.path.join(curr, 'stderr')

    command = '{} {} {} < {} 1>"{}" 2>"{}"'.format(config['tests']['timeout_prog'], timeout, cmd, input, stdout,
                                                   stderr)

    #print('call_process', command)

    rc = os.system(command)

    return_code = (rc >> 8) & 0xff

    if return_code == 124:  #gtimeout TIMEOUT status
        raise subprocess.TimeoutExpired(command, timeout)

    def get_data(filename):
        with open(filename, 'r', errors='ignore') as f:
            return f.read()

    #because fuck you, thats why
    #if return_code != 0:
    #    raise subprocess.CalledProcessError(return_code, command, output=get_data(stdout),stderr=get_data(stderr))

    if output and error:
        return get_data(stdout) and get_data(stderr)
    if output:
        return get_data(stdout)
    if error:
        return get_data(stderr)


def compile_source(file, output_path):
    opts = config['compiler']

    cmd = '{} {} -o "{}" "{}" '.format(opts['name'], opts['options'], output_path, file['file'])

    #params = list(filter(len, opts['options'].split(' ')))
    #command = [opts['name'], *params, '-o', output_path, file['file']]
    #print('compiling', command)

    output = ''
    try:
        output = call_process(cmd=cmd, timeout=30, output=True)
        #rc = os.system(cmd)
        #if rc != 0:
        #    raise subprocess.CalledProcessError(rc, cmd)
    except subprocess.CalledProcessError as error:
        print("Cannot compile program with name {}".format(file['file']))
        print("Reason:\n{}".format(output))
        raise error
    except subprocess.TimeoutExpired as error:
        print("Timeout expired while compiled program with name", file['name'])
        raise error



def parse_time(text):
    def time2ms(time):
        m = int(time[:time.find('m')])
        s = float(time[time.find('m')+1:-1])

        return m*60*1000+s*1000
        #return float(time)*1000

    #text = text.decode("utf-8", "ignore")

    result = {}
    #print('parse_time', text)
    for el in filter(len, text.split('\n')):
        if el.find("Segmentation fault") != -1 or el.find("Abort") != -1:
            raise subprocess.CalledProcessError(output=el, cmd='time', returncode=1)
        els = list(filter(len, el.split('\t')))

        #for name in ['real', 'user', 'sys']:
        #    if name in els:
        #        result[name] = time2ms(els[els.index(name)-1])

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

    cmd = '/bin/bash -c \'time "{}"\''.format(filepath)
    #command = ['time', filepath]

    #def format_cmd(stdio, stdout, stderr):
    #    return '/bin/bash -c \'time "{}" <"{}"\' 1>"{}" 2>"{}"'.format(filepath, stdio, stdout, stderr)

    error = call_process(cmd, timeout=config['tests'].getfloat('timeout'), input=test.name, error=True)

    #print('run_test', error)

    return parse_time(error)


def run_tests(solution, tests, outputfolder, gui_checker_test, gui_error):
    print("running tests for", solution.meta['username'])

    timeout = False
    runtime = False
    for idx_test, test in enumerate(tests):
        average = []

        is_running.wait()

        gui_checker_test(idx_test, len(tests))
        for i in range(int(config['tests']['count'])):

            try:
                average.append(run_test(outputfolder, solution.meta['username'], test))
            except subprocess.TimeoutExpired:
                print("Timeout expired for source {} on test {}".format(solution.filepath, test))
                if not timeout:
                    gui_error("Timeout for {}".format(solution.filepath))
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
                      .format(solution.filepath, test, error.returncode))
                if not runtime:
                    gui_error("Runtime error for {}".format(solution.filepath))
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


def process_sources(sources, tests, gui_checker, gui_checker_test, gui_error, proj):
    outputfolder = config['tests']['temporary_folder']

    for idx, source in enumerate(sources):
        print("Running {} of {}".format(idx, len(sources)))
        gui_checker(idx, len(sources), source)

        solution = proj.get_solution(source)
        output_path = os.path.join(outputfolder, source['meta']['username'])
        try:
            compile_source(source, output_path)
        except subprocess.CalledProcessError:
            gui_error("Cannot compile file {}".format(os.path.basename(source['file'])))
            continue

        run_tests(solution, tests, outputfolder, gui_checker_test, gui_error)

        if stop_flag.is_set():
            stop_flag.clear()
            return

        try:
            os.remove(output_path)
        except FileNotFoundError:
            pass

        if idx != 0 and idx % 100 == 0:
            gui_error("Storing data....")
            proj.save()
            gui_error("Done")


def check_folder(gui_checker, gui_checker_test, gui_error, proj):
    print("Taking sources from {}, tests from {}".format(proj.sources_path, proj.tests_path))
    gui_error("Taking sources from {}, tests from {}".format(proj.sources_path, proj.tests_path))

    sources = get_sources(proj.sources_path)
    sources = filter_sources(sources)
    sources = proj.update_sources(sources)

    tests = get_tests(proj.tests_path)
    tests = proj.update_tests(tests)

    progress_counter = len(proj.get_sources()) * len(tests) + len(sources) * len(proj.tests.keys())
    gui_checker_test_l = lambda idx, count: gui_checker_test(idx, count, progress_counter)

    is_running.set()
    if len(tests) > 0:
        process_sources(proj.get_sources(), tests, gui_checker, gui_checker_test_l, gui_error, proj)

    if len(sources) > 0:
        process_sources(sources, proj.tests.values(), gui_checker, gui_checker_test_l, gui_error, proj)
