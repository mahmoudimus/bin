#!/bin/bash

# https://gist.github.com/robwierzbowski/5430952/
# Create and push to a new github repo from the command line.
# Grabs sensible defaults from the containing folder and `.gitconfig`.
# Refinements welcome.

# Gather constant vars
CURRENTDIR=${PWD##*/}
GITHUBUSER=$(git config github.user)

# Get user input
# read "REPONAME?New repo name (enter for ${PWD##*/}):"
# read "USER?Git Username (enter for ${GITHUBUSER}):"
# read "DESCRIPTION?Repo Description:"

# echo "Here we go..."

# Curl some json to the github API oh damn we so fancy
# curl -u ${USER:-${GITHUBUSER}} https://api.github.com/user/repos -d "{\"name\": \"${REPONAME:-${CURRENTDIR}}\", \"description\": \"${DESCRIPTION}\", \"private\": false, \"has_issues\": true, \"has_downloads\": true, \"has_wiki\": false}"

# Set the freshly created repo to the origin and push
# You'll need to have added your public key to your github account

REPONAME=${1:?"Repo name?"}
CONFIG_FILE=${2:=~/.github.cfg}
_USER=$(awk -F '= ' '{if (! ($0 ~ /^;/) && $0 ~ /user/) print $2}' ${CONFIG_FILE})
_PASSWORD=$(awk -F '= ' '{if (! ($0 ~ /^;/) && $0 ~ /password/) print $2}' ${CONFIG_FILE})
PRIVATE=1

curl -u ${_USER}:${_PASSWORD} https://api.github.com/orgs/balanced-cookbooks/repos -d "{\"name\": \"${REPONAME:-${CURRENTDIR}}\", \"private\": ${PRIVATE}, \"has_issues\": true, \"has_downloads\": true, \"has_wiki\": false}"
RESULT=$?
if [ $RESULT -ne 0 ]; then
    echo "Failed to create repo"
    exit 1;
fi

curl -u ${_USER}:${_PASSWORD} -X PUT https://api.github.com/teams/538858/repos/balanced-cookbooks/${REPONAME} -d ""
RESULT=$?
if [ $RESULT -ne 0 ]; then
    echo "Failed to add the engineering team to the repo"
fi

curl -u ${_USER}:${_PASSWORD} -X PUT https://api.github.com/teams/640047/repos/balanced-cookbooks/${REPONAME} -d ""
RESULT=$?
if [ $RESULT -ne 0 ]; then
    echo "Failed to add the deployer team to the repo"
fi


curl -u ${_USER}:${_PASSWORD} https://api.github.com/repos/balanced-cookbooks/${REPONAME}/hooks -d '{"name":"hipchat", "config": {"auth_token": "<TOKEN>", "room": "dev"}, "events": ["commit_comment","download","fork","fork_apply","gollum","issues","issue_comment","member","public","pull_request","push","watch"], "active": true}'
RESULT=$?
if [ $RESULT -ne 0 ]; then
    echo "Failed to create repo hook"
    exit 1;
fi

if [ ! -d ".git" ]; then
    git init
    git add .
    git commit -m 'First commit'
fi

git remote add origin git@github.com:balanced-cookbooks/${REPONAME}.git
git push -u origin master
