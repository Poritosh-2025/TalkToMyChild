# TalkToMyChild

A backend-focused Django REST API project designed to provide a structured foundation for building scalable web applications with authentication, asynchronous task processing, caching, API documentation, and containerized development.

## 🚀 Overview

**TalkToMyChild** is a Django-based backend application built with a modular architecture.

The project focuses on:

* RESTful API development
* Authentication and authorization
* Background task processing
* Redis-based caching/message brokering
* PostgreSQL database integration
* API schema and documentation
* Docker-based development
* Code quality and formatting automation

The project is structured to make backend features easier to develop, maintain, and extend.

---

## ✨ Key Features

### 🔐 Authentication

* JWT-based authentication
* API-oriented authentication flow
* Token-based access control

### 🌐 REST API

* Django REST Framework
* Modular API structure
* Serializer-based request/response handling
* API schema generation with `drf-spectacular`

### ⚡ Asynchronous Processing

* Celery for background task execution
* Redis as the Celery broker/backend component
* Django Celery Beat for scheduled tasks

### 🗄️ Database

* PostgreSQL support
* Django ORM
* Environment-based database configuration

### 🚀 Caching

* Redis integration
* Django Redis support for application-level caching

### 🐳 Containerization

* Docker support
* Docker Compose configuration
* Separate application configuration for containerized development

### 📚 API Documentation

The project uses **drf-spectacular** for generating an OpenAPI schema and API documentation.

### 🧹 Code Quality

Development tooling includes:

* Black
* isort
* Flake8
* autopep8
* pre-commit

---

## 🛠️ Technology Stack

| Category               | Technology                |
| ---------------------- | ------------------------- |
| Language               | Python                    |
| Framework              | Django                    |
| API                    | Django REST Framework     |
| Authentication         | JWT / PyJWT               |
| Database               | PostgreSQL                |
| Task Queue             | Celery                    |
| Message Broker / Cache | Redis                     |
| Scheduled Tasks        | Django Celery Beat        |
| API Documentation      | drf-spectacular / OpenAPI |
| Web Server             | Gunicorn                  |
| Containerization       | Docker / Docker Compose   |
| Cloud SDK              | Boto3                     |
| Code Formatting        | Black / autopep8          |
| Import Sorting         | isort                     |
| Linting                | Flake8                    |
| Git Hooks              | pre-commit                |

---

## 📁 Project Structure

```text
TalkToMyChild/
│
├── apps/
│   └── Application-specific Django apps
│
├── common/
│   └── Shared/common backend components
│
├── config/
│   └── Project configuration and settings
│
├── manage.py
│
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── run.sh
│
├── requirements.txt
├── pyproject.toml
├── .pre-commit-config.yaml
├── .flake8
├── .dockerignore
├── .gitignore
│
└── README.md
```

---

## ⚙️ Requirements

Before running the project locally, make sure you have:

* Python 3.x
* PostgreSQL
* Redis
* Git

For the containerized setup:

* Docker
* Docker Compose

---

## 🔧 Installation

### 1. Clone the repository

```bash
git clone https://github.com/Poritosh-2025/TalkToMyChild.git
cd TalkToMyChild
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Linux/macOS:

```bash
source venv/bin/activate
```

Windows:

```powershell
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Configuration

Create the required environment configuration according to the project's settings.

Typical configuration may include:

```env
DEBUG=True

SECRET_KEY=your-secret-key

DATABASE_URL=your-database-url

REDIS_URL=redis://localhost:6379/0
```

> Do not commit real credentials, API keys, passwords, or secret keys to Git.

---

## 🗄️ Database Setup

Run Django migrations:

```bash
python manage.py migrate
```

Create an admin user:

```bash
python manage.py createsuperuser
```

---

## ▶️ Running the Project

Start the Django development server:

```bash
python manage.py runserver
```

The API will be available at:

```text
http://127.0.0.1:8000/
```

---

## ⚡ Running Celery

Start a Celery worker:

```bash
celery -A config worker --loglevel=info
```

If scheduled tasks are configured, Celery Beat can be started with:

```bash
celery -A config beat --loglevel=info
```

> The exact Celery application path may depend on the project's configuration.

---

## 🐳 Docker

The project includes Docker and Docker Compose configuration for containerized development.

Build and start the services:

```bash
docker compose up --build
```

Run in detached mode:

```bash
docker compose up -d --build
```

Stop the services:

```bash
docker compose down
```

---

## 📖 API Documentation

The project uses `drf-spectacular` to provide OpenAPI-based API schema generation.

After starting the application, the configured API documentation endpoints can be accessed according to the project's URL configuration.

---

## 🧪 Development & Code Quality

The project includes several tools to maintain consistent code quality.

### Format code

```bash
black .
```

### Sort imports

```bash
isort .
```

### Lint code

```bash
flake8 .
```

### Pre-commit

Install the Git hooks:

```bash
pre-commit install
```

Run all configured hooks:

```bash
pre-commit run --all-files
```

---

## 🏗️ Architecture

The backend follows a modular Django architecture where application-specific functionality is separated into Django apps while shared functionality is organized under common components.

The project is designed around:

```text
Client
   │
   ▼
Django REST API
   │
   ├── Authentication
   │
   ├── Business Logic
   │
   ├── PostgreSQL
   │
   ├── Redis
   │
   └── Celery
          │
          └── Background Tasks
```

This architecture allows long-running or asynchronous operations to be handled outside the main HTTP request-response cycle.

---

## 🔒 Security Considerations

The project uses several backend security-related practices and components, including:

* JWT-based authentication
* Environment-based secret configuration
* Django's built-in security mechanisms
* Token-based API access
* Separation of configuration from source code

Production deployments should additionally configure appropriate:

* HTTPS
* Secret management
* Database security
* CORS/CSRF policies
* Allowed hosts
* Secure cookies
* Logging and monitoring

---

## 📌 Project Status

This project is under active development.

The repository is primarily focused on backend architecture, API development, asynchronous processing, database integration, and maintainable Django application structure.

---

## 👨‍💻 Developer

**Poritosh Pal**

Backend Developer | Python | Django | REST API

GitHub:
https://github.com/Poritosh-2025

---

## 📄 License

License information will be added when the project license is defined.
