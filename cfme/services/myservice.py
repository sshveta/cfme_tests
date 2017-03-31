from widgetastic.widget import Text, View
from widgetastic_manageiq import Accordion, ManageIQTree, Calendar, SummaryFormItem
from widgetastic_patternfly import Input, BootstrapSelect, Dropdown, Button, CandidateNotFound
from cfme.web_ui import toolbar as tb, Quadicon
from cfme.fixtures import pytest_selenium as sel
from navmazing import NavigateToAttribute, NavigateToSibling
from cfme import BaseLoggedInPage
from utils.update import Updateable
from utils.appliance import Navigatable, current_appliance
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.log import logger
from utils.wait import wait_for
from utils import version


class MyServicesView(BaseLoggedInPage):
    def in_explorer(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Services', 'MyServices'])

    @property
    def is_displayed(self):
        return self.in_explorer and self.configuration.is_displayed and not self.myservice.is_dimmed

    @View.nested
    class myservice(Accordion):  # noqa
        ACCORDION_NAME = "Services"

        tree = ManageIQTree()

    configuration = Dropdown('Configuration')
    policy_btn = Dropdown('Policy')
    lifecycle_btn = Dropdown('Lifecycle')
    download_choice = Dropdown('Download')


class ServiceRetirementForm(MyServicesView):
    title = Text('#explorer_title_text')

    retirement_date = Calendar('retirementDate')
    retirement_warning = BootstrapSelect('retirement_warn')


class ServiceEditForm(MyServicesView):
    title = Text('#explorer_title_text')

    name = Input(name='name')
    description = Input(name='description')


class SetOwnershipForm(MyServicesView):
    title = Text('#explorer_title_text')

    select_owner = BootstrapSelect('user_name')
    select_group = BootstrapSelect('group_name')


class EditTagsForm(MyServicesView):
    title = Text('#explorer_title_text')

    select_tag = BootstrapSelect('tag_cat')
    select_value = BootstrapSelect('tag_add')


class MyServiceDetailView(MyServicesView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_explorer and self.myservice.is_opened and
            self.title.text == 'Service "{}"'.format(self.context['object'].name)
        )


class EditMyServiceView(ServiceEditForm):
    title = Text("#explorer_title_text")

    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and self.myservice.is_opened and
            self.title.text == 'Editing Service "{}"'.format(self.context['object'].name)
        )


class SetOwnershipView(SetOwnershipForm):
    title = Text("#explorer_title_text")

    save_button = Button('Save')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and self.myservice.is_opened and
            self.title.text == 'Set Ownership of Service "{}"'.format(self.context['object'].name)
        )


class EditTagsView(EditTagsForm):
    title = Text("#explorer_title_text")

    save_button = Button('Save')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and self.myservice.is_opened and
            self.title.text == 'Edit Tags of Service "{}"'.format(self.context['object'].name)
        )


class ServiceRetirementView(ServiceRetirementForm):
    title = Text("#explorer_title_text")

    save_button = Button('Save')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and self.myservice.is_opened and
            self.title.text == 'retire Service "{}"'.format(self.context['object'].name)
        )


class ReconfigureServiceView(SetOwnershipForm):
    title = Text("#explorer_title_text")

    save_button = Button('Save')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and self.myservice.is_opened and
            self.title.text == 'Reconfigure Service "{}"'.format(self.context['object'].name)
        )


