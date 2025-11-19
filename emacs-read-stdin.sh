# Adapted from https://github.com/davidshepherd7/emacs-read-stdin/blob/master/emacs-read-stdin.sh
# If the second argument is - then write stdin to a tempfile and open the
# tempfile. (first argument will be `--no-wait` passed in by the plugin.zsh)
if [ $# -ge 2 -a "$2" = "-" ]; then
    # Create a tempfile to hold stdin
    tempfile="$(mktemp --tmpdir emacs-stdin-$USERNAME.XXXXXXX 2>/dev/null \
    || mktemp -t emacs-stdin-$USERNAME)" # support BSD mktemp
    # Redirect stdin to the tempfile
    cat - > "$tempfile"
    # Reset $2 to the tempfile so that "$@" works as expected
    set -- "$1" "$tempfile" "${@:3}"
fi

emacsfun "$@"
