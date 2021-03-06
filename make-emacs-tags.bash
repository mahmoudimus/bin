#!/bin/bash
: <<EOF
# Code mostly stolen from: http://code.google.com/p/python-etags/

Python-etags is a shell script of use to folks who use emacs for python programming.

It runs etags over each entry in your python's sys.path.  Recall that sys.path is where
python looks for included modules.  Recall that emacs uses TAGS files, generated by
etags, to quickly find symbols via meta-<dot> and other commands.

Once you've downloaded this, just invoke:

  do_tags

After it runs will be one oddly named <foo>.tag file for each entry
entry in sys.path.  These can then be included into your program's
own TAGS file using --include.

Create tags files via etags for python.  The script found here will
fill this directory with <foo>.tags files.  One for each entry in
python's sys.path variable, i.e. your module search path.  <foo> is
replaced by the md5 of the entry's directory name.

Hints.

It maybe useful to set PYTHON_PATH so that etag files are made for other
python libraries.

For example here's a find command I use to build the PYTHON_PATH for google's
app engine.

  find /usr/local/googl_appengine -exec test -f '{}/__init__.py' \; -prune

My individual projects have Makefiles, and those know how to build thier
TAGS, as so:

TAGS :
     etags `find . -type f`
     etags --append --include=`echo ${PTAGS}/*.tags | sed 's/ / --include=/g'`

With PTAGS set to where ever I've got this module installed.

EOF


# TAGSDIR=$(cd `dirname $0` && pwd)
TAGSDIR=${1-${HOME}/emacs-tags}

if [ ! -d ${TAGSDIR} ]; then
    mkdir ${TAGSDIR}
    echo "Created ${TAGSDIR}"
fi

rm -f ${TAGSDIR}/*.tags

for ENTRY in `python -c 'import sys; print " ".join(sys.path)'` ; do
    if [ -d ${ENTRY} ]; then
        cd ${ENTRY}
        # pipe to md5sum and strip off the - at the end
        TAGFILE=${TAGSDIR}/$(pwd | md5sum | sed 's@  -$@@').tags
        if [ -f ${TAGFILE} ]; then
            echo "Skipping duplicate ${ENTRY} (aka `pwd`)"
        else
            echo "${ENTRY} --> ${TAGFILE}"
            find ${ENTRY} -type f | etags --output ${TAGFILE} -
        fi
    fi
done
