# Document Q&A Chatbot - Setup Guide

Welcome to the Document Q&A Chatbot! This project allows you to securely upload documents (PDF, TXT, DOCX), convert them into local vector embeddings using FAISS, and chat with them using Google's powerful Gemini 2.5 Flash API.

## Prerequisites

Before you begin, ensure you have the following installed:
- **Python 3.9+** (Ensure `pip` is also installed)
- **Git** (for version control)

You will also need:
- A Free Google Gemini API Key: [Get yours here](https://aistudio.google.com/app/apikey)
- A Free Google OAuth Client (if using Google Login)

## Installation Instructions

### 1. Clone the Repository
Clone this repository to your local machine and navigate into the directory:
```bash
git clone <your-repo-url>
cd python-project
```

### 2. Set up a Virtual Environment
It is highly recommended to use a virtual environment to manage dependencies.
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install all the required Python packages from the requirements file:
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a file named `.env` in the root directory of the project. Your `.env` file should look like this:

```ini
# Flask Security Key
SECRET_KEY=your_secure_random_string_here

# Google OAuth Credentials (for Login)
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# Database URI (defaults to SQLite if omitted)
# DATABASE_URL=sqlite:///instance/docchat.db
```

### 5. Initialize the Database
Set up the SQLite database and create the required tables:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 6. Run the Application
Start the Flask development server:
```bash
python run.py
```

The application will now be running at `http://127.0.0.1:5000/`.

## Post-Installation

1. **Register an Account:** Go to `http://127.0.0.1:5000/register` and create an account.
2. **Add your API Key:** Once logged in, navigate to **Settings** and input your Gemini API Key.
3. **Upload Documents:** Go to **My Documents** and upload a PDF, DOCX, or TXT file. The system will automatically chunk and vectorize it.
4. **Chat:** Navigate to the **Chat** tab, select your uploaded document, and start asking questions!
