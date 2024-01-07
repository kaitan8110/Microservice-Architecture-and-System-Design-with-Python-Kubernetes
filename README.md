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

### Auth Service

Create a directory for auth and cd into it.  
```
mkdir auth
cd auth
```

Create a virtual env within auth. 
```
python3 -m venv venv
```

Activate virtual env. 
```
source ./venv/bin/activate
```

All of the codes for this service will be created in server.py. Create server.py. 
```
vim server.py
```

Write the following lines of code in server.py. 
```
import jwt, datetime, os
from flask import Flask, request
from flask_mysqldb import MySQL
```

Install the above needed packages in current virtual env. 
```
pip install pyjwt flask flask_mysqldb 
```

Add the following lines of code in server.py. 
```
import jwt, datetime, os
from flask import Flask, request
from flask_mysqldb import MySQL

server = Flask(__name__)
# So that our application can connect to our MySQL datebase. And able to query the database. 
mysql = MySQL(server)

# Configuration for our server, or for our application
# Variables that we used to connect to our mysql database
server.config["MYSQL_HOST"] = os.environ.get("MYSQL_HOST")
server.config["MYSQL_USER"] = os.environ.get("MYSQL_USER")
server.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD")
server.config["MYSQL_DB"] = os.environ.get("MYSQL_DB")
server.config["MYSQL_PORT"] = int(os.environ.get("MYSQL_PORT"))

@server.route("/login", methods=["POST"])
def login():
	auth = request.authorization
	if not auth:
		return "missing credentials", 401

	# check db for username and password
```
Save and exit vim. 


Next, create a user for our auth service, and give that user a username and password. Then create a MySQL database `auth`. It will be the database of our auth service. Grant the user the privileges to the database, and create a table within that database, named `user`.  The user table is going to be what we use to store users that we want to give access to our api.  

Create a file named `init.sql`.

```
vim init.sql
```

Add below content to `init.sql`. 
```
CREATE USER 'auth_user'@'localhost' IDENTIFIED BY 'ComplexPassword123!';

CREATE DATABASE auth; 

GRANT ALL PRIVILEGES ON auth.* TO 'auth_user'@'localhost';

USE auth;

CREATE TABLE user (
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	email VARCHAR(255) NOT NULL UNIQUE,
	password VARCHAR(255) NOT NULL
);

# You may use your own email and password below.
INSERT INTO user (email, password) VALUES ('kaitan8110@gmail.com', 'Admin123');
```
Save and exit vim. 

Go into our database. 
```
mysql -uroot
```

Show databases. 
```
show databases; 
```
You can see that we don't have the `auth` database yet. 

We can exit MySQL first. 
```
exit
```

Run the `init.sql` within MySQL. 
```
mysql -uroot < init.sql
```

You may run the below command to check that *auth* database and *user* table have been created. 
```
mysql -uroot
show databases;
use auth;
show tables;
describe user;
select * from user;
```

Continue writing code for `server.py`. 

```
import jwt, datetime, os
from flask import Flask, request
from flask_mysqldb import MySQL

server = Flask(__name__)
# So that our application can connect to our MySQL datebase. And able to query the database. 
mysql = MySQL(server)

# Configuration for our server, or for our application
# Variables that we used to connect to our mysql database
server.config["MYSQL_HOST"] = os.environ.get("MYSQL_HOST")
server.config["MYSQL_USER"] = os.environ.get("MYSQL_USER")
server.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD")
server.config["MYSQL_DB"] = os.environ.get("MYSQL_DB")
server.config["MYSQL_PORT"] = int(os.environ.get("MYSQL_PORT"))

@server.route("/login", methods=["POST"])
def login():
	auth = request.authorization
	if not auth:
		return "missing credentials", 401

	# check db for username and password
	cur = mysql.connection.cursor()
	res = cur.execute(
		"SELECT email, password FROM user WHERE email=%s", (auth.username,)
	)

	if res > 0:
		user_row = cur.fetchone()
		email = user_row[0]
		password = user_row[1]

		if auth.username != email or auth.password != password:
			return "invalid credentials", 401
		else:
			return createJWT(auth.username, os.environ.get("JWT_SECRET"), True)
	else:
		return "invalid credentials", 401
```

