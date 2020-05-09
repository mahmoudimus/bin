#!/bin/bash

set -x

# https://gist.github.com/nicolasembleton/afc19940da26716f8e90#gistcomment-2682108

# Docs I read
# https://gist.github.com/nicolasembleton/afc19940da26716f8e90
# https://gist.github.com/ralph-hm/a65840c4f5e439b90170d735a89a863f
# https://github.com/max-lobur/dotfiles/blob/master/sh/bt.sh

# Things I had to do beforehand
#brew install blueutil
# Restart bluetooth every time good ol' lappy wakes up:
#brew install sleepwatcher
#sudo mkdir -p /usr/local/sbin
#sudo chown -R $(whoami):staff /usr/local/sbin/
#brew link sleepwatcher
#/usr/local/sbin/sleepwatcher --verbose -w ~/.local/bin/restart-bluetooth
#brew services start sleepwatcher

# Stop all the bluetooth stuff
sudo kill -9 $(pgrep bluetoothd)
/usr/local/bin/blueutil -p 0

sudo kextunload -b com.apple.iokit.BroadcomBluetoothHostControllerUSBTransport
sudo kextunload -b com.apple.iokit.IOBluetoothHostControllerUARTTransport

sudo launchctl stop com.apple.blued

# Start enough of the bluetooth stuff

/usr/local/bin/blueutil -p 1
sudo launchctl start com.apple.blued
sudo kextload -b com.apple.iokit.BroadcomBluetoothHostControllerUSBTransport
