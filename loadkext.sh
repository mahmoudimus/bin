#!/bin/bash
# https://github.com/XX-net/XX-Net/issues/8425#issuecomment-346916227

function status() {
    kextstat | grep net.tunnelblick.tap > /dev/null 2>&1 ;
    tap=$((1-$?))
    kextstat | grep net.tunnelblick.tun > /dev/null 2>&1 ;
    tun=$((1-$?))
}

status

if [ "$1" == "tap" ] ; then
    if [ $tap == 1 ] ; then
  echo "Already tap"
    else
        sudo kextunload -b net.tunnelblick.tap
        sudo kextutil "/Applications/Tunnelblick.app/Contents/Resources/tap-signed.kext" -r "/Applications/Tunnelblick.app/Contents/Resources"
    fi
elif [ "$1" == "tun" ] ; then
    if [ $tun == 1 ] ; then
  echo "Already tun"
    else
        sudo kextunload -b net.tunnelblick.tun
        sudo kextutil "/Applications/Tunnelblick.app/Contents/Resources/tun-signed.kext" -r "/Applications/Tunnelblick.app/Contents/Resources"
    fi
elif [ "$1" == "status" ] ; then
    echo "tap = $tap"
    echo "tun = $tun"
else
    echo "Run $0 <tap|tun|status>"
fi
