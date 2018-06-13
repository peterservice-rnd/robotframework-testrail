# -*- coding: utf-8 -*-

from robot.api import SuiteVisitor
from TestRailAPIClient import TestRailAPIClient, TESTRAIL_STATUS_ID_PASSED


class TestRailPreRunModifier(SuiteVisitor):
    """Pre-run modifier for starting test cases from a certain test run in [http://www.gurock.com/testrail/ | TestRail].

    == Dependencies ==
    | robot framework | http://robotframework.org |

    == Preconditions ==
    1. [ http://docs.gurock.com/testrail-api2/introduction | Enable TestRail API] \n

    == Example ==
    1. Create test cases in TestRail with case_id: 10,11,12. \n
    2. Add test cases with case_id:10,12 into test run with run_id = 20. \n
    3. Create robot_suite in Robot Framework:
    | *** Test Cases ***
    | Autotest name 1
    |     [Documentation]    Autotest 1 documentation
    |     [Tags]    testrailid=10
    |     Fail    Test fail message
    | Autotest name 2
    |     [Documentation]    Autotest 2 documentation
    |     [Tags]    testrailid=11
    |     Fail    Test fail message
    | Autotest name 3
    |     [Documentation]    Autotest 3 documentation
    |     [Tags]    testrailid=12
    |     Fail    Test fail message
    4. Run Robot Framework with pre-run modifier:
    | pybot.bat --prerunmodifier TestRailPreRunModifier:testrail_server_name:tester_user_name:tester_user_password:20:http:0 robot_suite.robot
    5. Test cases "Autotest name 1" and "Autotest name 3" will be executed. Test case "Autotest name 2" will be skipped. \n
    6. To execute tests from TestRail test run only with a certain status, for example "failed" and "blocked":
    | pybot.bat --prerunmodifier TestRailPreRunModifier:testrail_server_name:tester_user_name:tester_user_password:20:http:0:failed:blocked robot_suite.robot
    7. To execute stable tests from TestRail test run with run analysis depth = 5:
    | pybot.bat --prerunmodifier TestRailPreRunModifier:testrail_server_name:tester_user_name:tester_user_password:20:http:5 robot_suite.robot
    """

    def __init__(self, server, user, password, run_id, protocol, results_depth, *status_names):
        """Pre-run modifier initialization.

        *Args:*\n
            _server_ - name of TestRail server;\n
            _user_ - name of TestRail user;\n
            _password_ - password of TestRail user;\n
            _run_id_ - ID of the test run;\n
            _protocol_ - connecting protocol to TestRail server: http or https;\n
            _results_depth_ - analysis depth of run results;\n
            _status_names_ - name of test statuses in TestRail.
        """
        self.run_id = run_id
        self.status_names = status_names
        self.tr_client = TestRailAPIClient(server, user, password, run_id, protocol)
        self.tr_tags_list = None
        self.tr_stable_tags_list = None
        self.results_depth = int(results_depth)

    def _get_tr_tags_list(self):
        """Get list of 'testrailid' tags.

        If required test statuses from the test run are passed to modifier,
        a request is made to the TestRail to obtain information about all the statuses.
        Theirs identifiers will be retrieved from list of all the statuses.
        This identifiers will be used to receive test tags in the required status.

        If statuses aren't passed to modifier,
        the tags of all tests in the test run will be obtained regardless of their status.
        """
        status_ids = None
        if self.status_names:
            status_ids = [self.tr_client.get_status_id_by_status_label(name) for name in self.status_names]
        tests_info = self.tr_client.get_tests(run_id=self.run_id, status_ids=status_ids)
        self.tr_tags_list = ['testrailid={}'.format(test["case_id"]) for test in tests_info]

    def _get_tr_stable_tags_list(self):
        """Get list of 'testrailid' tags of the stable test cases.

        If analysis depth of the run results is passed to modifier and its value greater than zero,
        a request is made to the TestRail to receive information about test cases whose last result is 'passed'.
        Based on the information received, the results of the latest runs for these test cases are analyzed,
        on the basis of which the tags of stable test cases will be received.
        """
        passed_tests_info = self.tr_client.get_tests(run_id=self.run_id, status_ids=[TESTRAIL_STATUS_ID_PASSED])
        case_ids = [test["case_id"] for test in passed_tests_info]
        stable_case_ids_list = list()
        for case_id in case_ids:
            case_results = self.tr_client.get_results_for_case(self.run_id, case_id, self.results_depth)
            passed_list = [result for result in case_results if result['status_id'] == TESTRAIL_STATUS_ID_PASSED]
            if len(passed_list) == int(self.results_depth):
                stable_case_ids_list.append(case_id)
        self.tr_stable_tags_list = ['testrailid={}'.format(case_id) for case_id in stable_case_ids_list]

    def start_suite(self, suite):
        """Form list of tests for the Robot Framework test suite that are included in the TestRail test run.

        If analysis depth of the run results is greater than zero, when first suite is launched
        a list of 'testrailid' tags of stable test cases is obtained.
        After that the list of tags is written to the class attribute and for subsequent suites the obtaining is not happening.

        If analysis depth of the run results is zero, when the first suite is launched
        a list of 'testrailid' tags of all test cases in the given status is obtained.
        After that the list of tags is written to the class attribute and for subsequent suites the obtaining is not happening.

        *Args:*\n
            _suite_ - Robot Framework test suite name.
        """
        if self.results_depth > 0:
            if self.tr_stable_tags_list is None:
                self._get_tr_stable_tags_list()
            suite.tests = [t for t in suite.tests if (set(t.tags) & set(self.tr_stable_tags_list))]
        else:
            if self.tr_tags_list is None:
                self._get_tr_tags_list()
            suite.tests = [t for t in suite.tests if (set(t.tags) & set(self.tr_tags_list))]

    def end_suite(self, suite):
        """Removing test suites that are empty after excluding tests that are not part of the TestRail test run.

        *Args:*\n
            _suite_ - Robot Framework test suite name.
        """
        suite.suites = [s for s in suite.suites if s.test_count > 0]
