import json
import os
import pathlib
import platform
import shlex
import shutil
import subprocess
import sys
from enum import IntEnum

import pytest

sys.path.insert(1, os.getcwd())
from case_CASENUMBER import *


def pytest_parametrize_to_dict(args, parametrize_str):
    parser = CaseArgumentParser()
    parser.add_argument('--test_should_fail', default=False, type=lambda x: (str(x).lower() in ['true', 'yes']))
    # parametrize_str_tokens = parametrize_str.split()
    parametrize_str_tokens = shlex.split(parametrize_str)
    parametrize_arg_names = []
    for arg_name, arg_value in zip(parametrize_str_tokens[::2], parametrize_str_tokens[1::2]):
        parametrize_arg_names.append(arg_name[2:])
    parametrized_args = vars(parser.parse_args(parametrize_str_tokens))
    for parametrize_arg_name in parametrize_arg_names:
        args[parametrize_arg_name] = parametrized_args[parametrize_arg_name]
    return


@pytest.fixture()
def command_line_args(request):
    args = {}

    parser = CaseArgumentParser()
    option_string_actions = parser._option_string_actions

    keys = option_string_actions.keys()
    for key in keys:
        arg_key = key[2:]
        args[arg_key] = request.config.getoption(key)

    return args


case_reports = []
case_logs = {}
the_platform = platform.platform()
python_ver = 'python' if "Windows" in platform.platform() else "python3"
if "Windows-10" in the_platform:
    current_platform = "Platform W10x64"
if "Windows-11" in the_platform:
    current_platform = "Platform W11x64"
if "Linux-5" and "tegra" in the_platform:
    current_platform = "Platform X5"
if "Ubuntu" in platform.version() and "20." in platform.version():
    current_platform = "Platform U20"
if "Ubuntu" in platform.version() and "22." in platform.version():
    current_platform = "Platform U22"


def copy_log(script, parameters, pid):
    variable_path = pathlib.Path(os.environ.get("KAYA_VISION_POINT_LOGS"))
    log_folder = pathlib.Path.cwd().joinpath(script.replace('.py', '.log'))
    parameters_name_folder = parameters
    invalid_chars = r"\/:*?'<>;:|"
    for char in invalid_chars:
        parameters_name_folder = parameters_name_folder.replace(char, '')

    if len(parameters_name_folder) > 255:
        parameters_name_folder = parameters_name_folder[0:255]
    if not log_folder.exists():
        log_folder.mkdir()
    parameters_logs_path = log_folder.joinpath(parameters_name_folder)
    if not parameters_logs_path.exists():
        parameters_logs_path.mkdir()
    for next_log in variable_path.iterdir():
        if "python" in next_log.name and str(pid) in next_log.name:
            shutil.copy(next_log, parameters_logs_path.joinpath(next_log.name))
            return parameters_logs_path.joinpath(next_log.name)


# end of the function 'copy_log(script)'
class CaseReturnCode(IntEnum):
    SUCCESS = 0
    COULD_NOT_RUN = 1
    NO_HW_FOUND = 2
    ASSERT_ERROR = 3
    WRONG_PARAM_VALUE = 4
    FAILED_WITH_EXCEPTION = 5


def get_subprocess_result(full_output):
    test_failed = False
    return_code = None
    if 'Case return code: 0' in full_output:
        return_code = CaseReturnCode.SUCCESS
    elif 'AssertionError' in full_output:
        return_code = CaseReturnCode.ASSERT_ERROR
        test_failed = True
    elif "Case return code: 1" in full_output:
        return_code = CaseReturnCode.COULD_NOT_RUN
    elif 'Case return code: 2' in full_output:
        return_code = CaseReturnCode.NO_HW_FOUND
    elif 'Case return code: 5' in full_output:
        return_code = CaseReturnCode.FAILED_WITH_EXCEPTION

    return (return_code, test_failed)
def get_json_result_file_and_data(automation_scripts_folder_name):
    json_param_results_file = pathlib.Path(f'{automation_scripts_folder_name}/case_CASENUMBER').joinpath(
        "case_CASENUMBER_param_results.json")
    with json_param_results_file.open('r') as jrf:
        json_param_results_data = json.load(jrf)
        return json_param_results_file, json_param_results_data
