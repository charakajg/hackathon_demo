#!/bin/bash

sudo apt update

curl -sL https://deb.nodesource.com/setup_14.x | sudo bash -

sudo apt-get install -y nodejs
sudo apt-get install gcc g++ make -y

# Install Python and pip
sudo apt install -y python3 python3-pip

sudo apt-get update
sudo apt-get install -y libgl1-mesa-glx
sudo apt-get install pandoc

# Install pdfimages
sudo apt-get install poppler-utils

sudo apt install maven -y

# Install Python dependencies
pip3 install -r requirements.txt

python3 -m spacy download en_core_web_lg

# Additional installation steps
mkdir -p ~/file_uploads
mkdir -p ~/aws/pdf_processor/files

# Install the Yarn package manager
sudo curl -sL https://dl.yarnpkg.com/debian/pubkey.gpg | gpg --dearmor | sudo tee /usr/share/keyrings/yarnkey.gpg >/dev/null
sudo echo "deb [signed-by=/usr/share/keyrings/yarnkey.gpg] https://dl.yarnpkg.com/debian stable main" | sudo tee /etc/apt/sources.list.d/yarn.list
sudo apt-get update && sudo apt-get install yarn
# ...