class MyService(Updateable, Navigatable):

    def __init__(self, name, description=None, vm_name=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.description = description
        self.vm_name = vm_name

    def wait_for_vm_retire(self):
        """ Waits for self.vm_name to go to the off state and returns state

        Args:
        Returns: A string representing the VM state
        """
        def get_vm_details():
            power_state = SummaryFormItem('Power Management', 'Power State')

            logger.debug('Service VM power state: {}'.format(power_state))
            if power_state == 'unknown':
                # The VM power state is unknown, check lifecycle instead of power
                retire_state = SummaryFormItem('Lifecycle', 'Retirement state')
                return retire_state == 'Retired'
            else:
                # VM power is a known state, use ith
                return power_state == 'off'

        quadicon = Quadicon(self.vm_name, "vm")
        sel.click(quadicon)

        wait_for(
            get_vm_details,
            fail_func=tb.refresh,
            num_sec=120 * 60,
            delay=10,
            message="Service VM power off wait"
        )
        return SummaryFormItem('Power Management', 'Power State')

    def retire(self):
        view = navigate_to(self, 'Details')
        view.lifecycle_btn.item_select("Retire this Service", handle_alert=True)
        if self.obj.appliance.version < '5.8':
            view.flash.assert_success_message(
                'Retirement initiated for 1 Service from the {} Database'.format(
                    current_appliance.product_name))
        # wait for service to retire
        wait_for(
            lambda: SummaryFormItem('Lifecycle', 'Retirement State') == 'Retired',
            fail_func=tb.refresh,
            num_sec=10 * 60,
            delay=3,
            message='Service Retirement wait'
        )
        # wait for any vms to shutdown, this method leaves the page on the VM details
        if self.vm_name is not None:
            vm_state = self.wait_for_vm_retire()
            assert vm_state in ['off', 'unknown']

    def retire_on_date(self, retirement_date):
        view = navigate_to(self, 'SetRetirement')
        view.fill({'retirement_date': retirement_date})
        view.save.click()
        view = navigate_to(self, 'Details')
        wait_for(
            lambda: SummaryFormItem('Lifecycle', 'Retirement State') == 'Retiring',
            fail_func=tb.refresh,
            num_sec=5 * 60,
            delay=5,
            message='Service Retirement'
        )
        # wait for any vms to shutdown, this method leaves the page on the VM details
        vm_state = self.wait_for_vm_retire()
        assert vm_state in ['off', 'unknown']

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(MyServiceDetailView, override=updates)
        assert view.is_displayed
        view.flash.assert_success_message('Service "{}" was saved'.
            format(updates.get('name', self.name)))

    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except CandidateNotFound:
            return False

    def delete(self):
        view = navigate_to(self, 'Details')
        view.configuration.item_select(
            version.pick({
                version.LOWEST: 'Remove Service from the VMDB',
                '5.7': 'Remove Service'}),
            handle_alert=True)
        view = self.create_view(MyServiceAll)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_success_message(
            'Service "{}": Delete successful'.format(self.description or self.name))

    def set_ownership(self, owner, group):
        view = navigate_to(self, 'SetOwnership')
        view.fill({'select_owner': owner,
                   'select_group': group})
        view.save_button.click()
        view = self.create_view(MyServiceDetailView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_success_message('Ownership saved for selected Service')

    def edit_tags(self, tag, value):
        view = navigate_to(self, 'EditTags')
        view.fill({'select_tag': tag,
                   'select_value': value})
        view.save_button.click()
        view = self.create_view(MyServiceDetailView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_success_message('Tag edits were successfully saved')

    def check_vm_add(self, add_vm_name):
        view = navigate_to(self, 'Details')
        quadicon = Quadicon(add_vm_name, "vm")
        sel.click(quadicon)
        view.flash.assert_no_errors()

    def download_file(self, extension):
        view = navigate_to(self, 'All')
        view.download_choice.item_select("Download as " + extension)
        view.flash.assert_no_errors()


@navigator.register(MyService, 'All')
class MyServiceAll(CFMENavigateStep):
    VIEW = MyServicesView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Services', 'My Services')


@navigator.register(MyService, 'Details')
class MyServiceDetails(CFMENavigateStep):
    VIEW = MyServiceDetailView

    prerequisite = NavigateToSibling('All')

    def step(self):
        if self.obj.appliance.version > '5.8':
            self.prerequisite_view.myservice.tree.click_path("Active Services", self.obj.name)
        else:
            self.prerequisite_view.myservice.tree.click_path("All Services", self.obj.name)


@navigator.register(MyService, 'Edit')
class MyServiceEdit(CFMENavigateStep):
    VIEW = EditMyServiceView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit this Service')


@navigator.register(MyService, 'SetOwnership')
class MyServiceSetOwnership(CFMENavigateStep):
    VIEW = SetOwnershipView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Set Ownership')


@navigator.register(MyService, 'EditTags')
class MyServiceEditTags(CFMENavigateStep):
    VIEW = EditTagsView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.policy_btn.item_select('Edit Tags')


@navigator.register(MyService, 'SetRetirement')
class MyServiceSetRetirement(CFMENavigateStep):
    VIEW = ServiceRetirementView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        if self.obj.appliance.version > '5.8':
            self.prerequisite_view.lifecycle_btn.item_select('Set Retirement Date for this Service')
        else:
            self.prerequisite_view.lifecycle_btn.item_select('Set Retirement Date')


@navigator.register(MyService, 'Reconfigure')
class MyServiceReconfigure(CFMENavigateStep):
    VIEW = ReconfigureServiceView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Reconfigure this Service')
