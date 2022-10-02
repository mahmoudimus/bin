#!/bin/sh

XML_ENTITLEMENT_LOCATION=${HOME}/.config
XML_ENTITLEMENT_FILENAME=gdb-entitlement.xml
GDB_CERT_NAME=gdb-cert-euler
GDB_BIN_LOCATION=$(which gdb)

codesign \
    --entitlements ${XML_ENTITLEMENT_LOCATION}/${XML_ENTITLEMENT_FILENAME} \
    -fs ${GDB_CERT_NAME} \
    ${GDB_BIN_LOCATION}
