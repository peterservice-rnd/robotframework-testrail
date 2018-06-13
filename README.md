# RobotFramework Testrail

[![Build Status](https://travis-ci.org/peterservice-rnd/robotframework-testrail.svg?branch=master)](https://travis-ci.org/peterservice-rnd/robotframework-testrail)

Short Description
---

[Robot Framework](http://www.robotframework.org) library, listener and pre-run modifier for working with TestRail.

Installation
---

```
pip install robotframework-testrail
```

Documentation
---

See documentation on [GitHub](https://github.com/peterservice-rnd/robotframework-testrail/tree/master/docs).

Usage
---

[How to enable TestRail API](http://docs.gurock.com/testrail-api2/introduction)

### TestRail API Client

Library for working with [TestRail](http://www.gurock.com/testrail/).

#### Example

```robot
*** Settings ***
Library    TestRailAPIClient    host    user    password    run_id

*** Test Cases ***
Case
    ${project}=    Get Project    project_id
    ${section}=    Add Section    project_id=${project['id']    name=New Section
    ${case}=       Add Case    ${section['id']}    Title    Steps    Description    Refs    type_id    priority_id
    Update Case    ${case['id']}    request_fields
```

### TestRail Listener

Fixing of testing results and updating test cases.

#### Example

1. Create custom field "case_description" with type "text", which corresponds to the Robot Framework's test case documentation.

2. Create Robot test:

    ```robot
    *** Test Cases ***
    Autotest name
        [Documentation]    Autotest documentation
        [Tags]    testrailid=10    defects=BUG-1, BUG-2    references=REF-3, REF-4
        Fail    Test fail message
    ```

3. Run Robot Framework with listener:

    ```
    pybot --listener TestRailListener.py:testrail_server_name:tester_user_name:tester_user_password:run_id:https:update  robot_suite.robot
    ```

    Test with case_id=10 will be marked as failed in TestRail with message "Test fail message" and defects "BUG-1, BUG-2".
    
    Also title, description and references of this test will be updated in TestRail. Parameter "update" is optional.

### TestRail Pre-run Modifier

Pre-run modifier for starting test cases from a certain test run.

#### Example

1. Create Robot test:
    ```robot
    *** Test Cases ***
        Autotest name 1
        [Documentation]    Autotest 1 documentation
        [Tags]    testrailid=10
        Fail    Test fail message
        Autotest name 2
        [Documentation]    Autotest 2 documentation
        [Tags]    testrailid=11
        Fail    Test fail message
    ```

2. Run Robot Framework with pre-run modifier:

    ```
    pybot --prerunmodifier TestRailPreRunModifier:testrail_server_name:tester_user_name:tester_user_password:run_id:http:results_depth robot_suite.robot
    ```

    Only test cases that are included in the test run _run_id_ will be executed.

3. To execute tests from TestRail test run only with a certain status, for example "failed" and "blocked":

    ```
    pybot --prerunmodifier TestRailPreRunModifier:testrail_server_name:tester_user_name:tester_user_password:run_ind:http:results_depth:failed:blocked robot_suite.robot
    ```

License
---

Apache License 2.0