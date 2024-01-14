# Microservice-Architecture-and-System-Design-with-Python-Kubernetes

![architecture](documentation_images/architecture.png)

This project is a step-by-step code walkthrough of the **Microservice Architecture and System Design with Python Kubernetes** project. The credit goes to freeCodeCamp.org. And its youtube video can be found at: https://www.youtube.com/watch?v=hmkF77F9TLw. 

### Installation and Setup

1. Install Docker for Desktop
2. Install kubectl
3. Install minikube
4. Install K9s
5. Install Python 3 
6. Install Mysql
7. Install MongoDB


- [1. Setup Auth Service](1_set_up_Auth_Service.md)
- [2. Setup Gateway Service](2_set_up_Gateway_Service.md)
- [3. Setup RabbitMQ Service](3_set_up_RabbitMQ_Service.md)
- [4. Setup Converter Service](4_set_up_Converter_Service.md)
- [5. Setup Notification Service](5_set_up_Notification_Service.md)


**<u><b>Things that can be improved further</b></u>

Currently, in our Python code, the RabbitMQ connection is established at the start of the application. If the connection drops, our application won't reconnect unless restarted. 

To integrate a more robust RabbitMQ connection with reconnection logic into our existing Flask application, we can modify the way we create and use the RabbitMQ connection. Instead of establishing the connection globally at the start, we'll create a function to handle RabbitMQ operations, which includes establishing a connection and gracefully handling reconnection attempts in case of failure.

Edit the server.py in gateway as follows: 
```
import os, gridfs, pika, json, time
from flask import Flask, request, send_file
from flask_pymongo import PyMongo
from auth import validate
from auth_svc import access
from storage import util
from bson.objectid import ObjectId

server = Flask(__name__)

mongo_video = PyMongo(
    server,
    uri="mongodb://host.minikube.internal:27017/videos"
)

mongo_mp3 = PyMongo(
    server,
    uri="mongodb://host.minikube.internal:27017/mp3s"
)

fs_videos = gridfs.GridFS(mongo_video.db)
fs_mp3s = gridfs.GridFS(mongo_mp3.db)

def get_rabbitmq_channel():
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
            return connection.channel()
        except pika.exceptions.AMQPConnectionError:
            print("Connection to RabbitMQ failed. Retrying in 5 seconds...")
            time.sleep(5)

@server.route("/login", methods=["POST"])
def login():
    token, err = access.login(request)

    if not err:
        return token
    else:
        return err
    
@server.route("/upload", methods=["POST"])
def upload():
    access, err = validate.token(request)

    if err:
        return err

    print('access content:', access)
    print('err content:', err)

    access = json.loads(access)

    if access is None:
        return "No data provided", 400  # 400 Bad Request

    if access["admin"]:
        if len(request.files) > 1 or len(request.files) < 1:
            return "exactly 1 file required", 400

        # (Your existing upload logic)
        # Before calling util.upload, ensure RabbitMQ channel is established
        channel = get_rabbitmq_channel()

        for _, f in request.files.items():
            err = util.upload(f, fs_videos, channel, access)
        
            if err:
                return err
        
        return "success!", 200
    else: 
        return "not authorized", 401

@server.route("/download", methods=["GET"])
def download():
    access, err = validate.token(request)
    
    if err:
        return err
    
    print('access content(download): ', access)
    print('err content(download): ', err)

    access = json.loads(access)

    if access is None:
        return "No data provided", 400  # 400 Bad Request

    if access["admin"]:
        fid_string = request.args.get("fid")

        if not fid_string:
            return "fid is required", 400
        
        try:
            out = fs_mp3s.get(ObjectId(fid_string))
            return send_file(out, download_name=f"{fid_string}.mp3")
        except Exception as err:
            print(err)
            return "internal server error", 500

    return "not authorized", 401
        
if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8080)

```

In this modified code:

- I've added a `get_rabbitmq_channel()` function that attempts to connect to RabbitMQ and returns a channel. If the connection fails, it waits for 5 seconds before retrying.
- In the `/upload` endpoint, I call `get_rabbitmq_channel()` to ensure that we have a valid channel before proceeding with the upload logic. This ensures that if the RabbitMQ connection was down, the application will attempt to reconnect before processing the request.

This approach provides a basic reconnection mechanism. However, depending on the specifics of your application, you might need to implement more sophisticated error handling and reconnection logic, especially if you have long-running operations or if you need to ensure message delivery in the face of network interruptions.

The end. Thank you.