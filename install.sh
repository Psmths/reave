#!/bin/bash

function generate_certificate() {
    echo "Generating certificate using config at" $(dirname "$0")/reave/conf/csr.conf
    mkdir -p $(dirname "$0")/reave/data
    openssl req -config $(dirname "$0")/reave/conf/csr.conf \
    -new -x509 -days 365 -nodes -out $(dirname "$0")/reave/data/cert.pem \
    -keyout $(dirname "$0")/reave/data/cert.pem \
    >/dev/null 2>&1
}

function chkconfig(){
    CONFIG_FILE=$(dirname "$0")/reave/conf/reave.conf
    if [ -f "$CONFIG_FILE" ]; then
        echo "$CONFIG_FILE already loaded."
    else 
        echo "$CONFIG_FILE does not exist, creating it"
        cp $(dirname "$0")/reave/resource/reave.conf.default $CONFIG_FILE
    fi
}

generate_certificate
chkconfig