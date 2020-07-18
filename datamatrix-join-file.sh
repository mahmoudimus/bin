#!/bin/zsh

set -euo pipefail
IFS=$'\n\t'

function join_image() {
    for file in *.png; do
        dmtxread $file >> printme.txt
    done
}


# foo() { echo "${@:2}" ;}
# echo "${@}"
# echo "---"
# echo "${*}"
join_image "${@}"
