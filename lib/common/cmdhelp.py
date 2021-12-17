from lib.common.termcolor import colors

doc = {
    'payload': {
        'list': ['list', 'List all loaded payloads.'],
        'info': ['info <payload name>', 'List payload info of specified payload or current payload.'],
        'use': ['use <payload name>', 'Select payload to use.'],
        'set': ['set <option> <value>', 'Set payload option to specified value.'],
        'run agent': ['run agent <agent uuid>','Run the selected payload on the specified agent.'],
        'run listener': ['run listener <listener uuid>','Run the selected payload on all agents on the specified listener.']
    },
    'agent': {
        'list': ['list', 'List all registered agents.'],
        'interact': ['interact', 'Enter interactive command line. "quit" to exit'],
        'create': ['create', 'Start creating a new agent script.']
    },
    'listener':{
        'list': ['list', 'List all active listeners.'],
        'add': ['add <host> <port> <secret>', 'Create and start a new listener.'],
        'remove': ['remove <uuid>', 'Remove specified listener.'],
    }
}

def cmd_help(context,command):
    print(colors.YELLOW)
    print(doc[context][command][0] + '\t' + doc[context][command][1])
    print(colors.ENDC)

def context_help(context):
    if context:
        for cmd, tooltip in doc[context].items():
            print(colors.YELLOW + colors.BOLD + tooltip[0] + colors.ENDC + colors.YELLOW + colors.ITALIC + '\n\t' + tooltip[1] + '\n' + colors.ENDC)
    else:
        print(colors.YELLOW)
        print('Quickstart: https://github.com/Psmths/reave/blob/main/doc/commands.md\n')
        print('Available contexts:')
        for cmd in doc:
            print('\t' + cmd)
        print(colors.ENDC)