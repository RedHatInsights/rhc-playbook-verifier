#!/bin/bash
set -eu
set -x

# get to project root
cd ../../../

PATH=/usr/libexec:$PATH python3 -m unittest discover python.tests.integration
