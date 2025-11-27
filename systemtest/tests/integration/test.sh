#!/bin/bash
set -eu
set -x

# get to project root
cd ../../../

PATH=/usr/libexec:$PATH unittest discover python.tests.unit.integration