Next we will create the `createJWT` function. Add the below code to `server.py`. 
```
def createJWT(username, secret, authz):
	return jwt.encode(
		{
			"username": username, 
			"exp": datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(days=1),
			"iat": datetime.datetime.utcnow(),
			"admin": authz,
		},
		secret,
		algorithm="HS256",
	)
```

Add below code to `server.py` as well. 
```
if __name__ == "__main__":
	# To allow our application to listen to any ip address on our host. 
	# This tells your operating system to listen on all public IPs. 
	server.run(host="0.0.0.0", port=5000)
```

Next, we will actually want to create another route to validate JWT. And this route is going to be used by our api gateway to validate JWT sent within request from the client to both upload videos and download MP3 version of those videos. 

Add below lines to `server.py`.
```
@server.route("/validate", method=["POST"])
def validate():
	encoded_jwt = request.headers["Authorization"]

	if not encoded_jwt:
		return "missing credentials", 401
	
	encoded_jwt = encoded_jwt.split(" ")[1]

	try:
		decoded = jwt.decode(
			encoded_jwt,
			os.environ.get("JWT_SECRET"),
			algorithm=["HS256"]
		)
	except:
		return "not authorized", 403
	
	return decoded, 200
```

Next, we are going to write all the infrastructure code for the deployment. We are basically going to deploy all of our services within a kubernetes cluster. We need to create docker images that we need to push to a repository, and our kubernetes configuration is going to pull it from the repository, and create our deployments within our cluster. 

Let's create our `requirements.txt` first. 
```
pip3 freeze > requirements.txt
```

We will start by creating a docker file. 
```
vim Dockerfile
```

Fill in the below lines. 
```
FROM python:3.10-slim-bullseye

RUN apt-get update \
    && apt-get install -y --no-install-recommends --no-install-suggests \
    build-essential default-libmysqlclient-dev \
    && pip install --no-cache-dir --upgrade pip

WORKDIR /app
COPY ./requirements.txt /app
RUN pip install --no-cache-dir --requirement /app/requirements.txt
COPY . /app

EXPOSE 5000

CMD ["python3", "server.py"]
```
Save and exit vim. 

Build the above docker file. 
```
docker build .
```

Next, login to docker hub and create an `auth` repository. For *Repository Name*, key in *auth*. Then click on **create**. 
![create auth repository](documentation_images/create_auth_repository.png)

Next we want to tag the image we just built. 
```
docker tag <copy-and-paste-the-sha256-here-after-you-built-the-image> <your-docker-username>/auth:latest
```

You can also run the below command to see your latest tagged image. 
```
docker image ls
```

![auth docker tag](documentation_images/auth_docker_tag.png)

Next, we can push it to our repository. 
```
docker push <your-docker-username>/auth:latest
```

Once that is finished, you can go to your **auth** repository and refresh the page. You should see your image tag here. That means we successfully push this image to our repository. 
![image pushed to auth repository](documentation_images/image_pushed_to_auth_repository.png)

Next, make a directory named `manifests`. This directory is going to contain all of the `auth` service's kubernetes configuration. 
```
mkdir manifests
```

Change directory to manifests. 
```
cd manifests
```

Create an `auth-deploy.yaml` file with the below content.
```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth
  labels:
    app: auth
spec:
  replicas: 2
  selector:
    matchLabels:
      app: auth
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 3
  template:
    metadata:
      labels:
        app: auth
    spec:
      containers:
        - name: auth
          image: kaitan8110/auth
          ports:
            - containerPort: 5000
          envFrom:
            - configMapRef:
                name: auth-configmap
            - secretRef:
                name: auth-secret
```

Create a `configmap.yaml` file with the below content.
```
apiVersion: v1
kind: ConfigMap
metadata:
  name: auth-configmap
data:
  MYSQL_HOST: host.minikube.internal
  MYSQL_USER: auth_user
  MYSQL_DB: auth
  MYSQL_PORT: "3306"
```

