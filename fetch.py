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


def list_files(dir):
    r = []
    for root, dirs, files in os.walk(dir):
        for name in files:
            r.append(os.path.join(root, name))
    return r


def parse_filename(filename):
    data = list(filter(len, re.split("\((.*?)\)", filename)))
    if len(data) != 5:
        return None
    return {'username':data[0], 'date':data[1], 'status': data[2], 'plagiat': data[3], 'ext':data[4]}


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


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
    return list(filter(lambda name: name[-2:] != '.a', list_files(testsfolder)))


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
    #with tempfile.NamedTemporaryFile(mode='r+') as output:
    #output = mytemp
    #output.seek(0)
    #output.truncate()
    #print('calling', command)
    #print('temp file is', output.name)
    proc = subprocess.Popen(command,
                            stderr=subprocess.STDOUT, stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                            universal_newlines=True, errors='ignore')
    #                        stderr=output, stdout=output, stdin=subprocess.PIPE, universal_newlines=True)
    #print("popen")
    output = ''
    errors = ''
    try:
        output, errors = proc.communicate(timeout=timeout, input=input)
        #print("communicated",outp, errors)
    except subprocess.TimeoutExpired as error:
        kill_process(proc.pid)
    #output.seek(0)
    #data = output.read()
    #print(proc.args, proc.returncode)
    data = output
    #print('data', data)
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(output=data, cmd=command, returncode=proc.returncode)

    return data


def compile_source(file, output):
    opts = config['compiler']

    #command = "{} {} -o {} \"{}\"".format(opts['name'], opts['options'],
    #                                      os.path.join(output, file['meta']['username']), file['file'])

    #print('compiling', command)

    params = list(filter(len, opts['options'].split(' ')))
    output_path = os.path.join(output, file['meta']['username'])
    command = [opts['name'], *params, '-o', output_path, file['file']]
    print('compiling', command)
    #proc = subprocess.Popen(
    #    [opts['name'], *params, '-o', output_path, file['file']],
        #"{} {} -o {} \"{}\"".format(
        #    opts['name'], opts['options'],
        #    os.path.join(output, file['meta']['username']), file['file']
        #),
    #    stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
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


def run_test(program, test, programname):
    #print('run_test')
    #proc = subprocess.Popen("time {} < {} > /dev/null".format(program, test), shell=True,
    #                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    #print('started')
    #command = "time {} < {} > /dev/null".format(program, test)
    command = ['time', '-p', program]

    test_data = open(test, 'r').read()


    try:
        output = call_process(command, timeout=config['tests'].getfloat('timeout'), input=test_data)
        return parse_time(output)
        #output = proc.communicate(timeout=config['tests'].getfloat('timeout'))[0]
        #print('communicated')
        #if proc.returncode != 0:
        #    print("Error while running program with name {} on test {}".format(program, test))
        #    print("Reason:\n{}".format(output))
        #    raise subprocess.CalledProcessError(proc.returncode, proc.args, output=output, stderr='')
        #return parse_time(output)

    except subprocess.TimeoutExpired as error:
        print("Timeout expired for source {} on test {}".format(program, test))
        #try:
        #    pass
            #kill_process(program)
            #call_process('pkill \"{}\"'.format(program), timeout=10)
        #except subprocess.TimeoutExpired:
        #    pass
        raise error

    except subprocess.CalledProcessError as error:
        print("Error while running program with name {} on test {}".format(program, test))
        #print("Reason:\n{}".format(error.output))
        raise error


def run_tests(file, tests, outputfolder, gui_checker_test, gui_error, progress_counter):
    print("running tests for", file['meta']['username'])

    results = []
    timeout = []
    runtime = []
    for idx_test, test in enumerate(tests):

        average = []
        gui_checker_test(idx_test, len(tests), progress_counter)
        for i in range(int(config['tests']['count'])):

            try:
                average.append(run_test(os.path.join(outputfolder,file['meta']['username']), test, file['meta']['username']))
            except subprocess.TimeoutExpired:
                if len(timeout) == 0:
                    gui_error("Timeout for {}".format(os.path.basename(file['file'])))
                timeout.append(idx_test)
                if config['tests'].getboolean('force_run_after_timeout'):
                    average = [float(config['tests']['timeout'])*1000 for i in range(int(config['tests']['count']))]
                else:
                    for j in range(idx_test, len(tests)):
                        results.append(float(config['tests']['timeout'])*1000)

                    return results, timeout, runtime
                break
            except subprocess.CalledProcessError:
                if len(runtime) == 0:
                    gui_error("Runtime error for {}".format(os.path.basename(file['file'])))
                runtime.append(idx_test)
                if config['tests'].getboolean('force_run_after_timeout'):
                    average = [float(config['tests']['timeout'])*1000 for i in range(int(config['tests']['count']))]
                else:
                    for j in range(idx_test, len(tests)):
                        results.append(float(config['tests']['timeout'])*1000)

                    return results, timeout, runtime
                break


        results.append(np.mean(average))
        #results.append({key: np.mean([el[key] for el in average]) for key in average[0].keys()})

    return results, timeout, runtime


def generate_project(result, folder, tests):
    return {
        'task_name': os.path.basename(folder),
        'count_tests': len(tests),
        'data': result,
    }


def process_sources(sources, tests, gui_checker, gui_checker_test, gui_error, outputfolder, projectname):
    result = []
    sources_with_errors = []
    progress_counter = len(sources) * len(tests)
    for idx, source in enumerate(sources):
        print("Running {} of {}".format(idx, len(sources)))
        gui_checker(idx, len(sources), source)
        try:
            compile_source(source, outputfolder)
        except subprocess.CalledProcessError:
            gui_error("Cannot compile file {}".format(os.path.basename(source['file'])))
            sources_with_errors.append(source)
            continue

        timings, tl, rt = run_tests(source, tests, outputfolder, gui_checker_test, gui_error, progress_counter)
        print("average time is", np.mean(timings))
        result.append({'name': source, 'tests':{'time': timings, 'tl': tl, 'rt': rt}})

        if idx % 100 == 0:
            print("temp store")
            temp = open('./json.temp', 'w')
            json.dump(generate_project(result, projectname, tests), temp, sort_keys=True, indent=4)
            temp.close()

    print("Errors:\n{}".format(sources_with_errors))
    return result


def check_folder(folder, gui_checker, gui_checker_test, gui_error):
    print("Taking test from folder {}".format(folder))
    sources = get_sources(os.path.join(folder, 'sources'))
    outputfolder = os.path.join(folder, "executables")
    tests = get_tests(os.path.join(folder, 'tests'))

    if not os.path.exists(outputfolder):
        os.makedirs(outputfolder)

    sources = filter_sources(sources)
    result = process_sources(sources, tests, gui_checker, gui_checker_test, gui_error, outputfolder, folder)

    return generate_project(result, folder, tests)


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

