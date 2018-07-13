# -*- coding: utf-8 -*-

from requests import post, get

DEFAULT_TESTRAIL_HEADERS = {'Content-Type': 'application/json'}
TESTRAIL_STATUS_ID_PASSED = 1


class TestRailAPIClient(object):
    """Library for working with [http://www.gurock.com/testrail/ | TestRail].

    == Dependencies ==
    | requests | https://pypi.python.org/pypi/requests |

    == Preconditions ==
    1. [ http://docs.gurock.com/testrail-api2/introduction | Enable TestRail API]
    """

    def __init__(self, server, user, password, run_id, protocol='http', hosted=None, project_id=None, suite_id=None):
        """Create TestRailAPIClient instance.

        *Args:*\n
            _server_ - name of TestRail server;\n
            _user_ - name of TestRail user;\n
            _password_ - password of TestRail user;\n
            _run_id_ - ID of the test run;\n
            _protocol_ - connecting protocol to TestRail server: http or https.\n
            _hosted_ - indicator to not use testrail in API url.\n
            _project_id - ID of the test project to create a run under, required if creating a new run.\n
            _suite_id_ - ID of the test suite to create a test run for, required if creating a new run.
        """
        if hosted:
            self._url = '{protocol}://{server}/index.php?/api/v2/'.format(protocol=protocol, server=server)
        else:
            self._url = '{protocol}://{server}/testrail/index.php?/api/v2/'.format(protocol=protocol, server=server)
        self._user = user
        self._password = password
        if run_id == "new":
            run_details = self.add_run(project_id=project_id, suite_id=suite_id, include_all=True)
            new_run_id = run_details['id']
            self.run_id = new_run_id
        else:
            self.run_id = run_id

    def _send_post(self, uri, data):
        """Perform post request to TestRail.

        *Args:* \n
            _uri_ - URI for test case;\n
            _data_ - json with test result.

        *Returns:* \n
            Request result in json format.
        """
        url = self._url + uri
        response = post(url, json=data, auth=(self._user, self._password), verify=False)
        response.raise_for_status()
        return response.json()

    def _send_get(self, uri, headers=None, params=None):
        """Perform get request to TestRail.

        *Args:* \n
            _uri_ - URI for test case;\n
            _headers_ - headers for http-request;\n
            _params_ - parameters for http-request.

        *Returns:* \n
            Request result in json format.
        """
        url = self._url + uri
        response = get(url, headers=headers, params=params, auth=(self._user, self._password), verify=False)
        response.raise_for_status()
        return response.json()

    def get_tests(self, run_id, status_ids=None):
        """Get tests from TestRail test run by run_id.

        *Args:* \n
            _run_id_ - ID of the test run;\n
            _status_ids_ - list of the required test statuses.

        *Returns:* \n
            Tests information in json format.
        """
        uri = 'get_tests/{run_id}'.format(run_id=run_id)
        if status_ids:
            status_ids = ','.join(str(status_id) for status_id in status_ids)
        params = {
            'status_id': status_ids
        }
        response = self._send_get(uri=uri, headers=DEFAULT_TESTRAIL_HEADERS, params=params)
        return response

    def get_results_for_case(self, run_id, case_id, limit=None):
        """Get results for case by run_id and case_id.

        *Args:* \n
            _run_id_ - ID of the test run;\n
            _case_id_ - ID of the test case;\n
            _limit_ - limit of case results.

        *Returns:* \n
            Cases results in json format.
        """
        uri = 'get_results_for_case/{run_id}/{case_id}'.format(run_id=run_id, case_id=case_id)
        params = {
            'limit': limit
        }
        response = self._send_get(uri=uri, headers=DEFAULT_TESTRAIL_HEADERS, params=params)
        return response

    def add_result_for_case(self, run_id, case_id, test_result_fields):
        """Add results for case in TestRail test run by run_id and case_id.

        *Supported request fields for test result:*\n
        | *Name*        | *Type*   | *Description*                                                |
        | status_id     | int      | The ID of the test status                                    |
        | comment       | string   | The comment / description for the test result                |
        | version       | string   | The version or build you tested against                      |
        | elapsed       | timespan | The time it took to execute the test, e.g. "30s" or "1m 45s" |
        | defects       | string   | A comma-separated list of defects to link to the test result |
        | assignedto_id | int      | The ID of a user the test should be assigned to              |
        | Custom fields are supported as well and must be submitted with their system name, prefixed with 'custom_' |

        *Args:* \n
            _run_id_ - ID of the test run;\n
            _case_id_ - ID of the test case;\n
            _test_result_fields_ - result of the test fields dictionary.

        *Example:*\n
        | Add Result For Case | run_id=321 | case_id=123| test_result={'status_id': 3, 'comment': 'This test is untested', 'defects': 'DEF-123'} |
        """
        uri = 'add_result_for_case/{run_id}/{case_id}'.format(run_id=run_id, case_id=case_id)
        self._send_post(uri, test_result_fields)

    def get_statuses(self):
        """Get test statuses information from TestRail.

        *Returns:* \n
            Statuses information in json format.
        """
        uri = 'get_statuses'
        response = self._send_get(uri=uri, headers=DEFAULT_TESTRAIL_HEADERS)
        return response

    def update_case(self, case_id, request_fields):
        """Update an existing test case in TestRail.

        *Supported request fields:*\n
        | *Name*       | *Type*   | *Description*                                                          |
        | title        | string   | The title of the test case (required)                                  |
        | template_id  | int      | The ID of the template (field layout) (requires TestRail 5.2 or later) |
        | type_id      | int      | The ID of the case type                                                |
        | priority_id  | int      | The ID of the case priority                                            |
        | estimate     | timespan | The estimate, e.g. "30s" or "1m 45s"                                   |
        | milestone_id | int      | The ID of the milestone to link to the test case                       |
        | refs         | string   | A comma-separated list of references/requirements                      |
        | Custom fields are supported as well and must be submitted with their system name, prefixed with 'custom_' |

        *Args:* \n
            _case_id_ - ID of the test case;\n
            _request_fields_ - request fields dictionary.

        *Returns:* \n
            Case information in json format.

        *Example:*\n
        | Update Case | case_id=213 | request_fields={'title': name, 'type_id': 1, 'custom_case_description': description, 'refs': references} |
        """
        uri = 'update_case/{case_id}'.format(case_id=case_id)
        response = self._send_post(uri, request_fields)
        return response

    def get_status_id_by_status_label(self, status_label):
        """Get test status id by status label.

        *Args:* \n
            _status_label_ - status label of the tests.

        *Returns:* \n
            Test status ID.
        """
        statuses_info = self.get_statuses()
        for status in statuses_info:
            if status['label'].lower() == status_label.lower():
                return status['id']
        raise Exception(u"There is no status with label \'{}\' in TestRail".format(status_label))

    def get_test_status_id_by_case_id(self, run_id, case_id):
        """Get test last status id by case id.
        If there is no last test result returns None.

        *Args:* \n
            _run_id_ - ID of the test run;\n
            _case_id_ - ID of the test case.

        *Returns:* \n
            Test status ID.
        """
        last_case_result = self.get_results_for_case(run_id=run_id, case_id=case_id, limit=1)
        return last_case_result[0]['status_id'] if last_case_result else None

    def get_project(self, project_id):
        """Get project info by project id.

        *Args:* \n
            _project_id_ - ID of the project.

        *Returns:* \n
            Request result in json format.
        """
        uri = 'get_project/{project_id}'.format(project_id=project_id)
        response = self._send_get(uri=uri, headers=DEFAULT_TESTRAIL_HEADERS)
        return response

    def get_suite(self, suite_id):
        """Get suite info by suite id.

        *Args:* \n
            _suite_id_ - ID of the test suite.

        *Returns:* \n
            Request result in json format.
        """
        uri = 'get_suite/{suite_id}'.format(suite_id=suite_id)
        response = self._send_get(uri=uri, headers=DEFAULT_TESTRAIL_HEADERS)
        return response

    def get_section(self, section_id):
        """Get section info by section id.

        *Args:* \n
            _section_id_ - ID of the section.

        *Returns:* \n
            Request result in json format.
        """
        uri = 'get_section/{section_id}'.format(section_id=section_id)
        response = self._send_get(uri=uri, headers=DEFAULT_TESTRAIL_HEADERS)
        return response

    def add_section(self, project_id, name, suite_id=None, parent_id=None, description=None):
        """Creates a new section.

        *Args:* \n
            _project_id_ - ID of the project;\n
            _suite_id_ - ID of the test suite(ignored if the project is operating in single suite mode);\n
            _parent_id_ - ID of the parent section (to build section hierarchies);\n
            _name_ - name of the section;\n
            _description_ - description of the section.

        *Returns:* \n
            New section information.
        """
        uri = 'add_section/{project_id}'.format(project_id=project_id)
        data = {'name': name}
        if suite_id is not None:
            data['suite_id'] = suite_id
        if parent_id is not None:
            data['parent_id'] = parent_id
        if description is not None:
            data['description'] = description

        response = self._send_post(uri=uri, data=data)
        return response

    def get_sections(self, project_id, suite_id):
        """Returns an existing section.

        *Args:* \n
            _project_id_ - ID of the project;\n
            _suite_id_ - ID of the test suite.

        *Returns:* \n
            Information about section.
        """
        uri = 'get_sections/{project_id}&suite_id={suite_id}'.format(project_id=project_id, suite_id=suite_id)
        response = self._send_get(uri=uri, headers=DEFAULT_TESTRAIL_HEADERS)
        return response

    def get_case(self, case_id):
        """Get case info by case id.

        *Args:* \n
            _case_id_ - ID of the test case.

        *Returns:* \n
            Request result in json format.
        """
        uri = 'get_case/{case_id}'.format(case_id=case_id)
        response = self._send_get(uri=uri, headers=DEFAULT_TESTRAIL_HEADERS)
        return response

    def get_cases(self, project_id, suite_id=None, section_id=None):
        """Returns a list of test cases for a test suite or specific section in a test suite.

        *Args:* \n
            _project_id_ - ID of the project;\n
            _suite_id_ - ID of the test suite (optional if the project is operating in single suite mode);\n
            _section_id_ - ID of the section (optional).

        *Returns:* \n
            Information about test cases in section.
        """
        uri = 'get_cases/{project_id}'.format(project_id=project_id)
        params = {'project_id': project_id}
        if suite_id is not None:
            params['suite_id'] = suite_id
        if section_id is not None:
            params['section_id'] = section_id

        response = self._send_get(uri=uri, headers=DEFAULT_TESTRAIL_HEADERS, params=params)
        return response

    def add_case(self, section_id, title, steps, description, refs, type_id, priority_id, **additional_data):
        """Creates a new test case.

        *Args:* \n
            _section_id_ - ID of the section;\n
            _title_ - title of the test case;\n
            _steps_ - test steps;\n
            _description_ - test description;\n
            _refs_ - comma-separated list of references;\n
            _type_id_ - ID of the case type;\n
            _priority_id_ - ID of the case priority;\n
            _additional_data_ - additional parameters.

        *Returns:* \n
            Information about new test case.
        """
        uri = 'add_case/{section_id}'.format(section_id=section_id)
        data = {
            'title': title,
            'custom_case_description': description,
            'custom_steps_separated': steps,
            'refs': refs,
            'type_id': type_id,
            'priority_id': priority_id
        }
        for key in additional_data:
            data[key] = additional_data[key]

        response = self._send_post(uri=uri, data=data)
        return response

    def add_run(self, project_id, suite_id=None, name=None, description=None, milestone_id=None, assignedto_id=None, include_all=None, case_ids=None):
        """Creates a new test run.

        *Args:* \n
            _project_id_ - ID of the project to add the test run to
            _suite_id_ - ID of the test suite for the test run
            _name_ - Name to give to the test run
            _description_ - Description of the test run
            _milestone_id_ - ID of the milestone to link the test run to
            _assignedto_id_ - ID of the user the test run should be assigned to
            _include_all_ - boolean to determine if all test cases within the suite should be added
            _case_ids_ -  comma separated list of test case IDs to use if the include all option is set to false

        *Returns:*\n
            Information about the new test run.
        """

        uri = 'add_run/{project_id}'.format(project_id=project_id)
        data = {'name': name}
        if suite_id is not None:
            data['suite_id'] = suite_id
        if name is not None:
            data['name'] = name
        if description is not None:
            data['description'] = description
        if milestone_id is not None:
            data['milestone_id'] = milestone_id
        if assignedto_id is not None:
            data['assignedto_id'] = assignedto_id
        if include_all is not None:
            data['include_all'] = include_all
        if case_ids is not None:
            data['case_ids'] = case_ids

        response = self._send_post(uri=uri, data=data)
        return response