# Hosting on Azure App Service (10-Day Setup)

This guide walks you through deploying this Flask document RAG application to **Azure App Service** (Linux). Since this is for a short 10-day period, we will leverage Azure's Free (F1) or Basic (B1) tier, which keeps things incredibly simple and cheap.

## Architecture

* **Web Hosting**: Azure App Service (Linux Environment).
* **Database**: SQLite. The database file will be stored in `/tmp/document_chatbot.db` to prevent SMB file locking issues during the short 10-day evaluation.
* **Document Storage**: Uploaded files (PDFs, TXT) will also be persisted to `/tmp/uploads`.
  > **Note:** Because `/tmp` is wiped when the Azure container resarts, your accounts and chat history will be lost if the server goes down. This setup is specifically optimized for a quick 10-day evaluation.
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
   * **Name**: `WEBSITES_PORT` | **Value**: `8000` (Tells Azure which port Gunicorn is listening on).

*(Note: You do NOT need to put Pinecone or Gemini API keys here anymore because users enter those securely in the application Settings GUI!)*

3. Click **Save**.

### Step 5: Configure Health Checks (Recommended)
1. Go to the **Health checks** tab under the **Monitoring** section in the left sidebar.
2. Click **Enable**.
3. Set the **Path** to `/health` (This is a lightweight endpoint we added to prevent Azure timeouts).
4. Click **Save**.

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
  ```bash
  cd $APP_PATH
  python -c "import os; os.environ['FLASK_APP']='run.py'; from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
  ```
  *(Note: Because Azure builds your app in a temporary `/tmp/...` folder during startup, `$APP_PATH` ensures you are in the correct folder to run the script. The database file itself will still correctly save to the persistent `/home` drive).*

You're done! The app is now fully hosted on Azure Linux and will persist your database and file uploads as long as the App Service is running.

---

## 🔐 Configuring Google OAuth for Production

Right now, your Google login button will probably fail on the live site because Google only recognizes your local `http://localhost:5000` address. You need to tell Google your new Azure URL!

### Step 1: Update Google Cloud Console
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Make sure you have the correct project selected in the top dropdown.
3. In the left sidebar, navigate to **APIs & Services** > **Credentials**.
4. Under the "OAuth 2.0 Client IDs" section, click the pencil icon to edit your existing web client.
5. Under **Authorized JavaScript origins**, click "Add URI" and paste your Azure URL (exactly as it appears):
   * `https://docchatrag-f4cpaubbcfgcazfk.centralindia-01.azurewebsites.net`
6. Under **Authorized redirect URIs**, click "Add URI" and paste your Azure URL **plus the callback path**:
   * `https://docchatrag-f4cpaubbcfgcazfk.centralindia-01.azurewebsites.net/auth/google/callback`
7. Click **Save** at the bottom.

### Step 2: Update Azure App Settings
You must also update the environment variable in Azure so your Flask app knows where to send users back to.
1. Go back to your Web App in the **Azure Portal**.
2. Click **Environment variables** in the left sidebar.
3. Find your `GOOGLE_REDIRECT_URI` setting and edit it.
4. Replace the `localhost` URL with your new live callback URL:
   * `https://docchatrag-f4cpaubbcfgcazfk.centralindia-01.azurewebsites.net/auth/google/callback`
5. Click **Apply** at the bottom, and then **Apply/Save** at the top.

*Note: Changes in the Google Cloud console can sometimes take 5-10 minutes to propagate across their servers. If Google gives you an "URI mismatch" error immediately after saving, just wait a few minutes and try clicking the Sign-in button again!*

---

## 🌐 Binding a Custom Domain

If you own a domain name (like `mychatbot.com`) and want to connect it to your Azure App (`your-app-name.azurewebsites.net`), follow these steps:

**Important Prerequisites:**
* Your App Service plan **cannot** be on the Free (F1) tier. Custom domains require **Basic (B1)** tier or higher. If you are on F1, you must click "Scale up" in the Azure sidebar and upgrade to B1 first.
* You need access to the DNS settings of your domain registrar (GoDaddy, Namecheap, Cloudflare, etc.).

### Step 1: Add the Domain in Azure
1. In your Azure Web App sidebar, click **Custom domains** (under the Settings section).
2. Click **+ Add custom domain**.
3. In the right pane, select **App Service Managed Certificate** (this gives you free SSL).
4. For "TLS/SSL type", select **SNI SSL**.
5. Enter your domain name in the text box (e.g., `www.mychatbot.com` or `mychatbot.com`).

### Step 2: Configure your DNS Records
Azure will then show you **two records** that you must add to your domain registrar to prove you own the domain. Keep this Azure window open!

Open a new tab, log into your domain registrar (GoDaddy, Cloudflare, etc.), go to DNS Management, and add the two records Azure gave you:

**Types of records Azure will ask for:**
1. A **TXT Record** (Used to verify domain ownership):
   * **Host/Name:** `asuid` (or your subdomain like `asuid.www`)
   * **Value/Data:** The long ID string Azure provides.
2. A **CNAME or A Record** (Used to route the traffic):
   * **If using a subdomain (like www.mychatbot.com):** Create a **CNAME** record where the Name is `www` and the Value is `your-app-name.azurewebsites.net`.
   * **If using a root domain (like mychatbot.com):** Create an **A** record where the Name is `@` and the Value is the IP address Azure provides.

### Step 3: Validate and Add
1. Go back to the Azure window.
2. Click the **Validate** button at the bottom.
3. If your DNS records were entered correctly (and have propagated across the internet, which can sometimes take 5-15 minutes), Azure will show green checkmarks.
4. Click **Add**.

Your custom domain is now bound to the app with a free managed SSL certificate!
