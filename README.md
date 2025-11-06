# Headache Tracker

Simple web app for tracking and analyzing headaches using AI.

## Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py
```

Open `http://localhost:5514`

### Docker

```bash
# Build
docker build -t headache-tracker .

# Run
docker run -p 5000:5000 \
  -e OPENAI_API_KEY=your_key \
  -e SERVICE_ACCOUNT_JSON='{"type":"service_account"...}' \
  -e DRIVE_FOLDER_ID=your_folder_id \
  headache-tracker
```

Or use docker-compose:
```bash
# Create .env file with your keys
cp .env.example .env
# Edit .env with your values

# Run
docker-compose up -d
```

## Deployment Options

### 1. Render.com (Easiest)
- Connect GitHub repo
- Add environment variables
- Auto-deploy

### 2. Railway.app
- One-click deploy
- Add environment variables
- Done

### 3. Your Own Server (Docker)
- Install Docker
- Clone repo
- Run docker-compose
- Set up reverse proxy (nginx)

### 4. AWS/GCP/Azure
- Use Docker image
- Deploy to container service
- Configure environment variables

## Environment Variables

Required:
- `OPENAI_API_KEY` - Your OpenAI API key
- `SERVICE_ACCOUNT_JSON` - Google service account JSON (as string)
- `DRIVE_FOLDER_ID` - Google Drive folder ID with spreadsheet

Optional:
- `PORT` - Port to run on (default: 5514)

