#!/bin/bash
#2022-08-14 Erik Johnson - EkriirkE
edeb=$(ls -Art plex*.deb | tail -n 1)
wget -N --content-disposition "https://plex.tv/downloads/latest/5?channel=16&build=linux-aarch64&distro=debian&X-Plex-Token=xxxxxxxxxxxxxxxxxxxx"
deb=$(ls -Art plex*.deb | tail -n 1)
if [ "$edeb" == "$deb" ]; then
        echo "No new installation."
        exit 2
fi
dpkg -i "$deb"

#Comment out below if you wish to retain prior packages.  Otherwise only the most recently installed version is kept.
find . -maxdepth 1 -name "plex*.deb" ! -name "$deb" -type f -delete
