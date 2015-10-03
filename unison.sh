#!/bin/bash

# create ssh-config file
ssh_config="$PWD/.vagrant/ssh-config"
vagrant ssh-config > "$ssh_config"

# create unison profile
profile="
root = .
root = ssh://default//home/mahmoud/code/
ignore = Name {.git,.vagrant,*.swp,.DS_Store,*.pyc,.idea,*.egg-info,dist,.#*}

prefer = .
repeat = 2
terse = true
dontchmod = true
perms = 0
sshargs = -F $ssh_config
"

# write profile

if [ -z ${USERPROFILE+x} ]; then
  UNISONDIR=$HOME
else
  UNISONDIR=$USERPROFILE
fi

cd $UNISONDIR
[ -d .unison ] || mkdir .unison
echo "$profile" > .unison/myproject.prf
