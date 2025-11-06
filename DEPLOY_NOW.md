# Deploy to Render - Step by Step

## Your GitHub Repo
✅ https://github.com/kensuke0529/Headache.git

## Deploy Steps (10 minutes)

### 1. Go to Render
https://render.com → Sign up with GitHub

### 2. Create Web Service
- Click "New +" → "Web Service"
- Connect your repository: `kensuke0529/Headache`
- Click "Connect"

### 3. Configure Service
**Name:** `headache-tracker` (or anything you want)

**Environment:** `Docker`

**Instance Type:** `Free` (or $7/month for no sleep)

### 4. Add Environment Variables

Click "Advanced" → "Add Environment Variable"

Add these 3 variables:

#### Variable 1: OPENAI_API_KEY
```
Key: OPENAI_API_KEY
Value: [Copy from your .env file]
```

#### Variable 2: DRIVE_FOLDER_ID
```
Key: DRIVE_FOLDER_ID
Value: [Copy from your .env file]
```

#### Variable 3: SERVICE_ACCOUNT_JSON
```
Key: SERVICE_ACCOUNT_JSON
Value: [Copy from your .env file - the entire JSON on one line]
```

**Important:** Copy the entire JSON as ONE LINE (no line breaks!)

### 5. Deploy!
- Click "Create Web Service"
- Wait 5-10 minutes
- You'll get a URL like: `https://headache-tracker.onrender.com`

### 6. Test
- Open the URL
- Should see "Headache Tracker" with data loaded
- Try asking: "What are my headache patterns?"

### 7. Share with Girlfriend
Send her the URL and she's ready to use it!

---

## Troubleshooting

**If deployment fails:**
1. Check Render logs
2. Verify all 3 environment variables are set
3. Make sure SERVICE_ACCOUNT_JSON is one line

**If data won't load:**
- Check SERVICE_ACCOUNT_JSON is correct
- Verify Google Sheets permissions

---

## Cost

**Free Tier:**
- Sleeps after 15 min inactivity
- First load takes ~1 minute
- Perfect for testing

**Paid ($7/month):**
- Always on
- Instant responses
- Upgrade anytime

---

## Next Steps

1. Sign up on Render
2. Follow steps above
3. Get URL
4. Share with GF
5. Done! 🎉

