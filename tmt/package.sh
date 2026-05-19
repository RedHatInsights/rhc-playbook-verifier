#!/bin/bash
# Create an RPM package.
set -euo pipefail

cd ../
make mock

# COPR may already have installed another version of these packages
dnf --assumeyes remove rhc-playbook-signer rhc-playbook-verifier
dnf --assumeyes install mock/rhc-playbook-verifier-*.noarch.rpm

# The executable is intentionally absent from the default paths.
/usr/libexec/rhc-playbook-verifier --version
