#!/bin/bash

# TODO:
# Add update support
# Check if git is installed, if not, install git?
# check if pip is installed, if not, fallback to easy_install

git clone git://github.com/jcrocholl/pep8.git
pushd $(pwd)
cd pep8
python setup.py build
sudo python setup.py install
popd
sudo rm -fr pep8
ln -s $(which pep8) ~/bin/pep8

wget http://sourceforge.net/projects/pychecker/files/pychecker/0.8.18/pychecker-0.8.18.tar.gz/download
tar xzvf pychecker-0.8.18.tar.gz
pushd $(pwd)
cd pychecker-0.8.18
python setup.py build
sudo python setup.py install
popd
sudo rm -fr pychecker-0.8.18
ln -s $(which pychecker) ~/bin/pychecker

sudo pip install pylint
ln -s $(which pylint) ~/bin/pylint
