import os
import cmd
import readline
import threading
from rich.table import Column, Table
from rich.console import Console
from common.listener import Listener
from common.agent import Agent 
from common.cmdhelp import cmd_help, context_help


class MainMenu(cmd.Cmd):

    def __init__(self, agents, listeners, payloads):

        cmd.Cmd.__init__(self)
        readline.set_completer_delims(' ')

        self.agents = agents
        self.listeners = listeners
        self.payloads = payloads
        self.console = Console()
        self.context = None
        self.payload = None
        self.agent = None
        self.prompt = '> '        

    def complete_interact(self, text, line, begidx, endidx):
        if self.context == 'agent':
            return [i for i, a in self.agents.items() if i.startswith(text)]
            
    def complete_use(self, text, line, begidx, endidx):
        if self.context == 'payload':
            return [i for i in self.payloads.loaded_payloads if i.startswith(text)]

    def do_help(self,cmd):
        if self.context:
            context_help(self.context.split(' ')[0])
        else:
            context_help(None)

    def emptyline(self):
         pass

    def update_prompt(self):
        if self.payload:
            self.prompt = (self.context + '(' + self.payload.info['name'] + ') > ' if self.context else '(' + self.payload.info['name'] + ') > ')
        else:
            self.prompt = (self.context + ' > ') if self.context else '> '

    def do_listener(self, cmd):
        self.context = 'listener'
        self.update_prompt()

    def do_agent(self, cmd):
        self.context = 'agent'
        self.update_prompt()

    def do_payload(self, cmd):
        self.context = 'payload'
        self.update_prompt()

    def do_back(self, cmd):
        self.context = None
        self.update_prompt()

    def do_add(self,cmd):
        try:
            assert self.context == 'listener'
        except:
            print('wrong context')
            return
        try:
            assert len(cmd.split()) == 3
        except:
            cmd_help('listener', 'add')
            return
        cmd = cmd.split()
        host = cmd[0]
        port = cmd[1]
        secret = cmd[2]
        try:
            port = int(port)
        except:
            cmd_help('listener', 'add')
            return
        self.add_listener(host,port,secret)

    def do_list(self, cmd):
        try:
            assert self.context != None
        except:
            print('No context specified')
            return
        if self.context == 'listener':
            self.list_listener()
        if self.context == 'payload':
            self.list_payload()
        if self.context == 'agent':
            self.list_agent()

    def do_ls(self, cmd):
        self.do_list(cmd)

    def do_interact(self, cmd):
        try:
            assert self.context == 'agent'
        except:
            print('wrong context')
            return
        try:
            assert len(cmd.split()) == 1
        except:
            cmd_help('agent', 'interact')
            return
        cmd = cmd.split()
        uuid = cmd[0]
        try:
            assert uuid in self.agents
        except:
            print('Agent not found!')
            return
        
        print('Entering interactive session. Type quit to end session.')
        while True:
            interactive_cmd = input(uuid[0:7] + ' > ')
            if interactive_cmd == 'quit': break
            self.agents[uuid].add_command(interactive_cmd)

    def do_use(self,cmd):
        try:
            assert self.context == 'payload'
        except:
            print('wrong context')
            return
        try:
            assert len(cmd.split()) == 1
        except:
            cmd_help('payload', 'use')
            return
        cmd = cmd.split()
        payload_name = cmd[0]
        self.payload = self.payloads.get_payload_by_name(payload_name)
        if self.payload:
            self.update_prompt()
        else:
            print('Payload not found!')

    def do_info(self,cmd):
        try:
            assert self.context == 'payload' or self.context == 'agent'
        except:
            print('wrong context')
            return
        if self.context == 'payload':
            if not self.payload:
                try:
                    assert len(cmd.split()) == 1
                except:
                    cmd_help('payload', 'info')
                    return
                cmd = cmd.split()
                p = self.payloads.get_payload_by_name(cmd[0])
                if p:
                    self.payloads.print_payloads_info(p)
                else:
                    print('Payload not found!')
            else:
                self.payloads.print_payloads_info(self.payload)
        if self.context == 'agent':
            try:
                assert len(cmd.split()) == 1
            except:
                cmd_help('agent', 'info')
                return
            cmd = cmd.split()
            uuid = cmd[0]
            try:
                assert uuid in self.agents
            except:
                print('Agent not found!')
                return
            print(self.agents[uuid].enumdata)


    def do_set(self,cmd):
        try:
            assert self.context == 'payload'
        except:
            print('wrong context')
            return
        try:
            assert self.payload != None
        except:
            print('No payload selected!')
            return
        try:
            assert len(cmd.split()) >= 2
        except:
            cmd_help('payload', 'set')
            return
        cmd = cmd.split()
        option = cmd[0]
        value = ' '.join(cmd[1:])
        try:
            assert option in self.payload.options
        except:
            print('Invalid option selected!')
            return
        if value == 'False' or value == 'false':
            self.payload.options[option]['value'] = False
        elif value == 'True' or value == 'true':
            self.payload.options[option]['value'] = True
        elif value == 'None' or value == 'none':
            self.payload.options[option]['value'] = None 
        else:
            self.payload.options[option]['value'] = value

    def do_run(self,cmd):
        try:
            assert self.context == 'payload'
        except:
            print('wrong context')
            return
        try:
            assert self.payload != None
        except:
            print('No payload selected!')
            return
        try:
            assert len(cmd.split()) == 2
        except:
            cmd_help('payload', 'run agent')
            # cmd_help('payload', 'run listener')
            return
        cmd = cmd.split()
        script = self.payload.gen_payload()
        if cmd[0] == 'agent':
            uuid = cmd[1]
            try:
                assert uuid in self.agents
            except:
                print('Agent not found!')
                return
            self.agents[uuid].add_payload(script)


    def list_listener(self):
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("UUID")
        table.add_column("Listen Host")
        table.add_column("Listen Port")
        table.add_column("Secret Key")
        for listener in self.listeners:
            table.add_row(
                str(listener.uuid),
                listener.host,
                str(listener.port),
                listener.secret
            )
        self.console.print(table)


    def list_payload(self):
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name")
        table.add_column("Description")
        for payload_name, payload in self.payloads.loaded_payloads.items():
            table.add_row(
                payload_name,
                payload.info['description']
            )
        self.console.print(table)

    def list_agent(self):
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("UUID")
        table.add_column("Last Observed")
        table.add_column("Platform")
        table.add_column("Hostname")
        for uuid, agent in self.agents.items():
            a_status = '[green]' + str(agent.lastseen) + '[/green]'
            if agent.beacon_expired():
                a_status = '[red](!) ' + str(agent.lastseen) + '[/red]'

            table.add_row(
                uuid,
                a_status,
                'Proxmox' if 'pve' in agent.get_platform() else 'ESX/i',
                agent.get_hostname()
            )
        self.console.print(table)

    def add_listener(self, host, port, secret):
        l = Listener(port,
                    host,
                    secret, 
                    self.agents,
                    self.listeners)
        threading.Thread(target=l.main_thread).start()