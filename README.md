# OpticorAI Project Management System ✅🧠

A comprehensive, role-based task evaluation and project management system built with Django.

## 🌟 Features

- 🔐 Role-based Access (Admin, Manager, Employee)
- 📋 Task assignment and approval workflows
- 📊 Employee performance evaluation and KPIs
- 📈 Dynamic charts and visual analytics
- 📨 Notifications via Django Signals
- 📤 PDF & Excel report exports
- 🛡️ Two-Factor Authentication (2FA)
- 📦 Modular, scalable codebase

## 🚀 Setup Instructions

```bash
git clone https://github.com/YOUR-USERNAME/OpticorAI_project_management_system.git
cd OpticorAI_project_management_system
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## 🔐 .env File

```env
SECRET_KEY=your-secret-key
DEBUG=False
DJANGO_SETTINGS_MODULE=OpticorAI_project_management_system.settings
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-app-password
DATABASE_URL=your-database-url-from-railway
```

## 📁 Structure

```
├── manage.py
├── Procfile
├── runtime.txt
├── requirements.txt
├── README.md
├── .gitignore
```