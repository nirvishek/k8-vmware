from os import environ
from pprint import pprint
from unittest import TestCase
from osbot_utils.utils.Misc import random_string
from pytest import skip

from k8_vmware.Config import Config
from k8_vmware.vsphere.ESXI_Ssh import ESXI_Ssh
from k8_vmware.vsphere.Sdk import Sdk


class test_ESXI_Ssh(TestCase):

    def setUp(self) -> None:
        self.ssh        = ESXI_Ssh()
        self.ssh_config = self.ssh.ssh_config()
        self.ssh_user   = self.ssh_config.get('ssh_user')
        self.ssh_key    = self.ssh_config.get('ssh_key')
        if self.ssh_key is None:
            skip("Skipping test because environment variable ssh_host is not configured")

    # base methods
    def test_exec_ssh_command(self):
        assert self.ssh.exec_ssh_command(       ) == {'error': '', 'output': 'VMkernel\n', 'status': True}
        assert self.ssh.exec_ssh_command('uname') == {'error': '', 'output': 'VMkernel\n', 'status': True}
        assert self.ssh.exec_ssh_command('aaaa' ) == {'error': 'sh: aaaa: not found\n', 'output': '', 'status': False}

    def test_get_get_ssh_params(self):
        ssh_params = self.ssh.get_ssh_params('aaa')
        assert ssh_params == ['-t', '-i', environ.get('ESXI_SSH_KEY'),
                              environ.get('VSPHERE_USERNAME') + '@' + environ.get('VSPHERE_HOST'),
                              'aaa']

    def test_exec(self):
        #self.ssh.exec('uname'        ) == 'VMkernel'
        self.ssh.exec('cd /bin ; pwd') == '/bin'

    def test_ssh_config(self):
        config = self.ssh.ssh_config()
        assert config['ssh_host'] == environ.get('VSPHERE_HOST'    )
        assert config['ssh_user'] == environ.get('VSPHERE_USERNAME')
        assert config['ssh_key' ] == environ.get('ESXI_SSH_KEY'    )

    # helper methods

    def test_uname(self):
        assert self.ssh.uname() == 'VMkernel'

    def test_pwd(self):
        #result = self.ssh.pwd()

        #pprint(self.ssh.exec('esxcli system version get'))
        pprint(self.ssh.exec('esxcli system'))
        #pprint(self.ssh.uname())

    # helper methods: esxcli

    def test_esxcli(self):
        assert "Usage: esxcli [options] {namespace}+ {cmd} [cmd options]" in self.ssh.esxcli('')

    def test_esxcli_json(self):
        assert set(self.ssh.esxcli_json('network ip dns server list')) == {'DNSServers'}

    def test_esxcli_system_account_create(self):
        user_id     = f"user_{random_string()}"
        password    = f"pwd_{random_string()}"
        role        = 'Admin'
        description = f"description_{random_string()}"

        # create user
        assert self.ssh.esxcli_system_account_create(user_id, password, description) == ''
        assert self.ssh.esxcli_system_account_create(user_id, password, description) == f"The specified key, name, or identifier '{user_id}' already exists."


        # make user an admin
        assert self.ssh.esxcli_system_permission_set(user_id, role) == ''
        assert user_id in self.ssh.esxcli_system_permission_list(index_by="Principal").keys()

        # confirm user can login and execute commands on the server
        config = Config()                                                                                           # get config object
        server_details = config.vsphere_server_details()                                                            # store original values
        config.vsphere_set_server_details(username=user_id, password=password)                                      # set values with newly created temp account
        assert Sdk().about_name() == 'VMware ESXi'                                                                  # confirms we are able to login and make calls to the SOAP API
        config.vsphere_set_server_details(username=server_details['username'], password=server_details['password']) # reset the server details to the original values
        Sdk.cached_service_instance = None                                                                          # remove cache
        assert Sdk().about_name() == 'VMware ESXi'                                                                  # confirm all is good

        # remove user from Admin group
        assert self.ssh.esxcli_system_permission_unset(user_id) == ''                                               # remove user role
        assert user_id not in self.ssh.esxcli_system_permission_list(index_by="Principal").keys()                   # confirm user is not there

        # remove user
        assert self.ssh.esxcli_system_account_remove(user_id) == ''                                                 # delete user
        assert self.ssh.esxcli_system_account_remove(user_id) == f"The user or group named '{user_id}' does not exist."

    def test_esxcli_system_account_list(self):
        users = self.ssh.esxcli_system_account_list(index_by='UserID')
        assert self.ssh_user  in set(users)
        assert set(users[self.ssh_user]) == {'Description', 'UserID'}

    def test_esxcli_system_hostname_get(self):
        assert sorted(set(self.ssh.esxcli_system_hostname_get())) == ['DomainName', 'FullyQualifiedDomainName', 'HostName']

    def test_esxcli_system_permission_list(self):
        users = self.ssh.esxcli_system_permission_list(index_by='Principal')
        assert users.get('root').get("Role") == 'Admin'

    def test_esxcli_system_stats_installtime_get(self):
        date = self.ssh.esxcli_system_stats_installtime_get()
        assert date.year == 2020

    def test_esxcli_system_version_get(self):
        assert set(self.ssh.esxcli_system_version_get()) == {'Product', 'Patch', 'Version', 'Update', 'Build'}





