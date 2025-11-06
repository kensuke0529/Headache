# Docker Deployment Plan

## Current Status
✅ Flask app with clean UI
✅ Auto-loads data
✅ Docker-ready

## Next Steps

### Step 1: Test Docker Locally
```bash
# Build image
docker build -t headache-tracker .

# Test run
docker run -p 5000:5000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e SERVICE_ACCOUNT_JSON="$(cat ~/Desktop/mcp-00001-f19ba2d2e173.json)" \
  -e DRIVE_FOLDER_ID=$DRIVE_FOLDER_ID \
  headache-tracker
```

Open `http://localhost:5000` to test.

### Step 2: Choose Deployment Platform

#### Option A: Render.com (Recommended)
**Why:** Free tier, easy setup, auto-deploys
**Steps:**
1. Push to GitHub
2. Connect repo on Render
3. Select "Docker" as environment
4. Add env variables
5. Deploy

**Cost:** Free (with sleep) or $7/month

---

#### Option B: Railway.app
**Why:** Easy Docker support, $5/month
**Steps:**
1. Push to GitHub
2. Import repo on Railway
3. Add env variables
4. Auto-deploys

**Cost:** $5/month

---

#### Option C: DigitalOcean App Platform
**Why:** Simple, reliable, $5/month
**Steps:**
1. Push to GitHub or DockerHub
2. Create app on DO
3. Configure env variables
4. Deploy

**Cost:** $5/month

---

#### Option D: Your Own VPS
**Why:** Full control, cheapest long-term
**Steps:**
1. Get VPS (DigitalOcean, Linode, Vultr)
2. Install Docker
3. Clone repo
4. Run docker-compose
5. Set up nginx reverse proxy
6. Get SSL cert (Let's Encrypt)

**Cost:** $4-6/month

---

### Step 3: Set Up Domain (Optional)
1. Buy domain ($10-15/year)
2. Point to deployment
3. SSL auto-configured

Or use free subdomain from platform.

---

## Recommended: Render.com with Docker

### Why Render?
- ✅ Free tier available
- ✅ Docker support
- ✅ Auto-deploy from GitHub
- ✅ Free SSL
- ✅ Easy environment variables
- ✅ Good for girlfriend to use

### Steps:
1. Push code to GitHub (private repo)
2. Sign up on render.com
3. New Web Service → Docker
4. Connect GitHub repo
5. Add 3 environment variables
6. Deploy
7. Get URL: `https://headache-tracker.onrender.com`

### Time: 15 minutes
### Cost: Free (or $7/month for no sleep)

---

## What to Do Now?

**Choose one:**
1. Test Docker locally first
2. Deploy to Render right away
3. Deploy to Railway
4. Set up VPS

**My recommendation:** 
Deploy to Render (easiest, free)

