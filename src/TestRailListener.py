# -*- coding: utf-8 -*-

import json
import re
import requests
import os
from typing import Any, Dict, List, Optional, Union
from robot.api import logger
from TestRailAPIClient import JsonDict, TestRailAPIClient

__author__ = "Dmitriy.Zverev"
__license__ = "Apache License, Version 2.0"


class TestRailListener(object):
    """Fixing of testing results and update test case in [ http://www.gurock.com/testrail/ | TestRail ].

    == Dependencies ==
    | past | https://pypi.org/project/past/ |
    | requests | https://pypi.python.org/pypi/requests |
    | robot framework | http://robotframework.org |
    | TestRailAPIClient |

    == Preconditions ==
    1. [ http://docs.gurock.com/testrail-api2/introduction | Enable TestRail API] \n
    2. Create custom field "case_description" with type "text", which corresponds to the Robot Framework's test case documentation.

    == Example ==
    1. Create test case in TestRail with case_id = 10\n
    2. Add it to test run with id run_id = 20\n
    3. Create autotest in Robot Framework
    | *** Settings ***
    | *** Test Cases ***
    | Autotest name
    |    [Documentation]    Autotest documentation
    |    [Tags]    testrailid=10    defects=BUG-1, BUG-2    references=REF-3, REF-4
    |    Fail    Test fail message
    4. Run Robot Framework with listener:\n
    | set ROBOT_SYSLOG_FILE=syslog.txt
    | robot --listener TestRailListener.py:testrail_server_name:tester_user_name:tester_user_password:20:https:update  autotest.robot
    5. Test with case_id=10 will be marked as failed in TestRail with message "Test fail message" and defects "BUG-1, BUG-2".
    Also title, description and references of this test will be updated in TestRail. Parameter "update" is optional.
    """

    ROBOT_LISTENER_API_VERSION = 2
    ELAPSED_KEY = 'elapsed'
    TESTRAIL_CASE_TYPE_ID_AUTOMATED = 1
    TESTRAIL_TEST_STATUS_ID_PASSED = 1
    TESTRAIL_TEST_STATUS_ID_FAILED = 5

    def __init__(self, server: str, user: str, password: str, run_id: str, protocol: str = 'http',
                 juggler_disable: str = None, update: str = None) -> None:
        """Listener initialization.

        *Args:*\n
            _server_ - name of TestRail server;\n
            _user_ - name of TestRail user;\n
            _password_ - password of TestRail user;\n
            _run_id_ - ID of the test run;\n
            _protocol_ - connecting protocol to TestRail server: http or https;\n
            _juggler_disable_ - indicator to disable juggler logic; if exist, then juggler logic will be disabled;\n
            _update_ - indicator to update test case in TestRail; if exist, then test will be updated.
        """
        testrail_url = '{protocol}://{server}/testrail/'.format(protocol=protocol, server=server)
        self._url = testrail_url + 'index.php?/api/v2/'
        self._user = user
        self._password = password
        self.run_id = run_id
        self.juggler_disable = juggler_disable
        self.update = update
        self.tr_client = TestRailAPIClient(server, user, password, run_id, protocol)
        self._vars_for_report_link: Optional[Dict[str, str]] = None
        logger.info('[TestRailListener] url: {testrail_url}'.format(testrail_url=testrail_url))
        logger.info('[TestRailListener] user: {user}'.format(user=user))
        logger.info('[TestRailListener] the ID of the test run: {run_id}'.format(run_id=run_id))

    def end_test(self, name: str, attributes: JsonDict) -> None:
        """ Update test case in TestRail.

        *Args:* \n
            _name_ - name of test case in Robot Framework;\n
            _attributes_ - attributes of test case in Robot Framework.
        """
        tags_value = self._get_tags_value(attributes['tags'])
        case_id = tags_value['testrailid']

        if not case_id:
            logger.warn(f"[TestRailListener] No case_id presented for test_case {name}.")
            return

        if 'skipped' in [tag.lower() for tag in attributes['tags']]:
            logger.warn(f"[TestRailListener] SKIPPED test case \"{name}\" with testrailId={case_id} "
                        "will not be posted to Testrail")
            return

        # Update test case
        if self.update:
            references = tags_value['references']
            self._update_case_description(attributes, case_id, name, references)
        # Send test results
        defects = tags_value['defects']
        old_test_status_id = self.tr_client.get_test_status_id_by_case_id(self.run_id, case_id)
        test_result = self._prepare_test_result(attributes, defects, old_test_status_id, case_id)
        try:
            self.tr_client.add_result_for_case(self.run_id, case_id, test_result)
        except requests.HTTPError as error:
            logger.error(f"[TestRailListener] http error on case_id = {case_id}\n{error}")

    def _update_case_description(self, attributes: JsonDict, case_id: str, name: str,
                                 references: Optional[str]) -> None:
        """ Update test case description in TestRail

        *Args:* \n
            _attributes_ - attributes of test case in Robot Framework;\n
            _case_id_ - case id;\n
            _name_ - test case name;\n
            _references_ - test references.
        """
        logger.info(f"[TestRailListener] update of test {case_id} in TestRail")
        description = f"{attributes['doc']}\nPath to test: {attributes['longname']}"
        request_fields: Dict[str, Union[str, int, None]] = {
            'title': name, 'type_id': self.TESTRAIL_CASE_TYPE_ID_AUTOMATED,
            'custom_case_description': description, 'refs': references}
        try:
            json_result = self.tr_client.update_case(case_id, request_fields)
            result = json.dumps(json_result, sort_keys=True, indent=4)
            logger.info(f"[TestRailListener] result for method update_case: {result}")
        except requests.HTTPError as error:
            logger.error(f"[TestRailListener] http error, while execute request:\n{error}")

    def _prepare_test_result(self, attributes: JsonDict, defects: Optional[str], old_test_status_id: Optional[int],
                             case_id: str) -> Dict[str, Union[str, int]]:
        """Create json with test result information.

        *Args:* \n
            _attributes_ - attributes of test case in Robot Framework;\n
            _defects_ - list of defects (in string, comma-separated);\n
            _old_test_status_id_ - old test status id;\n
            _case_id_ - test case ID.

        *Returns:*\n
            Dictionary with test results.
        """
        link_to_report = self._get_url_report_by_case_id(case_id)
        test_time = float(attributes['elapsedtime']) / 1000
        comment = f"Autotest name: {attributes['longname']}\nMessage: {attributes['message']}\nTest time:" \
                  f" {test_time:.3f} s"
        if link_to_report:
            comment += f'\nLink to Report: {link_to_report}'
        if self.juggler_disable:
            if attributes['status'] == 'PASS':
                new_test_status_id = self.TESTRAIL_TEST_STATUS_ID_PASSED
            else:
                new_test_status_id = self.TESTRAIL_TEST_STATUS_ID_FAILED
        else:
            new_test_status_id = self._prepare_new_test_status_id(attributes['status'], old_test_status_id)
        test_result: Dict[str, Union[str, int]] = {
            'status_id': new_test_status_id,
            'comment': comment,
        }
        elapsed_time = TestRailListener._time_span_format(test_time)
        if elapsed_time:
            test_result[TestRailListener.ELAPSED_KEY] = elapsed_time
        if defects:
            test_result['defects'] = defects
        return test_result

    def _prepare_new_test_status_id(self, new_test_status: str, old_test_status_id: Optional[int]) -> int:
        """Prepare new test status id by new test status and old test status id.
        Alias of this method is "juggler".
        If new test status is "PASS", new test status id is "passed".
        If new test status is "FAIL" and old test status id is null or "passed" or "failed",
        new test status id is "failed".
        In all other cases new test status id is equal to old test status id.

        *Args:* \n
            _new_test_status_ - new test status;\n
            _old_test_status_id_ - old test status id.

        *Returns:*\n
            New test status id.
        """
        old_statuses_to_fail = (self.TESTRAIL_TEST_STATUS_ID_PASSED, self.TESTRAIL_TEST_STATUS_ID_FAILED, None)
        if new_test_status == 'PASS':
            new_test_status_id = self.TESTRAIL_TEST_STATUS_ID_PASSED
        elif new_test_status == 'FAIL' and old_test_status_id in old_statuses_to_fail:
            new_test_status_id = self.TESTRAIL_TEST_STATUS_ID_FAILED
        else:
            assert old_test_status_id is not None
            new_test_status_id = old_test_status_id
        return new_test_status_id

    @staticmethod
    def _get_tags_value(tags: List[str]) -> Dict[str, Optional[str]]:
        """ Get value from robot framework's tags for TestRail.

        *Args:* \n
            _tags_ - list of tags.

        *Returns:* \n
            Dict with attributes.
        """
        attributes: Dict[str, Optional[str]] = dict()
        matchers = ['testrailid', 'defects', 'references']
        for matcher in matchers:
            for tag in tags:
                match = re.match(matcher, tag)
                if match:
                    split_tag = tag.split('=')
                    tag_value = split_tag[1]
                    attributes[matcher] = tag_value
                    break
                else:
                    attributes[matcher] = None
        return attributes

    @staticmethod
    def _time_span_format(seconds: Any) -> str:
        """ Format seconds to time span format.

        *Args:*\n
            _seconds_ - time in seconds.

        *Returns:*\n
            Time formatted in Time span.
        """
        if isinstance(seconds, float):
            seconds = int(seconds)
        elif not isinstance(seconds, int):
            seconds = 0
        if seconds <= 0:
            return ''
        s = seconds % 60
        res = "{}s".format(s)
        seconds -= s
        if seconds >= 60:
            m = (seconds % 60 ** 2) // 60
            res = "{}m {}".format(m, res)
            seconds -= m * 60
        if seconds >= 60 ** 2:
            h = seconds // 60 ** 2
            res = "{}h {}".format(h, res)
        return res

    @staticmethod
    def _get_vars_for_report_link() -> Dict[str, str]:
        """" Getting value from environment variables for prepare link to report.

        If test cases are started by means of CI, then must define the environment variables
        in the CI configuration settings to getting url to the test case report.
        The following variables are used:
            for Teamcity - TEAMCITY_HOST_URL, TEAMCITY_BUILDTYPE_ID, TEAMCITY_BUILD_ID,
                           REPORT_ARTIFACT_PATH, TORS_REPORT,
            for Jenkins  - JENKINS_BUILD_URL.
        If these variables are not found, then the link to report will not be formed.

        == Example ==
        1. for Teamcity
        |    Changing build configuration settings
        |    REPORT_ARTIFACT_PATH     output
        |    TORS_REPORT              report.html
        |    TEAMCITY_BUILD_ID        %teamcity.build.id%
        |    TEAMCITY_BUILDTYPE_ID    %system.teamcity.buildType.id%
        |    TEAMCITY_HOST_URL        https://teamcity.billing.ru

        2. for Jenkins
        |    add to the shell the execution of the docker container parameter
        |    -e "JENKINS_BUILD_URL = ${BUILD_URL}"

        *Returns:*\n
            Dictionary with environment variables results.
        """
        variables: Dict[str, str] = {}
        env_var = os.environ.copy()
        if 'TEAMCITY_HOST_URL' in env_var:
            try:
                teamcity_vars = {'TEAMCITY_HOST_URL',
                                 'TEAMCITY_BUILDTYPE_ID',
                                 'TEAMCITY_BUILD_ID',
                                 'REPORT_ARTIFACT_PATH'}
                variables = {var: env_var[var] for var in teamcity_vars}
            except KeyError:
                logger.error("[TestRailListener] There are no variables for getting a link to the report by tests.")
            if env_var.get('TORS_REPORT', '').strip():
                variables['TORS_REPORT'] = env_var['TORS_REPORT']
        elif 'JENKINS_BUILD_URL' in env_var:
            variables = {'JENKINS_BUILD_URL': env_var['JENKINS_BUILD_URL']}
        return variables

    @property
    def vars_for_report_link(self) -> Dict[str, str]:
        """Get variables for report link.

        Saves environment variables information once and then returns cached values.

        *Returns:*\n
            Cached variables for report link.
        """
        if not self._vars_for_report_link:
            self._vars_for_report_link = self._get_vars_for_report_link()
        return self._vars_for_report_link

    def _get_url_report_by_case_id(self, case_id: Union[str, int]) -> Optional[str]:
        """" Getting url for Report by id test case.

        *Args:* \n
            _case_id_ - test case ID.

        *Returns:*\n
            Report URL.
        """
        build_url = ''
        report_filename = self.vars_for_report_link.get('TORS_REPORT', 'report.html')
        report_uri = f'{report_filename}#search?include=testrailid={case_id}'
        if 'TEAMCITY_HOST_URL' in self.vars_for_report_link:
            vars = self.vars_for_report_link
            base_hostname = vars.get('TEAMCITY_HOST_URL')
            buildtype_id = vars.get('TEAMCITY_BUILDTYPE_ID')
            build_id = vars.get('TEAMCITY_BUILD_ID')
            report_artifact_path = vars.get('REPORT_ARTIFACT_PATH')
            build_url = f'{base_hostname}/repository/download/{buildtype_id}/{build_id}:id/{report_artifact_path}'
        elif 'JENKINS_BUILD_URL' in self.vars_for_report_link:
            build_url = self.vars_for_report_link['JENKINS_BUILD_URL'] + 'robot/report'
        return f'{build_url}/{report_uri}' if build_url else None
