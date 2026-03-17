# 🚀 Anveshan  
### Connect • Collaborate • Create

Anveshan is a **campus collaboration platform** designed to bridge the gap between **ideas and the right people**. It connects **students, faculty, and clubs** in a single ecosystem to enable structured collaboration for hackathons, research projects, and innovation activities within a campus.

---

# 📖 Project Overview

In many colleges, students have innovative ideas and want to participate in hackathons or build projects. However, they often struggle to find the **right teammates with the required skills**.  

Similarly, faculty members may have **research ideas** but lack a structured way to find interested students or collaborators.

**Anveshan solves this problem** by providing a centralized platform where students, faculty, and clubs can connect, collaborate, and build meaningful projects together.

---

# ❗ Problem Statement

Collaboration in academic environments is often **unstructured and inefficient**.  

Common issues include:

- Students struggling to find teammates with specific skills
- Hackathon participants missing opportunities due to lack of teams
- Faculty members unable to easily connect with students for research
- Collaboration happening through scattered channels like WhatsApp or informal discussions
- No centralized platform dedicated to **campus innovation and teamwork**

These challenges reduce the potential for **innovation, research participation, and skill development**.

---

# 💡 Solution

**Anveshan** provides a centralized digital platform where:

- Students can **find teammates based on skills**
- Hackathon teams can **request members with specific expertise**
- Students can **post personal project ideas**
- Faculty can **share research topics and collaborate with students**
- Faculty can **connect with other faculty for interdisciplinary research**
- Clubs can **organize hackathons and manage participation**

This structured system transforms **random communication into organized collaboration**.

---

# ✨ Key Features

### 🎯 Skill-Based Team Formation
Students can form teams by requesting members with specific skills like frontend, backend, AI, or design.

### 🏆 Hackathon Team Requests
Clubs can post hackathons, and students can either join existing teams or send skill-based requests.

### 💡 Personal Project Collaboration
Students can post project ideas and find collaborators who share the same interests.

### 👨‍🏫 Faculty Research Collaboration
Faculty members can post research ideas and invite students to participate.

### 🤝 Faculty–Faculty Collaboration
Professors can collaborate with colleagues for interdisciplinary research.

### 📢 Event and Hackathon Management
Clubs can post events, manage participation, and encourage innovation within the campus.

### 🔗 Structured Collaboration System
All collaboration activities happen in a **single organized platform**, reducing confusion and improving efficiency.

---

# 🏗 System Architecture
       +----------------------+
       |      Frontend        |
       | HTML • CSS • JS     |
       +----------+-----------+
                  |
                  |
         HTTP Requests
                  |
                  ▼
       +----------------------+
       |       Backend        |
       |    Python Flask      |
       |  Authentication API  |
       |  Collaboration Logic |
       +----------+-----------+
                  |
                  |
                  ▼
       +----------------------+
       |       Database       |
       |        MySQL         |
       | Users • Projects     |
       | Skills • Hackathons  |
       +----------------------+
     
---

# 🛠 Tech Stack

| Layer | Technology |
|------|-------------|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python Flask |
| Database | MySQL |
| Deployment | Render |
| Version Control | Git & GitHub |

---

# ⚙ Installation & Setup

Follow these steps to run the project locally.

1️⃣ Clone the Repository

```bash
git clone https://github.com/Sankeerthika/Anveshan.git
cd Anveshan  

2️⃣ Create Virtual Environment
python -m venv venv

Activate it:

Windows

venv\Scripts\activate

Mac/Linux

source venv/bin/activate

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Configure Database

Create a MySQL database and update your database credentials in the configuration file.

Example:

DB_HOST=localhost
DB_USER=root
DB_PASSWORD=yourpassword
DB_NAME=anveshan

5️⃣ Run the Application
python app.py

The application will run on:
http://localhost:5000/


## 📷 Screenshots

![Home](https://raw.githubusercontent.com/Sankeerthika/Anveshan/main/backend/screenshorts/homepage.png)

