import magic


def serve_http(proto_msg):
    mime = magic.Magic(mime=True)

    get_req = proto_msg.split("\n", 1)[0]
    # Serve index page (index.html)
    if "GET / HTTP" in get_req:
        get_r_filename = "/index.html"
    else:
        get_r_filename = get_req.split(" ")[1]
    try:
        r_file = open("reave/resource/www" + get_r_filename, mode="rb")
        r_body_raw = r_file.read()
        r_file.close()
        r_headers = {
            "Content-Type": mime.from_file("reave/resource/www" + get_r_filename),
            "Content-Length": len(r_body_raw),
            "Connection": "close",
        }
        r_status = "200"
        r_status_str = "OK"
    except (FileNotFoundError, IsADirectoryError) as e:
        r_file = open("reave/resource/www/404.html", mode="rb")
        r_body_raw = r_file.read()
        r_file.close()
        r_headers = {
            "Content-Type": "text/html",
            "Content-Length": len(r_body_raw),
            "Connection": "close",
        }
        r_status = "404"
        r_status_str = "NOT FOUND"

    r_headers_raw = "".join("%s: %s\n" % (k, v) for k, v in r_headers.items())
    r_proto = "HTTP/1.1"
    r_http_header = ("%s %s %s \n" % (r_proto, r_status, r_status_str)).encode()

    return(r_http_header + r_headers_raw.encode() + "\n".encode() + r_body_raw)
