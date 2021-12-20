#!/bin/bash

function generate_certificate() {
    mkdir -p $(dirname "$0")/../data
    openssl req -new -x509 -days 365 -nodes -out $(dirname "$0")/../data/cert.pem -keyout $(dirname "$0")/../data/cert.pem
}

generate_certificate