Create a `secret.yaml` file with the below content. (Usually, we don't push this file to the remote github repository as it contains application's sensitive information. Especially in a production environment.)
```
apiVersion: v1
kind: Secret
metadata:
  name: auth-secret
stringData:
  MYSQL_PASSWORD: ComplexPassword123!
  JWT_SECRET: sarcasm
type: Opaque
```

Create a `service.yaml` file with the below content.
```
apiVersion: v1
kind: Service
metadata:
  name: auth
spec:
  selector:
    app: auth
  type: ClusterIP
  ports:
    - port: 5000
      targetPort: 5000
      protocol: TCP
```

Now that we have all our infrastructure code for our kubernetes deployment, we can actually start to deploy this `auth` service to our cluster. 

Start Docker Desktop. Then start minikube. 
```
minikube start
```

Enter into K9s. 
```
K9s
```

Change the namespace to **all** by hitting `0`. 
![K9s_1](documentation_images/k9s_1.png)

We can see our minikube pods running within the kube-system namespace. 
![K9s_2](documentation_images/k9s_2.png)

Hit `Ctrl + C` to quit K9s interactive window. 

Fyi, all of the files within this manifests directory, when applied will interface with the kubernetes API. So these files are going to interface with that API, to create our service and its corresponding resources. 

Change to the `manifests` directory. Run the below to apply all the files in the current directory. (`-f` is a flag for files) 
```
kubectl apply -f ./
```

We can see the following kubernetes resources have been created. 
![K9s resources created](documentation_images/k9s_resources_created.png)

Both instances of our auth service are running now. 
![Auth both instances running](documentation_images/auth_both_instances_running.png)

Now, we can start to write the code for our gateway service. 

### Gateway Service

Cd into the root project directory. Then create a gateway directory. Next, initialise and activate a python environment. 
```
cd ../../
mkdir gateway
cd gateway
python -m venv venv
source ./venv/bin/activate
```

Create a `server.py` file, fill in below content and save. 
```
import os, gridfs, pika, json
from flask import Flask, request
from flask_pymongo import PyMongo
from auth import validate
from auth_svc import access
from storage import util

server = Flask(__name__)
server.config["MONGO_URI"] = "mongodb://host.minikube.internal:27017/videos"

mongo = PyMongo(server)
```

Next we will install all the dependencies. 
```
pip3 install pika flask pyMongo Flask-PyMongo
```

Continue writing code for `server.py`.  Save and exit. 
```
import os, gridfs, pika, json
from flask import Flask, request
from flask_pymongo import PyMongo
from auth import validate
from auth_svc import access
from storage import util

server = Flask(__name__)
server.config["MONGO_URI"] = "mongodb://host.minikube.internal:27017/videos"

mongo = PyMongo(server)

fs = gridfs.GridFS(mongo.db)

connection = pika.BlockingConnection(pika.ConnectionParameters("rabbitmq")) # Configure rabbitMQ connection, make communication with our rabbitMQ's queue synchronouns. 
channel = connection.channel()

@server.route("/login", methods=["POST"])
def login():
    token, err = access.login(request)
```

Create a directory named `auth_svc`. The `__init__.py` below essential marked the `auth_svc` directory as a package. 

```
mkdir auth_svc
cd auth_svc
touch __init__.py
```

Create an `access.py` file.  `access.py` is essentially a module that contains our login function. 
```
vim access.py 
```

Fill in the below content. Save and exit. 
```
import os, requests

def login(request):
    auth = request.authorization
    if not auth:
        return None, ("missing credentials", 401)
    
    basicAuth = (auth.username, auth.password)

    response = requests.post(
        f"http://{os.environ.get('AUTH_SVC_ADDRESS')}/login",
        auth=basicAuth
    )

    if response.status_code == 200:
        return response.text, None
    else:
        return None, (response.text, response.status_code)
```

Next, we will need to install `requests`. 
```
pip3 install requests
```

Continue filling code for `server.py`. 
```
import os, gridfs, pika, json
from flask import Flask, request
from flask_pymongo import PyMongo
from auth import validate
from auth_svc import access
from storage import util

server = Flask(__name__)
server.config["MONGO_URI"] = "mongodb://host.minikube.internal:27017/videos"

mongo = PyMongo(server)

fs = gridfs.GridFS(mongo.db)

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
```

