#!/bin/bash -e
# https://github.com/XX-net/XX-Net/issues/8425#issuecomment-346916227

function status() {
    kextstat | grep net.tunnelblick.tap > /dev/null 2>&1 ;
    tap=$((1-$?))
    kextstat | grep net.tunnelblick.tun > /dev/null 2>&1 ;
    tun=$((1-$?))
}

# additional ethernet intf inside moby (ethN); default: 1
ethintf=${DOCKER_TAP_MOBY_ETH-1}
# name of the docker network to create; default: tap
network=${DOCKER_TAP_NETWORK-tap}
# tap intf to use on host (/dev/X); default: tap1
tapintf=${DOCKER_TAP_DEVICE-tap1}
# name of the docker network's bridge intf inside moby; default: br-$tapintf
netintf=${DOCKER_TAP_MOBY_BRIDGE-br-$tapintf}

err() { echo "$(tput setaf 9)$@$(tput sgr0)"; exit 1; }
exc() { echo "$(tput setaf 11)$@$(tput sgr0)"; }
log() { echo "$(tput setaf 10)$@$(tput sgr0)"; }

chown_tap_device() {
    test "$(stat -f %Su /dev/$tapintf)" = "$USER" && return # already done
    log Permit non-root usage of $tapintf device
    sudo chown $USER /dev/$tapintf
}

status

if [ "$1" == "tap" ] ; then
    if [ $tap == 1 ] ; then
  echo "Already tap"
    else
        sudo kextunload -b net.tunnelblick.tap
        sudo kextutil "/Applications/Tunnelblick.app/Contents/Resources/tap-signed.kext" -r "/Applications/Tunnelblick.app/Contents/Resources"
        chown_tap_device
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
