sudo apt-get -y install python3
sudo apt-get -y install pip
sudo apt-get -y install python3-venv
screen -Sm gamma bash -c "python3 -m venv .venv; source .venv/bin/activate; python3 -m pip install -r requirements.txt; exec sh"