Next, create a `validate` module. 
```
mkdir auth
cd auth
touch __init__.py
vim validate.py
```

Fill in below content for `validate.py`. Save and exit. 
```
import os, requests

def token(request):
    if not "Authorization" in request.headers:
        return None, ("missing credentials", 401)
    
    token = request.headers["Authorization"]

    if not token:
        return None, ("missing credentials", 401)
    
    response = request.post(
        f"http://{os.environ.get('AUTH_SVC_ADDRESS')}/validate",
        headers={"Authorization": token},
    )

    if response.status_code == 200:
        return response.text, None
    else:
        return None, (response.text, response.status_code)
```

Continue writing code for `server.py`. It should look like this now. 
```
import os, gridfs, pika, json
from flask import Flask, request
from flask_pymongo import PyMongo
from auth import validate
from auth_svc import access
from storage import util

server = Flask(__name__)
server.config["MONGO_URI"] = "mongodb://host.minikube.internal:27017/videos"

mongo = PyMongo(server)

fs = gridfs.GridFS(mongo.db)

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

    access = json.loads(access)

    if access["admin"]:
        if len(request.files) > 1 or len(request.files) < 1:
            return "exactly 1 file required", 400

        for _, f in request.files.items():
            err = util.upload(f, fs, channel, access)
        
            if err:
                return err
        
        return "success!", 200
    else: 
        return "not authorized", 401

@server.route("/download", methods=["GET"])
def download():
    pass
        
if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8080)
```

Next, we need to create a `storage` package, and within that package, create a `util` module. 

Cd to the `gateway` directory and run the below commands. 
```
mkdir storage
cd storage
touch __init__.py
vim util.py
```

Fill in below code for `util.py`. Save and exit. 
```
import pika, json

def upload(f, fs, channel, access):
    try:
        fid = fs.put(f)
    except Exception as err:
        return "internal server error", 500
    
    message = {
        "video_fid": str(fid),
        "mp3_fid": None,
        "username": access["username"],        
    }

    try: 
        channel.basic_publish(
            exchange="",
            routing_key="video",
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            ),
        )
    except:
        fs.delete(fid)
        return "internal server error", 500
```

Change to gateway root directory. Next, we can start creating the deployment for the gateway service. 
```
cd ..
```

We will freeze our dependencies into a `requirements.txt` file first.
```
pip3 freeze > requirements.txt
```

Create our Dockerfile. 
```
vim Dockerfile
```

Fill in below code. Save and exit. 
```
FROM python:3.10-slim-bullseye

RUN apt-get update \
    && apt-get install -y --no-install-recommends --no-install-suggests \
    build-essential \
    && pip install --no-cache-dir --upgrade pip

WORKDIR /app
COPY ./requirements.txt /app
RUN pip install --no-cache-dir --requirement /app/requirements.txt
COPY . /app

EXPOSE 8080

CMD ["python3", "server.py"]
```

Let's build our image. 
```
docker build .
```

Tag your image.
```
docker tag <fill-in-your-sha256> <your-docker-username>/gateway:latest
```

Push your image. 
```
docker push <your-docker-username>/gateway:latest
```

It automatically create a remote gateway repository for us. 
![Two repository](documentation_images/two_repository.png)

Next, we will create our kubernetes infrastructure deployment files. 

Create a `manifests` directory at the `gateway` directory level. And change directory to it. 
```
mkdir manifests
cd manifests
```

Create a `gateway-deploy.yaml`.
```
vim gateway-deploy.yaml
```

Fill in below code. Save and exit. 
```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway
  labels:
    app: gateway
spec:
  replicas: 2
  selector:
    matchLabels:
      app: gateway
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 3
  template:
    metadata:
      labels:
        app: gateway
    spec:
      containers:
        - name: gateway
          image: kaitan8110/gateway
          envFrom:
            - configMapRef:
                name: gateway-configmap
            - secretRef:
                name: gateway-secret
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
  name: gateway-configmap
data: 
  AUTH_SVC_ADDRESS: "auth:5000"
```

