# Start the MongoDB service
sudo systemctl start mongodb

# kill the running instance at port 5000
sudo kill $(lsof -t -i:5000)

python3 app_server/app.py
