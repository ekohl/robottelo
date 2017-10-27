# coding=utf-8
"""Smoke tests for the basic foreman scenario.

:TestType: Functional
"""

# pylint: disable=missing-docstring,redefined-outer-name,too-many-arguments

import pytest
import requests
from fauxfactory import gen_string

from robottelo.cli.activationkey import ActivationKey
from robottelo.cli.capsule import Capsule
from robottelo.cli.contentview import ContentView
from robottelo.cli.host import Host
from robottelo.cli.lifecycleenvironment import LifecycleEnvironment
from robottelo.cli.org import Org
from robottelo.cli.product import Product
from robottelo.cli.proxy import Proxy
from robottelo.cli.repository import Repository
from robottelo.cli.subscription import Subscription
from robottelo.config import settings
from robottelo.ssh import command

DEMO_REPOS_URL = "https://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/"


def download_on_host(url, destination):
    command("curl -o {} {}".format(destination, url))


def temporary_object(request, cls, params, name_type='utf8'):
    if not params["name"]:
        params["name"] = gen_string(name_type)
    obj = cls.create(params)
    if 'organization-id' not in params:
        request.addfinalizer(lambda: cls.delete({"id": obj["id"]}))
    return obj


@pytest.fixture
def organization(request, name=None):
    params = {"name": name}
    return temporary_object(request, Org, params)


@pytest.fixture
def product(request, organization, name=None):
    params = {"name": name, "organization-id": organization["id"]}
    return temporary_object(request, Product, params)


@pytest.fixture
def puppet_repository(request, organization, product, name=None):
    params = {
        "name": name,
        "organization-id": organization["id"],
        "product-id": product["id"],
        "content-type": "puppet",
    }
    return temporary_object(request, Repository, params, "alpha")


@pytest.fixture
def yum_repository(request, organization, product, name=None,
                   url="https://jlsherrill.fedorapeople.org/fake-repos/needed-errata/"):
    params = {
        "name": name,
        "organization-id": organization["id"],
        "product-id": product["id"],
        "content-type": "yum",
        "url": url,
    }
    return temporary_object(request, Repository, params, "alpha")


@pytest.fixture
def lifecycleenvironment(request, organization, name=None, prior="Library"):
    params = {
        "name": name,
        "organization-id": organization["id"],
        "prior": prior,
    }
    return temporary_object(request, LifecycleEnvironment, params, "alpha")


@pytest.fixture
def contentview(request, organization, name=None):
    params = {
        "name": name,
        "organization-id": organization["id"],
    }
    return temporary_object(request, ContentView, params, "alpha")


@pytest.mark.foreman_pipeline
def test_puppet_self_registration():
    """
    Verify a host is registered after a puppet apply
    """
    response = requests.get(settings.server.get_url(), verify=False)
    response.raise_for_status()
    assert response.status_code == 200
    assert "login-form" in response.content

    result = command("puppet agent -t -v")
    assert result.return_code == 0

    response = requests.get(settings.server.get_url(), verify=False)
    response.raise_for_status()
    assert response.status_code == 200
    assert "login-form" in response.content

    assert settings.server.hostname in [proxy["name"] for proxy in Proxy().list()]

    assert settings.server.hostname in [host["name"] for host in Host().list()]


