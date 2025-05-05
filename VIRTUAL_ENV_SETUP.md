# Virtual Environment Setup for TechSaaS

This document provides instructions for setting up a virtual environment to test the full stack TechSaaS application, including the Incident Response Dashboard.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

## Setup Instructions

1. **Create a virtual environment**:

```bash
# Navigate to the TechSaaS directory
cd /home/fiftytwo/Desktop/52\ codes/52TechSaas

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

2. **Install dependencies**:

```bash
# Install required packages
pip install flask flask-cors pytest pytest-flask python-dotenv

# Install additional dependencies
pip install langchain requests pyjwt bcrypt
```

3. **Configure environment variables**:

```bash
# Create a .env file if it doesn't exist
touch .env

# Add necessary environment variables
echo "SECURITY_STORAGE_PATH=./data/security" >> .env
echo "FLASK_APP=ai-service/app.py" >> .env
echo "FLASK_ENV=development" >> .env
```

4. **Create necessary directories**:

```bash
mkdir -p data/security
```

## Running the Application

1. **Start the Flask server**:

```bash
# Make sure the virtual environment is activated
source venv/bin/activate

# Run the Flask application
flask run --host=0.0.0.0 --port=5000
```

2. **Access the Incident Dashboard**:

Open your browser and navigate to:
```
http://localhost:5000/api/v1/security/dashboard
```

## Running Tests

```bash
# Run the simplified core test
python ai-service/test_incident_core.py

# Run pytest for all tests (when fully implemented)
pytest
```

## Deactivating the Virtual Environment

When you're done working on the project, you can deactivate the virtual environment:

```bash
deactivate
```

## Troubleshooting

- **ModuleNotFoundError**: Make sure your virtual environment is activated and all dependencies are installed
- **Permission Issues**: Ensure you have write permissions to the directories where data will be stored
- **Port Already in Use**: Change the port in the flask run command if port 5000 is already in use
