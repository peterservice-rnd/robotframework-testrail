# -*- coding: utf-8 -*-

from typing import List, Optional

from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError, Future
from requests.exceptions import RequestException
from robot.api import SuiteVisitor, TestSuite
from robot.output import LOGGER
from TestRailAPIClient import TestRailAPIClient, TESTRAIL_STATUS_ID_PASSED

CONNECTION_TIMEOUT = 60  # Value in seconds of timeout connection with testrail for one request


class TestRailPreRunModifier(SuiteVisitor):
    """Pre-run modifier for starting test cases from a certain test run in [http://www.gurock.com/testrail/ | TestRail].

    == Dependencies ==
    | robot framework | http://robotframework.org |
    | TestRailAPIClient |

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
    | robot --prerunmodifier TestRailPreRunModifier:testrail_server_name:tester_user_name:tester_user_password:20:http:0 robot_suite.robot
    5. Test cases "Autotest name 1" and "Autotest name 3" will be executed. Test case "Autotest name 2" will be skipped.
    6. To execute tests from TestRail test run only with a certain status, for example "failed" and "blocked":
    | robot --prerunmodifier TestRailPreRunModifier:testrail_server_name:tester_user_name:tester_user_password:20:http:0:failed:blocked robot_suite.robot
    6. To execute stable tests from TestRail test run with run analysis depth = 5:
    | robot --prerunmodifier TestRailPreRunModifier:testrail_server_name:tester_user_name:tester_user_password:20:http:5 robot_suite.robot
    """

    def __init__(self, server: str, user: str, password: str, run_id: str, protocol: str,  # noqa: E951
                 results_depth: str, *status_names: str) -> None:
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
        self.results_depth = int(results_depth) if str(results_depth).isdigit() else 0
        self._tr_tags_list: Optional[List[str]] = None
        self._tr_stable_tags_list: Optional[List[str]] = None
        LOGGER.register_syslog()

    @property
    def tr_stable_tags_list(self) -> List[str]:
        """Gets list of 'testrailid' tags of the stable test cases.

        Returns:
            List of tags.
        """
        if self._tr_stable_tags_list is None:
            self._tr_stable_tags_list = self._get_tr_stable_tags_list()

        return self._tr_stable_tags_list

    @property
    def tr_tags_list(self) -> List[str]:
        """Gets 'testrailid' tags.

        Returns:
            List of tags.
        """
        if self._tr_tags_list is None:
            self._tr_tags_list = self._get_tr_tags_list()

        return self._tr_tags_list

    def _log_to_parent_suite(self, suite: TestSuite, message: str) -> None:
        """Log message to the parent suite.

        *Args:*\n
            _suite_ - Robot Framework test suite object.
            _message_ - message.
        """
        if suite.parent is None:
            LOGGER.error("{suite}: {message}".format(suite=suite, message=message))

    def _get_tr_tags_list(self) -> List[str]:
        """Get list of 'testrailid' tags.

        If required test statuses from the test run are passed to modifier,
        a request is made to the TestRail to obtain information about all the statuses.
        Theirs identifiers will be retrieved from list of all the statuses.
        This identifiers will be used to receive test tags in the required status.

        If statuses aren't passed to modifier,
        the tags of all tests in the test run will be obtained regardless of their status.

        Returns:
            List of tags.
        """
        status_ids = None
        if self.status_names:
            status_ids = [self.tr_client.get_status_id_by_status_label(name) for name in self.status_names]
        tests_info = self.tr_client.get_tests(run_id=self.run_id, status_ids=status_ids)
        return ['testrailid={}'.format(test["case_id"]) for test in tests_info if test["case_id"] is not None]

    def _get_tr_stable_tags_list(self) -> List[str]:
        """Get list of 'testrailid' tags of the stable test cases.

        If analysis depth of the run results is passed to modifier and its value greater than zero,
        a request is made to the TestRail to receive information about test cases whose last result is 'passed'.
        Based on the information received, the results of the latest runs for these test cases are analyzed,
        on the basis of which the tags of stable test cases will be received.

        Returns:
            List of stable tags.
        """
        stable_case_ids_list = list()
        catched_exceptions = list()
        passed_tests_info = self.tr_client.get_tests(run_id=self.run_id, status_ids=[TESTRAIL_STATUS_ID_PASSED])
        case_ids = [test["case_id"] for test in passed_tests_info if test["case_id"] is not None]

        def future_handler(future: Future) -> None:
            """Get result from future with try/except block and to list.
            Args:
                future: future object.
            """
            case_id = futures[future]
            try:
                case_results = future.result()
            except RequestException as exception:
                catched_exceptions.append(exception)
            else:
                passed_list = [result for result in case_results if
                               result['status_id'] == TESTRAIL_STATUS_ID_PASSED]
                if len(passed_list) == int(self.results_depth):
                    stable_case_ids_list.append(case_id)

        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self.tr_client.get_results_for_case, self.run_id, case_id, self.results_depth):
                       case_id for case_id in case_ids}

            for future in as_completed(futures, timeout=CONNECTION_TIMEOUT):
                future_handler(future)

        if catched_exceptions:
            raise catched_exceptions[0]
        return ['testrailid={}'.format(case_id) for case_id in stable_case_ids_list]

    def start_suite(self, suite: TestSuite) -> None:
        """Form list of tests for the Robot Framework test suite that are included in the TestRail test run.

        If analysis depth of the run results is greater than zero, when first suite is launched
        a list of 'testrailid' tags of stable test cases is obtained.
        After that the list of tags is written to the class attribute and for subsequent suites the obtaining is not happening.

        If analysis depth of the run results is zero, when the first suite is launched
        a list of 'testrailid' tags of all test cases in the given status is obtained.
        After that the list of tags is written to the class attribute and for subsequent suites the obtaining is not happening.

        *Args:*\n
            _suite_ - Robot Framework test suite object.
        """
        tests = suite.tests
        suite.tests = None
        try:
            if self.results_depth > 0:
                suite.tests = [t for t in tests if (set(t.tags) & set(self.tr_stable_tags_list))]
            else:
                suite.tests = [t for t in tests if (set(t.tags) & set(self.tr_tags_list))]
        except (RequestException, TimeoutError) as error:
            self._log_to_parent_suite(suite, str(error))

    def end_suite(self, suite: TestSuite) -> None:
        """Removing test suites that are empty after excluding tests that are not part of the TestRail test run.

        *Args:*\n
            _suite_ - Robot Framework test suite object.
        """
        suite.suites = [s for s in suite.suites if s.test_count > 0]
        if not suite.suites:
            self._log_to_parent_suite(suite, "No tests to execute after using TestRail pre-run modifier.")
