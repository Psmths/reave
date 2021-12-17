class Payload:
    """
    Payload object describes a payload to run on an agent and provides
    the method gen_payload() to generate a payload with the appropriate
    user-selected options.
    """
    def __init__(self):

        self.info = {
            'name': 'any_get_login_history',
            'description': 'Get successful login attempts from host logs',
            'date': '2021-12-12',
            'author': 'PSMTHS',
            'compatibility': 'ESXi 6.7 EP 15,  Proxmox VE 4.0'
        }

        self.options = {}

    def set_defaults(self):
        """
        Set payload options to defaults
        """
        for option, value in self.options.items():
            value['value'] = value['defaults']

    def gen_payload(self):

        self.set_defaults()

        payload_script = """
import os
os.system('cat /var/log/auth.log | grep -E '(Accepted)' | grep -E '(for)'')
        """

        return payload_script