@pytest.mark.katello_pipeline
def test_katello_content(organization, product, yum_repository, puppet_repository,
                         contentview, lifecycleenvironment):
    download_on_host(DEMO_REPOS_URL + "test_errata_install/animaniacs-0.1-1.noarch.rpm",
                     "/tmp/animaniacs-0.1-1.noarch.rpm")
    Repository.upload_content({"id": yum_repository["id"], "organization-id": organization["id"],
                               "product-id": product["id"],
                               "path": "/tmp/animaniacs-0.1-1.noarch.rpm"})
    Repository.synchronize({"id": yum_repository['id'], "organization-id": organization["id"],
                            "product-id": product["id"]})

    download_on_host("https://forgeapi.puppetlabs.com/v3/files/stbenjam-dummy-0.2.0.tar.gz",
                     "/tmp/stbenjam-dummy-0.2.0.tar.gz")
    Repository.upload_content({"id": puppet_repository['id'],
                               "organization-id": organization["id"], "product-id": product["id"],
                               "path": "/tmp/stbenjam-dummy-0.2.0.tar.gz"})

    ContentView.add_repository({"id": contentview["id"], "organization-id": organization["id"],
                                "repository-id": yum_repository["id"]})
    ContentView.publish({"id": contentview["id"], "organization-id": organization["id"]})
    ContentView.version_promote({"organization-id": organization["id"],
                                 "content-view-id": contentview["id"],
                                 "from-lifecycle-environment": "Library",
                                 "to-lifecycle-environment": lifecycleenvironment["name"]})

    activationkey = ActivationKey.create({"name": gen_string("alpha"),
                                          "organization-id": organization["id"],
                                          "content-view-id": contentview["id"],
                                          "lifecycle-environment-id": lifecycleenvironment["id"],
                                          "unlimited-hosts": True})
    ActivationKey.update({"id": activationkey["id"], "organization-id": organization["id"],
                          "auto-attach": False})

    subscriptions = Subscription.list({"organization-id": organization["id"]})
    assert subscriptions
    subscription = subscriptions[0]

    ActivationKey.add_subscription({"id": activationkey["id"],
                                    "subscription-id": subscription["id"]})

    command("yum -y install subscription-manager")

    command('[ -e "/etc/rhsm/ca/candlepin-local.pem" ] && rpm -e `rpm -qf /etc/rhsm/ca/candlepin-local.pem`')

    command("subscription-manager unregister")
    command("subscription-manager clean")
    command("yum erase -y 'katello-ca-consumer-*'")
    command("rpm -Uvh http://{}/pub/katello-ca-consumer-latest.noarch.rpm".format(
        settings.server.hostname))
    result = command("subscription-manager register --force --org='{}' --username='{}' --password='{}' --env=Library".format(
        organization["label"], settings.server.admin_username, settings.server.admin_password))
    assert result.return_code == 0

    command("subscription-manager unregister")
    command("subscription-manager clean")
    result = command("subscription-manager register --force --org='{}' --activationkey='{}'".format(
        organization["label"], activationkey["name"]))
    assert result.return_code == 0


@pytest.mark.capsule_pipeline
def test_capsule_content_sync(organization, product):
    """
    Verify a capsule can sync content
    """
    proxies = Proxy.list({"search": "feature = 'Pulp Node'"})
    assert proxies
    proxy = proxies[0]

    content_view = "Test CV"

    Capsule().content_add_lifecycle_environment(
        {"id": proxy["id"], "environment": "Library", "organization-id": organization["id"]},
    )

    Capsule().content_synchronize({"id": proxy["id"]})

    # pylint: disable=line-too-long
    url1 = "http://{PROXY_HOSTNAME}/pulp/repos/{ORGANIZATION_LABEL}/Library/{CONTENT_VIEW_LABEL}/custom/{PRODUCT_LABEL}/{YUM_REPOSITORY_LABEL}/{FILENAME}"
    url2 = "http://{PROXY_HOSTNAME}/pulp/repos/{ORGANIZATION_LABEL}/Library/{CONTENT_VIEW_LABEL}/custom/{PRODUCT_LABEL}/{YUM_REPOSITORY_LABEL}/Packages/{FILENAME[0]}/{FILENAME}"
    # pylint: enable=line-too-long

    response = requests.get(url1.format(
        PROXY_HOSTNAME=proxy["name"],
        ORGANIZATION_LABEL=organization["name"].replace(" ", "_"),
        CONTENT_VIEW_LABEL=content_view.replace(" ", "_"),
        PRODUCT_LABEL=product["name"].replace(" ", "_"),
        FILENAME="walrus-0.71-1.noarch.rpm",
    ))

    if response.status_code == 404:
        response = requests.get(url2.format(
            PROXY_HOSTNAME=proxy["name"],
            ORGANIZATION_LABEL=organization["name"].replace(" ", "_"),
            CONTENT_VIEW_LABEL=content_view["name"].replace(" ", "_"),
            PRODUCT_LABEL=product["name"].replace(" ", "_"),
            FILENAME="walrus-0.71-1.noarch.rpm",
        ))

    response.raise_for_status()
    assert response.content
