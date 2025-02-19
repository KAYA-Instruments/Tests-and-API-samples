from case_CASENUMBER import *
from py.xml import html # https://stackoverflow.com/questions/70651334/is-there-way-to-show-test-author-name-in-pytest-html-reports-for-each-tests
import pytest
import re
import platform
import os

square_open = re.escape("[")
square_close = re.escape("]")

def pytest_addoption(parser):
    arg_parser = CaseArgumentParser()
    option_string_actions = arg_parser._option_string_actions
    option_string_actions.pop('-h')
    option_string_actions.pop('--help')

    keys = option_string_actions.keys()
    for key in keys:
        sa = option_string_actions[key]
        parser.addoption(key, type=sa.type, action='store', default=sa.default, help=sa.help)

    parser.addoption("--pytest_parametrize", action='append', default=[], help="pytest_parametrize")

    pass

def pytest_generate_tests(metafunc):
    metafunc.parametrize("pytest_parametrize", metafunc.config.getoption("pytest_parametrize"))
    pass


def pytest_html_report_title(report):
    report.title = "Case CASENUMBER report"


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_header(cells):
    cells[1] = html.th("Test parameters")

    # cells.insert(2, html.th("Description"))

    # remove last column, "Links"
    del cells[-1]

    pass

@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_row(report, cells):
    test_params = re.search('%s(.*)%s' % (square_open, square_close), report.head_line).group(1)
    cells[1] = html.td(test_params)

    # cells.insert(2, html.td(report.description))

    # remove last column, "Links"
    del cells[-1]

    pass

'''
def pytest_html_results_table_html(report, data):
    if report.passed:
        del data[:]
'''

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    report.description = str(item.function.__doc__) #"THE DESCRIPTION"

    #pytest_html = item.config.pluginmanager.getplugin('html')
    #extra = getattr(report, 'extra', [])
    #if report.when == 'call':
        #extra.append(pytest_html.extras.html('<p>some html</p>'))
        #report.extra = extra
    pass

def pytest_configure(config):
    host_name = platform.uname()[1]
    (_, software_info) = KY_GetSoftwareVersion()
    vp_sersion = f"{software_info.Major}.{software_info.Minor}.{software_info.SubMinor}"

    (_, infosize_test) = KY_DeviceScan()
    installed_frame_grabbers = []
    for x in range(0, infosize_test):
        (status, device_info) = KY_DeviceInfo(x)
        installed_frame_grabbers.append(device_info.szDeviceDisplayName)

    config._metadata = {
        'Name of Machine': host_name,
        'VP version': vp_sersion,
        'Installed frame grabbers': ', '.join(installed_frame_grabbers)
    }