Create a `secret.yaml` file. 
```
vim secret.yaml
```

Fill in below code. Save and exit. 
```
apiVersion: v1
kind: Secret
metadata:
  name: gateway-secret
stringData:
  PLACEHOLDER: nothing
type: Opaque
```

Create a `service.yaml` file. 
```
vim service.yaml
```

Fill in below code. Save and exit. 
```
apiVersion: v1
kind: Service
metadata:
  name: gateway
spec:
  selector:
    app: gateway
  type: ClusterIP
  ports: 
    - port: 8080
      targetPort: 8080
      protocol: TCP
```

Create a `ingress.yaml` file. (To allow traffic to access our gateway endpoint)
```
vim ingress.yaml
```

Fill in below code. Save and exit. 
```
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: gateway-ingress
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "0"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
    nginx.ingress.kubernetes.io/proxy-sent-timeout: "600"
spec:
  rules:
    - host: mp3converter.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: gateway
                port:
                  number: 8080
```

To make sure that `mp3converter.com` get routed to localhost, we need to edit a `hosts` file in your local setup. 
```
sudo vim /etc/hosts
```

Add a new line below to `hosts` file. 
```
127.0.0.1 mp3converter.com
```
![Hosts file](documentation_images/edit_hosts_file.png)
Save and exit. 

We will now need to configure a minikube add-on to allow ingress. Run below command in your local environment to list the addons that minikube have. 
```
minikube addons list
```

Next, run below command to enable `ingress` addon. 
```
minikube addons enable ingress
```

Below shows `ingress` addon is enabled.
![Minikube enable ingress addons](documentation_images/minikube_enable_ingress_addon.png)

Basically, whenever we want to test this microservice architecture, we will need to run the `minikube tunnel` command. And when this is running, whenever we send request to our loopback address, it is going to go to our minikube cluster via the ingress. And since we map `mp3converter.com` to our loopback address, if we send request to `mp3converter.com`, they are going to go to this minikube tunnel. 
```
minikube tunnel
```

Next, we will try to create the gateway manifest files. Change directory to the gateway manifest directory.
```
kubectl apply -f ./
```

All the resources should be created now. 

But you should encounter an error in the gateway's pods as the `rabbitmq` service is still not deployed yet.
![Gateway error. RabbitMQ not deployed yet. ](documentation_images/gateway_pod_error_rabbitmq.png)

So let's just scale our deployment pods down now first, until `rabbitmq` is deployed.
```
kubectl scale deployment --replicas=0 gateway
```

From here we can start to get into the `rabbitmq` stuff. 

### Setup RabbitMQ Service

Change directory back to project root directory. 

Next, create a `rabbitMQ` directory. We shall named it `rabbit`. Then change directory into it.
```
mkdir rabbit
cd rabbit
```

For `rabbitMQ`, instead of making a deployment like the first two services, we are going to make a stateful set. As we need our queue to remain intact; even if the pods crashes. We want our queue and messages to stay persistent, until the messages are pull from the queue. 

Create a `manifests` directory, and change directory to it. 
```
mkdir manifests
cd manifests
```

Create a `statefulset.yaml` file. 
```
vim statefulset.yaml
```

Fill in below code. Save and exit. 
```
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: rabbitmq
spec:
  serviceName: "not-applicable"
  selector:
    matchLabels:
      app: rabbitmq
  template:
    metadata:
      labels:
        app: rabbitmq
    spec:
      containers:
        - name: rabbitmq
          image: rabbitmq:3-management
          ports:
            - name: http
              protocol: TCP
              containerPort: 15672
            - name: amqp
              protocol: TCP
              containerPort: 5672
          envFrom:
            - configMapRef:
                name: rabbitmq-configmap
            - secretRef:
                name: rabbitmq-secret
          volumeMounts:
            - mountPath: "/var/lib/rabbitmq"
              name: rabbitmq-volume
      volumes:
        - name: rabbitmq-volume
          persistentVolumeClaim:
            claimName: rabbitmq-pvc
```

