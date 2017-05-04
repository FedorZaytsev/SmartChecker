import os
import re
import signal
import subprocess
import numpy as np
import threading
import json
import queue
from settings import *
import tempfile
import hashlib
import project
import sarge
import datetime
import time
sarge.default_capture_timeout = config['tests'].getfloat('timeout')


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


def kill_process_new(pid):
    assert False
    print('killing process', pid)
    try:
        proc = subprocess.Popen(['pkill', '-TERM', '-P', str(pid)])
        output, err = proc.communicate(timeout=10)
        if proc.returncode != 0:
            print("Fatal! Cannot kill pid {}".format(pid))
            return subprocess.CalledProcessError(proc.returncode, ' '.join(proc.args))
    except subprocess.TimeoutExpired as err:
        print("FATAL! KILL PROCESS TIMEOUT")

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

def ttt(cmd, input=None, timeout=1, output=False, error=False):

    child_pid = os.fork()
    if child_pid == 0:

        if input:
            stdin_fd = os.open(input, os.O_RDONLY)
            os.close(0)
            os.dup2(stdin_fd, 0)
            os.close(stdin_fd)
        if output:
            stdout_fd = os.open('./stdout', os.O_WRONLY | os.O_CREAT)
            os.close(1)
            os.dup2(stdout_fd, 1)
            os.close(stdout_fd)
        if error:
            stderr_fd = os.open('./stderr', os.O_WRONLY | os.O_CREAT)
            os.close(1)
            os.dup2(stderr_fd, 2)
            os.close(stderr_fd)
        os.execvp(cmd[0], cmd)
        exit(0)
    else:
        return_code = None

        start_time = datetime.datetime.now()
        while (datetime.datetime.now() - start_time).total_seconds() < timeout:
            wpid, rc = os.waitpid(child_pid, os.WNOHANG)
            if wpid == child_pid:
                return_code = rc
                break
            time.sleep(0.1)

        if return_code is None:
            print("return code is None")
            os.killpg(child_pid, signal.SIGINT)
            raise subprocess.TimeoutExpired(cmd, timeout)
        elif return_code != 0:
            raise subprocess.CalledProcessError(return_code, cmd)
        else:
            if output and error:
                return open('./stdout', errors='ignore').read(), open('./stderr', errors='ignore').read()

            if output:
                return open('./stdout', errors='ignore').read()

            if error:
                return open('./stderr', errors='ignore').read()


def call_process_new(command, input=None, timeout=None, output=False, error=False, programname=None):
    print("call_process {}, input {}, {}, {}".format(command, input, output, error))

    output = ttt(command, input, timeout=timeout, output=output, error=error)

    print("got {}".format(output))

    return output

    """cmd = command#' '.join(["'{}'".format(cmd) for cmd in command])
    print("call_process {}".format(cmd))

    pid = os.spawnvp(os.P_NOWAIT, cmd[0], cmd[1:])

    start_time = datetime.datetime.now()
    while True:
        pid, status = os.waitpid(pid, os.WNOHANG)
        if (datetime.datetime.now() - start_time).total_seconds() > timeout:
            kill_process(pid)
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

        if pid == 0:
            time.sleep(0.1)
        else:
"""


    """reference = [None]

    def timeout_called(programname):
        sarge.run('pkill {}'.format(programname))

    t = threading.Timer(timeout+0.5, lambda: timeout_called(programname))
    t.start()
    reference[0] = sarge.Command(cmd, stdout=sarge.Capture(), stderr=sarge.Capture())
    reference[0].run(input=input)
    t.cancel()

    proc = reference[0]

    proc.stdout.close()
    output_data = proc.stdout.read().decode('UTF-8', errors='ignore')
    error_data = proc.stderr.read().decode('UTF-8', errors='ignore')

    if proc.returncode != 0:
        error_data = proc.stderr.read().decode('UTF-8', errors='ignore')
        raise subprocess.CalledProcessError(output=error_data, cmd=command, returncode=proc.returncode)

    if output and error:
        return output_data, error_data

    if output:
        return output_data

    if error:
        return error_data"""

    """mytemp.seek(0)
    mytemp.truncate()
    print('call_process', command)
    proc = subprocess.Popen(command,
                            stderr=mytemp, stdout=mytemp, stdin=input,
                            universal_newlines=True, errors='ignore')
    #                        stderr=output, stdout=output, stdin=subprocess.PIPE, universal_newlines=True)

    output = ''
    errors = ''
    try:
        print('communicate')
        output, errors = proc.communicate(timeout=timeout)
        print('done')
    except subprocess.TimeoutExpired as error:
        kill_process(proc.pid)
        raise error

    mytemp.seek(0)
    data = mytemp.read()

    if proc.returncode != 0:
        raise subprocess.CalledProcessError(output=data, cmd=command, returncode=proc.returncode)

    return data"""

import gc
def call_process_old_old(command, input=None, timeout=None):
    print("call_process ", command)
    proc = subprocess.Popen(command,
                            stderr=subprocess.STDOUT, stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                            universal_newlines=True, errors='ignore')
    #                        stderr=output, stdout=output, stdin=subprocess.PIPE, universal_newlines=True)
    #print("popen")
    print("gc", gc.get_count())
    output = ''
    errors = ''
    try:
        output, errors = proc.communicate(timeout=timeout, input=input)
        #print("communicated")
    except subprocess.TimeoutExpired as error:
        kill_process(proc.pid)

    data = output
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(output=data, cmd=command, returncode=proc.returncode)

    return data


def call_process(command, timeout, input='/dev/null', output=False, error=False):
    assert type(command) is str

    curr = os.getcwd()
    stdout = os.path.join(curr, 'stdout')
    stderr = os.path.join(curr, 'stderr')
    command = '{} {} {} < {} 1>"{}" 2>"{}"'.format(config['tests']['timeout_prog'], timeout, command, input, stdout,
                                                  stderr)

    print('call_process', command)

    rc = os.system(command)

    print('return code', rc)
    return_code = (rc >> 8) & 0xff

    if return_code == 124:  #gtimeout TIMEOUT status
        raise subprocess.TimeoutExpired(command, timeout)


    def get_data(filename):
        with open(filename, 'r', errors='ignore') as f:
            return f.read()

    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command, output=get_data(stdout),stderr=get_data(stderr))

    if output and error:
        return get_data(stdout) and get_data(stderr)
    if output:
        return get_data(stdout)
    if error:
        return get_data(stderr)


def compile_source(file, output):
    opts = config['compiler']

    output_path = os.path.join(output, file['meta']['username'])
    cmd = '{} {} -o "{}" "{}"'.format(opts['name'], opts['options'], output_path, file['file'])
    params = list(filter(len, opts['options'].split(' ')))
    command = [opts['name'], *params, '-o', output_path, file['file']]
    print('compiling', command)

    try:
        output = call_process(cmd, timeout=30, output=True)
        print('compile got', output)
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
        #m = int(time[:time.find('m')])
        #s = float(time[time.find('m')+1:-1])

        #return m*60*1000+s*1000
        return float(time)*1000

    #text = text.decode("utf-8", "ignore")

    result = {}
    #print('text', text)
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

    cmd = 'time -p "{}"'.format(filepath)
    command = ['time', '-p', filepath]
    #test_data = open(test['name'], 'r').read()

    error = call_process(cmd, timeout=config['tests'].getfloat('timeout'), input=test['name'], error=True)

    print('run_test', error)

    return parse_time(error)


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
                      .format(solution.filepath, test['name'], error.returncode))
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

        if idx % 100 == 0:
            gui_error("Storing data....")
            proj.save()
            gui_error("Done")


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

