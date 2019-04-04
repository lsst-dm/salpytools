#!/usr/bin/env bash

# Config values
VERSION="tickets/DM-16255" # This is the git tag or branch
PRODUCT=salpytools
GIT_LSST="https://github.com/lsst-dm"
#INSTALL_PATH=/usr/local
#INSTALL_PATH=$HOME/test-install
INSTALL_PATH=/opt

# Change accordingly
PRODUCT_DIR=$INSTALL_PATH/$PRODUCT/$VERSION
INSTALL_DIR=$INSTALL_PATH/$PRODUCT/$VERSION/sandbox-install

# Git clone and version checkout
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR
git clone $GIT_LSST/$PRODUCT.git
cd $PRODUCT
git checkout $VERSION

# Build and install
echo "# INSTALL_DIR: "$INSTALL_DIR
echo "# PRODUCT_DIR: "$PRODUCT_DIR
mkdir -p $PRODUCT_DIR
export PYTHONPATH=$PYTHONPATH:$PRODUCT_DIR/python
python setup.py install --prefix=$PRODUCT_DIR --install-lib=$PRODUCT_DIR/python

# Clean up
echo "# Cleaning up:" $INSTALL_DIR
rm -rf $INSTALL_DIR

# Remember to set the paths
echo "# Remember to add the following line to your init config:"
echo ""
echo " source $PRODUCT_DIR/setpath.sh $PRODUCT_DIR"
echo ""

