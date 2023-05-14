#!/bin/bash

sudo apt install nodejs
sudo apt install npm

# Install Python and pip
sudo apt install -y python3 python3-pip

sudo apt-get update
sudo apt-get install -y libgl1-mesa-glx
sudo apt-get install pandoc

sudo apt install maven -y

# Install Python dependencies
pip3 install -r requirements.txt

python3 -m spacy download en_core_web_lg

# Additional installation steps
mkdir ~/file_uploads
# ...
