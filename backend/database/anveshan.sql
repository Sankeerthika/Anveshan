CREATE DATABASE IF NOT EXISTS anveshan;
USE anveshan;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50),
    email VARCHAR(50) UNIQUE,
    password VARCHAR(100),
    role VARCHAR(20)
);

-- Events table
CREATE TABLE IF NOT EXISTS events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100),
    event_date DATE,
    deadline DATE,
    organizer VARCHAR(50)
);
