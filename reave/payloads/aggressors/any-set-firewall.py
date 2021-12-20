class Payload:

    def __init__(self):

        self.info = {
            'name': 'any-set-firewall',
            'description': 'Enable or disable the host firewall.',
            'date': '2021-12-19',
            'author': 'PSMTHS',
            'compatibility': 'ESXi 6.7 EP 15,  Proxmox VE 4.0'
        }

        self.options = {
            'status': {
                'required': True,
                'info': 'Set to True to enable host inbound firewall, False to disable.',
                'defaults': True,
                'value': ''
            }
        }

        # Set payload options to defaults
        for option, value in self.options.items():
            value['value'] = value['defaults']

    def gen_payload(self):

        status = self.options['status']['value']

        payload_script = """
import os
import platform
host_platform = platform.platform()
if 'VMkernel' in host_platform:
    firewall_setting_str = 'true' if %(setting)s else 'false'
    os.system('esxcli network firewall set -e ' + firewall_setting_str)
if '-pve' in host_platform:
    if %(setting)s:
        os.system('iptables -P INPUT ACCEPT')
    else:
        os.system('iptables -P INPUT DROP')
        """ % {'setting': str(status)}

        return payload_script