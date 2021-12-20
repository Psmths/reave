import magic


def serve_http(connection, proto_msg):
    mime = magic.Magic(mime=True)

    get_req = proto_msg.split("\n", 1)[0]
    # Serve index page (index.html)
    if "GET / HTTP" in get_req:
        get_r_filename = "/index.html"
    else:
        get_r_filename = get_req.split(" ")[1]

    try:
        r_file = open("resource/www" + get_r_filename, mode="rb")
        r_body_raw = r_file.read()
        r_file.close()
        r_headers = {
            "Content-Type": mime.from_file("resource/www" + get_r_filename),
            "Content-Length": len(r_body_raw),
            "Connection": "close",
        }
        r_status = "200"
        r_status_str = "OK"
    except (FileNotFoundError, IsADirectoryError):
        r_file = open("resource/www/404.html", mode="rb")
        r_body_raw = r_file.read()
        r_file.close()
        r_headers = {
            "Content-Type": "text/html",
            "Content-Length": len(r_body_raw),
            "Connection": "close",
        }
        r_status = "400"
        r_status_str = "NOT FOUND"

    r_headers_raw = "".join("%s: %s\n" % (k, v) for k, v in r_headers.items())
    r_proto = "HTTP/1.1"
    r_http_header = ("%s %s %s \n" % (r_proto, r_status, r_status_str)).encode()

    connection.send(r_http_header)
    connection.send(r_headers_raw.encode())
    connection.send("\n".encode())
    connection.send(r_body_raw)
    connection.close()