def save_result_to_json(parametrize, result, output, automation_scripts_folder_name):
    json_param_results_file, json_param_results_data = get_json_result_file_and_data(automation_scripts_folder_name)
    json_param_results_data[parametrize]["status"] = result
    json_param_results_data[parametrize]["last output"] = output
    with json_param_results_file.open('w') as jrf: json.dump(json_param_results_data, jrf, indent=4)

def test_case(command_line_args, pytest_parametrize):
    args = command_line_args
    automation_scripts_folder_name = 'QA_Automation_Scripts'
    args["unattended"] = True  # force unattended mode when running under PyTest
    # othwerwise, we get "OSError: pytest: reading from stdin while output is captured!  Consider using `-s`"

    pytest_parametrize_to_dict(args, pytest_parametrize)  # pass 'args' by ref to let the func modify it

    test_should_fail = args['test_should_fail']
    args.pop('test_should_fail')
    command = [python_ver, f'./{automation_scripts_folder_name}/case_CASENUMBER/case_CASENUMBER.py', '--unattended', '--deviceIndex',
               f'{args["deviceIndex"]}']
    if len(pytest_parametrize.split(' ')) > 2:
        # for parameter in pytest_parametrize.split(' ')[2:]:
        for parameter in shlex.split(pytest_parametrize)[2:]:
            command.append(parameter)
    json_param_results_file, json_param_results_data = get_json_result_file_and_data(automation_scripts_folder_name)
    # if json_param_results_data[pytest_parametrize]["status"] == "Passed":
    #     print(json_param_results_data[pytest_parametrize]["last output"])
    #     return CaseReturnCode.SUCCESS
    test_failed = False
    return_code = 0
    exception = None
    full_output = None
    pid = 0
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        # return_code = CaseRun(args)
        pid = process.pid
        stdout, stderr = process.communicate()
        full_output = stdout.strip() if len(stderr.strip()) == 0 else stdout.strip()+ '\n' + stderr.strip()
        # full_output = stdout.strip()+ '\n' + stderr.decode("utf-8")
        return_code = CaseReturnCode(process.returncode) # if return code not in CaseReturnCode: return_code = CaseReturnCode.FAILED_WITH_EXCEPTION
    except Exception as ex:
        (return_code, test_failed) = get_subprocess_result(full_output)

    # print(f'Case return code: {return_code}')
    case_log_file = copy_log(pathlib.Path(__file__).name, pytest_parametrize, pid)
    error_count = 0
    with case_log_file.open('r', errors='ignore') as lf:
        log_file_data = lf.readlines()
    for next_line in log_file_data:
        if 'error' in next_line.lower():
            error_count += 1
    full_output = f'ERROR COUNT FROM LOG FILE = {error_count}\n' + full_output
    if return_code == CaseReturnCode.NO_HW_FOUND:
        print(full_output)
        save_result_to_json(pytest_parametrize, "Didn't run", full_output, automation_scripts_folder_name)
        pytest.skip("No hardware found")  # if HW not found, test case skipped anywhere
    elif return_code == CaseReturnCode.COULD_NOT_RUN and "AssertionError" not in full_output:
        print(full_output)
        save_result_to_json(pytest_parametrize, "CouldNotRun", full_output, automation_scripts_folder_name)
        # pytest.skip("Could not run")
        pytest.xfail("CouldNotRun")
    print(full_output)
    if return_code != CaseReturnCode.SUCCESS:
        test_failed = True
    if test_should_fail != test_failed:
        save_result_to_json(pytest_parametrize, "Failed", full_output, automation_scripts_folder_name)
    assert test_should_fail == \
           test_failed, \
        f'Test expected to fail: {"Yes" if test_should_fail else "No"}, actually failed: {"Yes" if test_failed else "No"}'

    if test_should_fail == True and test_failed == True:
        print(f'Test case expectedly failed')
        save_result_to_json(pytest_parametrize, "Passed", full_output, automation_scripts_folder_name)
    else:
        assert return_code == CaseReturnCode.SUCCESS, save_result_to_json(pytest_parametrize, "Failed", full_output, automation_scripts_folder_name)
        save_result_to_json(pytest_parametrize, "Passed", full_output, automation_scripts_folder_name)
