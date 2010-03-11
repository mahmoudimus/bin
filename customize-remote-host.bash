#!/bin/bash

TARGET_HOST=${1?"What's the target host pal?"}
TARGET_USERNAME=${2-${USER}}
SSH_KEY_DIR=${HOME}/.ssh

if [ -e ${SSH_KEY_DIR}/id_rsa.pub ]; then
    export SSH_KEY=${SSH_KEY_DIR}/id_rsa.pub
fi

if [ -e ${SSH_KEY_DIR}/id_dsa.pub ]; then
    export SSH_KEY=${SSH_KEY_DIR}/id_dsa.pub
fi

TO_DEPLOY="${HOME}/.bashrc ${HOME}/.alias.bash ${HOME}/.inputrc"

# get your key over there
ssh ${TARGET_USERNAME}@${TARGET_HOST} "mkdir ~/.ssh; echo $(cat ${SSH_KEY}) >> ~/.ssh/authorized_keys2"

for deployee in ${TO_DEPLOY}; do
    scp ${deployee} ${TARGET_USERNAME}@${TARGET_HOST}:~
done
