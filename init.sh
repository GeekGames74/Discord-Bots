sudo apt-get -y install python3
sudo apt-get -y install pip
sudo apt-get -y install python3-venv
python3 -m venv .venv
source .venv/bin/activate
screen -S gamma
python3 -m pip install -r requirements.txt