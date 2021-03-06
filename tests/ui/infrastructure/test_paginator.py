import pytest
from unittestzero import Assert

class TestPaginator:
    def test_paginator(self, setup_infrastructure_providers, infra_vms_pg):
        Assert.true(infra_vms_pg.is_the_current_page)
        Assert.true(infra_vms_pg.paginator.selected_per_page, '20')
        infra_vms_pg.paginator.set_per_page('100')
        Assert.true(infra_vms_pg.paginator.selected_per_page, '100')
