#!/bin/bash
# This script will install the necessary items to have Docker
# run automatically on boot on OSX.


# This pulls in the docker-osx script. If it is not available
# in noplay's repo, you can get a mirrored copy from this repo.

curl https://raw.githubusercontent.com/noplay/docker-osx/0.10.0/docker-osx > /usr/local/bin/docker-osx
chmod +x /usr/local/bin/docker-osx

docker-osx start

mkdir /Applications/Docker/
curl https://raw.githubusercontent.com/amussey/blog-posts/master/2014/05_OSX-boot2docker-on-Startup/initialize_docker.sh > /Applications/Docker/initialize_docker.sh


# Load the launcher to make sure docker is up and running on boot.

curl https://raw.githubusercontent.com/amussey/blog-posts/master/2014/05_OSX-boot2docker-on-Startup/com.user.boot2docker.plist > launchctl load ~/Library/LaunchAgents/com.user.boot2docker.plist
launchctl load ~/Library/LaunchAgents/com.user.boot2docker.plist

if [ $(cat ~/.bash_profile | grep "eval \`docker-osx env\`" | wc -l) -eq 1 ] ; then 
   echo "eval `docker-osx env`" >> ~/.bash_profile
fi

source ~/.bash_profile
touch ~/.docker-osx-boot-launcher.log
