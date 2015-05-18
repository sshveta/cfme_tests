# -*- coding: utf-8 -*-
import pytest
import re
from datetime import datetime, timedelta

from cfme.infrastructure.virtual_machines import Vm, details_page
from cfme.provisioning import provisioning_form
from cfme.services import requests
from cfme.web_ui import fill, flash
from utils import testgen, version
from utils.log import logger
from utils.providers import setup_provider
from utils.randomness import generate_random_string
from utils.wait import wait_for, TimedOutError


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.sel.go_to("dashboard"),
    pytest.mark.long_running
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(
        metafunc, 'provisioning', template_location=["provisioning", "template"])

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # No provisioning data available
            continue

        # required keys should be a subset of the dict keys set
        if not {'template', 'host', 'datastore'}.issubset(args['provisioning'].viewkeys()):
            # Need all three for template provisioning
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])
    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")