import os
import json
import zlib
import base64

class Protocol:
    ACK = '_response{"status" : "ACK"}'.encode()
    ERR_UNKNOWN_METHOD = '_response{"status" : "ERR_UNKNOWN_METHOD"}'.encode()

    def STDOUT(json_stub):
        print(json_stub["data"])
        return ACK

    def STDERR(json_stub):
        print("[red]" + json_stub["data"] + "[/red]")
        return ACK

    def AGENT_ERROR(json_stub):
        return ACK

    def FILE_TRANSFER(json_stub):
        download_directory = "/tmp/downloads"
        blob_data = zlib.decompress(base64.b85decode(json_stub["data"]))
        blob_offset = json_stub["offset"]
        blob_name = json_stub["filename"]
        if not os.path.exists(download_directory):
            os.makedirs(download_directory)
        with open(download_directory + blob_name, "ab") as b:
            b.seek(blob_offset)
            b.write(blob_data)
        response_packet_stub = {"status": "ACK", "offset": blob_offset}
        cmd_pkt = "_response" + json.dumps(response_packet_stub)
        return cmd_pkt.encode()