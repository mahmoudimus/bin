#!/bin/bash
# https://gist.github.com/davidjpeacock/394a250c106e0a9cfddd
SUBDIR_NAME=${1:?"Repo subdir name?"}
OLD_REMOTE=${2:?"Path?"}
BRANCH=${3:-"master"}

function strategy_one() {
    git remote add -f ${SUBDIR_NAME} ${OLD_REMOTE}
    mkdir -p ${SUBDIR_NAME}

    git merge ${SUBDIR_NAME}/${BRANCH}

    for e in `/bin/ls -1A ${OLD_REMOTE}`; do
        git mv $e ${SUBDIR_NAME};
    done
    git ci -m "merging ${OLD_REMOTE} into ${SUBDIR_NAME}"
}

function strategy_two() {
    git remote add -f ${SUBDIR_NAME} ${OLD_REMOTE}
    git merge -s ours --no-commit ${SUBDIR_NAME}/master
    git read-tree --prefix=${SUBDIR_NAME}/ -u ${SUBDIR_NAME}/master
    git add .
    git ci -m "merging ${OLD_REMOTE} into ${SUBDIR_NAME}"
}


strategy_one
