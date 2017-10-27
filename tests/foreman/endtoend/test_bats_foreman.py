# coding=utf-8
"""Smoke tests for the basic foreman scenario.

:TestType: Functional
"""

import requests
import pytest

from robottelo.cli.host import Host
from robottelo.cli.proxy import Proxy
from robottelo.cli.capsule import Capsule
from robottelo.config import settings
from robottelo.ssh import command


@pytest.mark.foreman_pipeline
def test_puppet_self_registration():
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


@pytest.mark.katello_pipeline
def test_capsule_content_sync():
    """
    Verify a capsule can sync content
    """
    proxies = Proxy().list(search='Feature = "Pulp Node"')
    assert len(proxies) >= 1
    proxy = proxies[0]

    organization = 'Test Organization'

    Capsule().content_add_lifecycle_environment(id=proxy['id'], environment='Library',
                                                organization=organization)

    Capsule().content_synchronize(id=proxy['id'])

    url1 = "http://{PROXY_HOSTNAME}/pulp/repos/{ORGANIZATION_LABEL}/Library/{CONTENT_VIEW_LABEL}/custom/{PRODUCT_LABEL}/{YUM_REPOSITORY_LABEL}/{FILENAME}"
    url2 = "http://{PROXY_HOSTNAME}/pulp/repos/{ORGANIZATION_LABEL}/Library/{CONTENT_VIEW_LABEL}/custom/{PRODUCT_LABEL}/{YUM_REPOSITORY_LABEL}/Packages/{FILENAME[0]}/{FILENAME}"

    response = requests.get(url1.format(
        PROXY_HOSTNAME=proxy['name'],
        ORGANIZATION_LABEL=organization.replace(' ', '_'),
        CONTENT_VIEW_LABEL='Test_CV',
        PRODUCT_LABEL='Test_Product',
        FILENAME="walrus-0.71-1.noarch.rpm",
    ))

    if response.status_code == 404:
        response = requests.get(url2.format(
            PROXY_HOSTNAME=proxy['name'],
            ORGANIZATION_LABEL=organization.replace(' ', '_'),
            CONTENT_VIEW_LABEL='Test_CV',
            PRODUCT_LABEL='Test_Product',
            FILENAME="walrus-0.71-1.noarch.rpm",
        ))

    response.raise_for_status()
    assert response.content
