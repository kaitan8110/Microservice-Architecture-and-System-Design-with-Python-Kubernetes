### Setup Converter Service

Create a `converter` directory. This is going to be the consumer service that pull the messages off the video queue.
```
mkdir converter
cd converter
```

Create a Python virtual environment in `converter` directory. And activates it.
```
python3 -m venv venv
source ./venv/bin/activate
```
 
Create a `consumer.py` file.
```
vim consumer.py
```

Fill in below code. Save and exit.
```
import pika, sys, os, time
from pymongo import MongoClient
import gridfs
from convert import to_mp3

def main():
    client = MongoClient("host.minikube.internal", 27017)
    db_videos = client.videos
    db_mp3s = client.mp3s

    # gridfs
    fs_videos = gridfs.GridFS(db_videos)
    fs_mp3s = gridfs.GridFS(db_mp3s)

    # rabbitmq connection
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host="rabbitmq")
    )
    channel = connection.channel()

    def callback(ch, method, properties, body):
        err = to_mp3.start(body, fs_videos, fs_mp3s, ch)
        if err:
            ch.basic_nack(delivery_tag=method.delivery_tag)
        else:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue=os.environ.get("VIDEO_QUEUE"), on_message_callback=callback
    )
    
    print("Waiting for messages. To exit press CTRL+C")

    channel.start_consuming()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
```

Next, we need to install the dependencies. 
```
pip3 install pika pymongo
```

Next, we need to create the `convert` package. Change directory to it. 
```
mkdir convert
cd convert
```

Initialise as a package. 
```
touch __init__.py
```

Create a module named `to_mp3.py`. 
```
vim to_mp3.py
```

Fill in below code. Save and exit.
```
import pika, json, tempfile, os
from bson.objectid import ObjectId
import moviepy.editor

def start(message, fs_videos, fs_mp3s, channel):
    message = json.loads(message)

    # empty temp file
    tf = tempfile.NamedTemporaryFile()
    # video contents
    out = fs_videos.get(ObjectId(message["video_fid"]))
    # add video contents to empty file
    tf.write(out.read())
    # create audio from temp video file
    audio = moviepy.editor.VideoFileClip(tf.name).audio
    tf.close()

    # write audio to the file
    tf_path = tempfile.gettempdir() + f"/{message['video_fid']}.mp3"
    audio.write_audiofile(tf_path)

    # save file to mongo
    f = open(tf_path, "rb")
    data = f.read()
    fid = fs_mp3s.put(data)
    f.close()
    os.remove(tf_path)

    message["mp3_fid"] = str(fid)

    try:
        channel.basic_publish(
            exchange="",
            routing_key=os.environ.get("MP3_QUEUE"),
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            ),
        )
    except Exception as err:
        fs_mp3s.delete(fid)
        return "failed to publish message"
```

Install `moviepy`.
```
pip3 install moviepy
```

Now we need to create our Dockerfile, and our kubernetes deployments to create the service within our cluster. 

Let's freeze our dependencies to `requirements.txt` file first. 
```
pip3 freeze > requirements.txt
```

Create a Dockerfile.
```
vim Dockerfile
```

Fill in below code. Save and exit.
```
FROM python:3.10-slim-bullseye

RUN apt-get update \
    && apt-get install -y --no-install-recommends --no-install-suggests \
    build-essential ffmpeg \
    && pip install --no-cache-dir --upgrade pip

WORKDIR /app
COPY ./requirements.txt /app
RUN pip install --no-cache-dir --requirement /app/requirements.txt
COPY . /app

CMD ["python3", "consumer.py"]
```

Run docker build.
```
docker build .
```

Tag the image. 
```
docker tag <Paste-in-sha256> <your-docker-username>/converter:latest
```

Run docker push . 
```
docker push <your-docker-username>/converter:latest
```

Create a manifests directory and change directory to it.
```
mkdir manifests
cd manifests
```

Create a `convert-deploy.yaml` file. 
```
vim convert-deploy.yaml
```

Fill in below code. Save and exit.
```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: converter
  labels:
    app: converter
spec:
  replicas: 4
  selector:
    matchLabels:
      app: converter
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 8
  template:
    metadata:
      labels:
        app: converter
    spec:
      containers:
        - name: converter
          image: kaitan8110/converter
          envFrom:
            - configMapRef:
                name: converter-configmap
            - secretRef:
                name: converter-secret
```

Create a `configmap.yaml` file. 
```
vim configmap.yaml
```

Fill in below code. Save and exit.
```
apiVersion: v1
kind: ConfigMap
metadata:
  name: converter-configmap
data:
  MP3_QUEUE: "mp3"
  VIDEO_QUEUE: "video"
```

Next, create a new `mp3` queue in RabbitMQ management console. Visit `https://rabbitmq-manager.com/` in your browser. Login and create the queue. Both username and password are `guest`. 

![](documentation_images/create_mp3_queue.png)
![](documentation_images/both_queue_created.png)

Create a `secret.yaml` file. 
```
vim secret.yaml
```

Fill in below code. Save and exit.
```
apiVersion: v1
kind: Secret
metadata:
  name: converter-secret
stringData:
  PLACEHOLDER: "NONE"
type: Opaque
```

Now, let's apply all the manifest files in current directory.
```
kubectl apply -f ./
```

We can see our converter service is deployed, if you run `k9s` in the terminal. 
![](documentation_images/converter_is_deployed.png)

Now, let's test the end to end functionality of uploading video, and having our video converted to mp3. (Make sure your `minikube tunnel` is still running)

