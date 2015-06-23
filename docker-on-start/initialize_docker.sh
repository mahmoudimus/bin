#!/bin/bash

echo -e "\n\n\n"                      >> ~/.docker-osx-boot-launcher.log
date                                  >> ~/.docker-osx-boot-launcher.log
echo "==============================" >> ~/.docker-osx-boot-launcher.log
/usr/local/bin/docker-osx start       >> ~/.docker-osx-boot-launcher.log
echo "==============================" >> ~/.docker-osx-boot-launcher.log
echo "boot2docker completed."         >> ~/.docker-osx-boot-launcher.log
