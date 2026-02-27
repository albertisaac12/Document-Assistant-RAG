# Hosting on Azure App Service (10-Day Setup)

This guide walks you through deploying this Flask document RAG application to **Azure App Service** (Linux). Since this is for a short 10-day period, we will leverage Azure's Free (F1) or Basic (B1) tier, which keeps things incredibly simple and cheap.

## Architecture

* **Web Hosting**: Azure App Service (Linux Environment).
* **Database**: SQLite. The database file will be stored in `/home/document_chatbot.db`. Azure App Service mounts `/home` to a persistent shared SMB drive, so your data will survive app restarts.
* **Document Storage**: Uploaded files (PDFs, TXT) will also be persisted to `/home/uploads`.
* **Vector Store**: Pinecone (managed via API, no hosting needed here).
* **LLM**: Google Gemini (managed via API, no hosting needed here).

---

## ☁️ Setting Up The Azure Environment

### Prerequisites
1. An [Azure Account](https://azure.microsoft.com/en-us/free/).
2. The code must be pushed to a **GitHub Repository** (which you've already done).

### Step 1: Create the Azure Web App

1. Log into the [Azure Portal](https://portal.azure.com/).
2. Click **Create a resource** and search for **Web App**.
3. Fill out the "Basics" tab:
   * **Subscription**: Your Azure subscription.
   * **Resource Group**: Create a new one (e.g., `rag-chatbot-rg`).
   * **Name**: The name of your app (this becomes your `.azurewebsites.net` URL).
   * **Publish**: Choose **Code**.
   * **Runtime stack**: Choose **Python 3.10** or **3.11** (depending on what you're using locally).
   * **Operating System**: **Linux**.
   * **Region**: Choose the region closest to you or closest to your Pinecone index.
   * **Pricing Plan**: Choose **Free F1** or **Basic B1** (B1 allows more compute if you hit errors with HuggingFace models loading).

4. Click **Review + create** and then **Create**. Wait a minute for deployment to complete.

### Step 2: Connect GitHub For Continuous Deployment

1. Go to your newly created Web App in the Azure Portal.
2. In the left sidebar, click on **Deployment Center**.
3. Settings to configure:
    * **Source**: Choose **GitHub**.
    * **Organization / Repository**: Select your `albertisaac12/Document-Assistant-RAG` repo.
    * **Branch**: Select the branch you want to deploy from (e.g., `Hosting-Azure` or `main`).
4. Click **Save**. 

Azure will now automatically configure a GitHub Actions workflow in your repository. Every time you push to this branch, Azure will automatically install the `requirements.txt` and start the app using Gunicorn!

### Step 3: Configure Startup Command (IMPORTANT)

By default, Azure tries to guess how to run your Python app. We need to explicitly tell it to use `gunicorn` to serve the app and allow generous timeouts, because Hugging Face models can take a few seconds to load locally in memory on startup.

1. Go to the left sidebar of your Web App and click **Configuration**.
2. Go to the **General settings** tab.
3. In the **Startup Command** input box, paste the following exactly:
   ```bash
   gunicorn --bind=0.0.0.0 --timeout 600 run:app
   ```
4. Click **Save** at the top.

### Step 4: Configure App Environment Variables

We need to add the same variables you have in your `.env` file into the Azure settings.

1. Still under **Configuration**, go to the **Application settings** tab.
2. Click **+ New application setting**. Add the following:
   * **Name**: `FLASK_ENV` | **Value**: `production`
   * **Name**: `FLASK_SECRET_KEY` | **Value**: *(Generate a strong random password/hash and paste it here)*
   * **Name**: `SCM_DO_BUILD_DURING_DEPLOYMENT` | **Value**: `true` (Tells Azure to run pip install).
   * **Name**: `WEBSITES_CONTAINER_START_TIME_LIMIT` | **Value**: `1800` (Increases the container startup timeout to 30 minutes, giving Hugging Face models enough time to download).

*(Note: You do NOT need to put Pinecone or Gemini API keys here anymore because users enter those securely in the application Settings GUI!)*

3. Click **Save**.

---

## 🛠️ Accessing/Monitoring Your Live App

**1. Access the App**
Go to the **Overview** page of your Web App and click the **Default Domain** link (e.g., `https://your-app-name.azurewebsites.net`). 

**2. Viewing Logs**
During deployment, if you get an "Application Error", it's usually because Azure is still installing pip packages in the background. 
* To see exactly what the server is doing: Go to **Log stream** in the left sidebar to watch the raw container logs.

**3. Database Initialization (Important final step!)**
The first time you boot the Azure app, it will lack the database tables. Luckily, because we integrated Flask-Migrate, it will create it on boot, but you may need to SSH in to create the database yourself using SSH:
* In the left sidebar, click **SSH** under Development Tools, and click `Go ->`.
* Run:
  ```bash
  cd /home/site/wwwroot
  FLASK_APP=run.py python -m flask db upgrade
  ```
This creates the tables mapped locally in the `/home/document_chatbot.db` file.

You're done! The app is now fully hosted on Azure Linux and will persist your database and file uploads as long as the App Service is running.
