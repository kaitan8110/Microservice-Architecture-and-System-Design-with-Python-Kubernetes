CREATE USER 'auth_user'@'localhost' IDENTIFIED BY 'ComplexPassword123!';

CREATE DATABASE auth; 

GRANT ALL PRIVILEGES ON auth.* TO 'auth_user'@'localhost';

USE auth;

CREATE TABLE user (
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	email VARCHAR(255) NOT NULL,
	password VARCHAR(255) NOT NULL
);

# You may use your own email and password below.
INSERT INTO user (email, password) VALUES ('kaitan8110@gmail.com', 'Admin123');