Create a `pvc.yaml` file.
```
vim pvc.yaml
```

Fill in below code. Save and exit. 
```
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: rabbitmq-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: standard
```

Create a `service.yaml` file.
```
vim service.yaml
```

Fill in below code. Save and exit. 
```
apiVersion: v1
kind: Service
metadata:
  name: rabbitmq
spec:
  type: ClusterIP
  selector:
    app: rabbitmq
  ports:
    - name: http
      protocol: TCP
      port: 15672
      targetPort: 15672
    - name: amqp
      protocol: TCP
      port: 5672
      targetPort: 5672
```

As we are going to access the management interface of rabbitMQ from a web browser outside of the cluster at port 15672, we will need to create an ingress to allow access to it.

Create a `ingress.yaml` file.
```
vim ingress.yaml
```

Fill in below code. Save and exit. 
```
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rabbitmq-ingress
spec:
  rules:
    - host: rabbitmq-manager.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: rabbitmq
                port:
                  number: 15672
```

Edit hosts file.
```
sudo vim /etc/hosts
```

Add a new line as below. Save and exit. 
```
127.0.0.1 rabbitmq-manager.com
```
![Add Rabbitmq to hosts file. ](documentation_images/add_rabbitmq_to_hostsfile.png)

Next, create a `configmap.yaml`. We currently do not need a `configmap` but just in case we need it in future, we will create a template placeholder first. 
```
vim configmap.yaml
```

Fill in below code. Save and exit. 
```
apiVersion: v1
kind: ConfigMap
metadata:
  name: rabbitmq-configmap
data:
  PLACEHOLDER: "NONE"
```

We will do the same thing for `secret.yaml`. Create it with:
```
vim secret.yaml
```

Fill in below code. Save and exit. 
```
apiVersion: v1
kind: Secret
metadata:
  name: rabbitmq-secret
stringData:
  PLACEHOLDER: "NONE"
type: Opaque
```

Lets try to apply our manifest files with: 
```
kubectl apply -f ./ 
```

The resources should be created now. Run the below command to check if `rabbitMQ` pod is up.
```
K9s
```

RabbitMQ pod is running as shown below. 
![rabbitMQ pod is running. ](documentation_images/rabbitmq_pod_running.png)

Let's try to access `rabbitmq-manager.com` in our browser. (Remember to run the `minikube tunnel` command in a separate terminal, and keep it running)

![rabbitMQ management console. ](documentation_images/rabbitmq_management_console.png)

For first-time login, both username and password are `guest`.

It should look something like that after login.
![rabbitmq_dashboard_after_login. ](documentation_images/rabbitmq_dashboard_after_login.png)

Let's add a `video` queue by going through the below steps. Then click on `Add queue`.
![add_video_queue. ](documentation_images/add_video_queue.png)

Now we have our video queue here.
![](documentation_images/video_queue.png)

Now, let's see whether we can start up our gateway server.

Change directory to gateway manifests directory first.

Then run:
```
kubectl apply -f ./
```

We can see our gateway pods are up now.
![](documentation_images/gateway_pod_is_up.png)

Change directory to project root directory. We will then need to create a `converter` service.

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

Looks like our end to end functionality is working, up to the point where we put the message on the mp3 queue. So at this point, we are uploading our video, and adding the message to a video queue. So essentially, when we upload a video, it gets put onto mongoDB, then we create a message and add it to this video queue. And then our consumer converter service is going to pull off of this video queue. Convert the video into an mp3, and then put a new message on this mp3 queue, saying that an mp3 for a specific file ID exists in mongoDB. So the last thing we need to create is a service that is going to consume this mp3 queue. And that service is just going to a notification service that is going to tell our user that a video is done, or a video conversion to mp3 process is done. So the service is essentially going to pull the messages off the queue. And it's going to have the ID and the email of the user. And it's going to send an email to the user saying "Hey, this ID is available for download as an mp3". And then from there, there's going to be a download endpoint that we create on our gateway. Where the user can use his or her token to basically request to download a specific mp3, using the file ID that's sent in the notification service email. 