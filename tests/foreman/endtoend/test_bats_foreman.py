# coding=utf-8
"""Smoke tests for the basic foreman scenario.

:TestType: Functional
"""

import requests

from robottelo.cli.host import Host
from robottelo.cli.proxy import Proxy
from robottelo.config import settings
from robottelo.ssh import command


def test_all():
    """
    Verify a host is registered after a puppet apply
    """
    response = requests.get(settings.server.get_url(), verify=False)
    response.raise_for_status()
    assert response.status_code == 200
    assert 'login-form' in response.content

    command('puppet agent -t -v')

    response = requests.get(settings.server.get_url(), verify=False)
    response.raise_for_status()
    assert response.status_code == 200
    assert 'login-form' in response.content

    assert settings.server.hostname in [proxy['name'] for proxy in Proxy().list()]

    assert settings.server.hostname in [host['name'] for host in Host().list()]