We want to test by uploading a video file. And when we upload that video file, we want to see that the messages gets added to our video queue, and then get remove from our video queue, and another message gets added to our mp3 queue. And we don't have a consuming service to consume the mp3 queue's messages, so the messages should just be piling up at the mp3 queue, if our end-to-end functionality is working as expected. And also if it is working as expected, we should be able to download a converted video file, which would just be a mp3 file from our mongodb. So let's go ahead and test that. 

We will use `curl` to test it. We can now download a video from youtube first. 

Before that lets install `youtube-dl` in our local environment to download youtube videos. 
```
brew install youtube-dl
```

Let's use this youtube video. Copy the link. 
![](documentation_images/example_youtube_video.png)

Run the below command in your terminal. The video will be downloaded to your current directory.
```
youtube-dl "https://youtu.be/jiudBq7z8wk?si=gPbT450hpAb9Hoyh"
```

Let's check the username in our mysql first. Login to mysql with: 
```
mysql -uroot
```

Run the below commands in sql shell. 
```
use auth;
show tables; 
select * from user; 
```

After executing the `select * from user;` command, you should find a user credential here from when we created the database, using our sql script to create the user in the beginning of the project.  You should see an email and password. And these are the credentials that we are going to use in our basic auth when we send a request to our login endpoint to get a json web token to upload the video. 

We will exit the sql with:
```
exit
```

Let's try to login to `mp3converter.com` now. 
```
curl -X POST http://mp3converter.com/login -u <email-credential-from-user-table>:<password-credential-from-user-table>
```

You should then get your jwt token.
![](documentation_images/jwt_token.png)

We can just copy the jwt token, and go back to the directory where our video file is. For me, its at the converter/manifests directory. 

For make it simpler to work with, let's change the file name of the video file to `test.mkv`.
```
mv Mark\ Zuckerberg\ Says\ He\ Is\ Not\ a\ Lizard\ Person\ _\ Inverse-jiudBq7z8wk.mp4 test.mkv
```

Next, run the below command in converter/manifests directory. Replace the jwt token below with your own. 
```
curl -X POST -F 'file=@./test.mkv' -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6ImthaXRhbjgxMTBAZ21haWwuY29tIiwiZXhwIjoxNzA0NzIwNDU0LCJpYXQiOjE3MDQ2MzQwNTQsImFkbWluIjp0cnVlfQ.hcQyuAqHmF8zUlSbwAdVie2UXK2cc2U8HgiH4T9FP3s' http://mp3converter.com/upload
```

You should get a success result like below. 
![](documentation_images/upload_success.png)

In the RabbitMQ dashboard, there should be a message at `video` queue initially. Thereafter, there should be a message in `mp3` queue. (You should have one message only if you execute it one time. I have 5 messages as I have previously ran multiple times)
![](documentation_images/messages_stacking_up_at_mp3_queue.png)

It seems that we have successfully written audio file as well. (Below is `converter` container's logs in K9s)
![](documentation_images/writing_audio_done.png)

Let's now check our mongoDB to see if there is videos or audio files being stored there. 

Run `mongosh`, which should put you directly into mongoDB that is running in our localhost/local machine. 
```
mongosh
```

Next run the below command, which shows you that we have these mp3s and videos databases.
![](documentation_images/mongosh.png)

With gridFS, the actual file data is stored in these chunks. And the files are essentially like the metadata for a collection of chunks. (I have previously uploaded a few videos beforehand, thus here shows more than one result)
![](documentation_images/db_fs_files.png)

Let try to get message of the mp3 queue from the RabbitMQ dashboard. Then, copy the `mp3_fid` value. 
![](documentation_images/get_message_from_mp3.png)

Let's try to run the below command in mongoDB shell. As you can see, the `mp3_fid` is stored successfully, inside of our mp3s database.  
![](documentation_images/fs_files_objectid.png)

So now we want to download the above mp3, to see if it is an audio file. And to do that. we can exit the mongodb shell first. 
```
exit
```

Then run the below command in your local terminal. The command below will save a `test.mp3` audio file in your current directory. 
```
mongofiles --db=mp3s get_id --local=test.mp3 '{"$oid": "659aa8cb6f412c7a4ba67d3f"}'
```

If the output is as below, it means it is successful. And you may test the `test.mp3` in your current directory. 
![](documentation_images/write_audio_file.png)

Looks like our end to end functionality is working, up to the point where we put the message on the mp3 queue. So essentially, when we upload a video, it gets put onto mongoDB, then we create a message and add it to this video queue. And then our consumer converter service is going to pull off of this video queue. Convert the video into an mp3, and then put a new message on this mp3 queue, saying that an mp3 for a specific file ID exists in mongoDB. So the last thing we need to create is a service that is going to consume this mp3 queue. 

And that service is just going to a notification service that is going to tell our user that a video-conversion-to-mp3 process is done. So the service is essentially going to pull the messages off the queue. And it's going to have the ID and the email of the user. And it's going to send an email to the user saying "Hey, this ID is available for download as an mp3". And then from there, there's going to be a download endpoint that we create on our gateway. Where the user can use his or her token to basically request to download a specific mp3, using the file ID that's sent in the notification service email. 

Next, we need to update our gateway service to have a download endpoint.

Change directory to `gateway` directory.

Let's update `server.py` file. 
```
vim server.py
```

Edit the `server.py` file as below. Save and close it. 
```
import os, gridfs, pika, json
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

connection = pika.BlockingConnection(pika.ConnectionParameters("rabbitmq")) # Configure rabbitMQ connection, make communication with our rabbitMQ's queue synchronouns. 
channel = connection.channel()

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

Since we have changed our code, we will need to rebuild our docker image and push it to our repository. Once that is done, we can proceed to create our notification service. 