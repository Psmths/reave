import os
import json
import zlib
import base64
import logging
import configparser
from rich import print


class Protocol:
    ACK = '_response{"status" : "ACK"}'.encode()
    ERR_UNKNOWN_METHOD = '_response{"status" : "ERR_UNKNOWN_METHOD"}'.encode()
    logger = logging.getLogger(__name__)

    def STDOUT(json_stub):
        if json_stub["data"]:
            print(json_stub["data"])
        return '_response{"status" : "ACK"}'.encode()

    def STDERR(json_stub):
        if json_stub["data"]:
            print("[red]" + json_stub["data"] + "[/red]")
        return '_response{"status" : "ACK"}'.encode()

    def AGENT_ERROR(json_stub):
        return '_response{"status" : "ACK"}'.encode()

    # TODO: Stateful file transfer to handle interruptions
    def FILE_TRANSFER(json_stub):
        logging.debug("Handling FILE_TRANSFER")
        config = configparser.ConfigParser()
        config.read("reave/data/reave.conf")
        download_directory = config["reave"]["download_directory"]
        blob_data = zlib.decompress(base64.b85decode(json_stub["data"]))
        blob_offset = json_stub["offset"]
        blob_name = json_stub["filename"]
        if not os.path.exists(download_directory):
            os.makedirs(download_directory)
        file = os.path.join(download_directory, blob_name)
        with open(file, "ab") as b:
            b.seek(blob_offset)
            b.write(blob_data)
        response_packet_stub = {"status": "ACK", "offset": blob_offset}
        cmd_pkt = "_response" + json.dumps(response_packet_stub)
        return cmd_pkt.encode()
