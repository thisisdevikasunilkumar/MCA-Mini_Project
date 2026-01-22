# MCA-Mini_Project - Procezo

**Procezo** is an Employee Monitoring and Productivity Management System designed to automate attendance, track work activities, and evaluate employee engagement through real-time emotion detection and analytics.

---

## 🚀 Features

### 👨‍💼 Admin Module
- **Manage Employees      :** Add, edit, and manage employee profiles.
- **Attendance Monitoring :** Automated attendance logging via face recognition.
- **Emotion Tracking      :** Monitor employee emotions and stress levels during working hours.
- **Activity Reports      :** Analyze productivity through keyboard and screen activity monitoring.
- **Centralized Dashboard :** View consolidated insights of performance, attendance, and engagement metrics.

### 👩‍💻 Staff Module
- **Login/Logout        :** Attendance recorded using facial recognition.
- **Emotion Detection   :** Real-time emotion analysis during active work sessions.
- **Profile Management  :** Employees can update personal information.
- **Performance Reports :** View personal productivity summaries and attendance logs.

---

## 🎨 UI / UX Design (Figma)

The complete UI/UX design of **Procezo** was created using **Figma**.

🔗 **Figma Design Link:**  
https://www.figma.com/design/nObz93WhgZg4kcEYnxP071/Procezo?node-id=0-1&t=mtfQqJm4dXSvoPl3-1

> This design includes dashboard layouts, admin panels, staff views, and overall application flow.

---

## 🧰 Technologies Used

| Component              | Technology                                                       |
|------------------------|------------------------------------------------------------------|
| **Front-End**          | HTML, CSS, JavaScript                                            |
| **Back-End**           | Python (Django Framework)                                        |
| **Database**           | MySQL                                                            |
| **AI Module**          | Convolutional Neural Network (CNN) for Face & Emotion Detection  |
| **Tools**              | VS Code                                                          |
| **Operating System**   | Windows 7 or above                                               |
| **Supported Browsers** | Microsoft Edge, Chrome, Firefox, Internet Explorer               |

---

## ⚙️ Installation & Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/thisisdevikasunilkumar/MCA---Mini_Project.git

2. **Install Required Packages**
   ```bash
    python -m pip install -r requirements.txt

3. **Set Up the Database**
   - Import the provided `.sql` file into **MySQL**.

4. **Configure Django**
   - Open `settings.py` and update the database configuration:
     
   ```bash
   DATABASES = {
     'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'your_database_name',
        'USER': 'your_username',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
     }
   }

5. **Create Database Before Migration**
   ```bash
     CREATE DATABASE database_name;
   
6. **Run Migrations**
   ```bash
     python manage.py makemigrations
     python manage.py migrate

7. **Start the Server**
   ```bash
    python manage.py runserver

8. **Access the Application**
   - Open your browser and visit:
     
   ```bash
     http://127.0.0.1:8000/
   
---   

## 👥 Team Members
- [Devika Sunilkumar](https://github.com/thisisdevikasunilkumar)
- [Diya V P](https://github.com/diyaprince)
- [Hitha Krishna P R](https://github.com/HithaKrishna)
- [Tina Paul C](https://github.com/tinachirammal2002)

---

### 📌 Note
This project was developed as part of the **MCA 3rd Semester Mini Project** and is intended purely for learning and academic purposes.

### 📚 Academic Information

- **Course**: Master of Computer Applications (MCA)  
- **Semester**: 3rd Semester   
- **Institution**: *CCSIT Dr. John Matthai Centre Aranattukara, Thrissur* 
