#!/bin/bash
set -x

hash xml 2>/dev/null || {
    echo >&2 "Require xmlstarlet. Aborting, fix by: brew install xmlstarlet";
    exit 1;

}

function isVersion() {
    return $(sw_vers -productVersion | grep -q "^${1}")
}

function isSystemIntegrityProtectionEnabled() {
    return $(csrutil status | grep -q "enabled.$")
}

function isElCapitan()
{
    local identifier="10.11"
    return $(isVersion "${identifier}")
}

function getOverrideDirectory() {
    local root=/System/Library/Displays
    if isElCapitan; then
        root=${root}/Contents/Resources/Overrides
    else
        root=${root}/Overrides
    fi
    echo -n $root
}

if isElCapitan && isSystemIntegrityProtectionEnabled; then
   >&2 echo "Can not run while System Integrity Protection is Enabled."
   >&2 echo "Please disable: http://www.macworld.com/article/2986118/"
   exit -1
fi


rootDir=$(getOverrideDirectory)
result=($(ioreg -lw0 |
                 grep IODisplayPrefsKey |
                 sed 's@.*\([[:digit:]]\{3\}\)\-\([[:alnum:]]\{4\}\)"$@\1 \2@g'))
vendorId=DisplayVendorID-${result[0]}
if [ -d ${rootDir}/${vendorId} ]; then
    displayFile=DisplayProductID-${result[1]}
    if [ -f ${rootDir}/${vendorId}/${displayFile} ]; then
        xml ed -L \
            -a '//dict/key[text() = "scale-resolutions"]/following::data[last()]' \
            -t elem -n data -v AAAPAAAACWAAAAAB \
            ${rootDir}/${vendorId}/${displayFile}
    fi
fi
