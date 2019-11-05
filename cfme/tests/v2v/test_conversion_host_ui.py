"""Test to validate End-to-End migrations- functional testing."""
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.v2v_fixtures import set_conversion_host_for_rhev_ui
from cfme.fixtures.v2v_fixtures import set_conversion_instance_for_osp_ui
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION

pytestmark = [
    test_requirements.v2v,
    pytest.mark.provider(
        classes=[RHEVMProvider, OpenStackProvider],
        selector=ONE_PER_VERSION,
        required_flags=["v2v"],
        scope="module",
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_VERSION,
        fixture_name="source_provider",
        required_flags=["v2v"],
        scope="module",
    ),
    pytest.mark.usefixtures("v2v_provider_setup"),
]


def test_add_conversion_host_ui_crud(appliance, source_provider, provider):
    if provider.one_of(RHEVMProvider):
        set_conversion_host_for_rhev_ui(appliance, source_provider, provider, "VDDK")
    else:
        set_conversion_instance_for_osp_ui(appliance, source_provider, provider, "VDDK")
    # TODO : Add Remove conversion host test
