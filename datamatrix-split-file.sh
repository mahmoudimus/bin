#!/bin/zsh

set -euo pipefail
IFS=$'\n\t'

function split_to_image() {
    FILENAME=${1}
    cat ${FILENAME} | split -b 1500 - part-
    rm ${FILENAME}
    for part in part-*; do
        dmtxwrite -e 8 ${part} > ${part}.png
    done
}


# foo() { echo "${@:2}" ;}
# echo "${@}"
# echo "---"
# echo "${*}"
split_to_image "${@}"
