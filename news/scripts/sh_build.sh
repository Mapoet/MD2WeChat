#!/bin/bash
# Build the advanced control flow example
#
# Usage:
# ./scripts/sh_build.sh
#
cd ../build
cmake .. -DCMAKE_BUILD_TYPE=Debug -DTF_BUILD_WORKFLOW=ON
cmake --build . --target advanced_control_flow
./workflow/advanced_control_flow