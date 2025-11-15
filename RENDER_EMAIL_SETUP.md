# Step-by-Step Email Setup for Render

This guide will walk you through setting up email for your GameReady app on Render, step by step.

## Why We Need Email

Your app needs email to:
- Send verification emails when users sign up
- Send daily reminder emails to athletes
- Send password reset emails (if you add that feature later)

Without email configured, users won't be able to verify their accounts and log in.

---

## Step 1: Choose an Email Service

**We recommend SendGrid** because:
- ✅ Free tier: 100 emails per day (plenty for most apps)
- ✅ Easy to set up
- ✅ Works great with Render
- ✅ Reliable delivery

**Alternative options:**
- Gmail (limited, not recommended for production)
- Mailgun (also good, similar to SendGrid)
- AWS SES (more complex, but very reliable)

**For this guide, we'll use SendGrid.**

---

## Step 2: Create a SendGrid Account

1. **Go to SendGrid website:**
   - Visit: https://sendgrid.com
   - Click "Start for Free" or "Sign Up"

2. **Create your account:**
   - Enter your email address
   - Create a password
   - Fill in your information
   - Verify your email address (check your inbox)

3. **Complete the setup:**
   - SendGrid will ask some questions about your use case
   - Select "Transactional Email" or "Marketing Email" (either works)
   - You can skip the optional steps for now

4. **Verify your account:**
   - SendGrid may ask you to verify your phone number
   - Follow the prompts to complete verification

**✅ You should now be logged into your SendGrid dashboard**

---

## Step 3: Create an API Key in SendGrid

An API key is like a password that lets your app send emails through SendGrid.

1. **In SendGrid dashboard, go to Settings:**
   - Look for "Settings" in the left sidebar
   - Click on "API Keys"

2. **Create a new API key:**
   - Click the big blue button "Create API Key"
   - Give it a name: `GameReady Production` (or any name you like)
   - Select permissions: Choose **"Full Access"** (or "Mail Send" if you want to be more restrictive)
   - Click "Create & View"

3. **IMPORTANT: Copy the API key immediately!**
   - SendGrid will show you the API key **ONCE**
   - It looks like: `SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Copy this entire key** - you won't be able to see it again!
   - Paste it somewhere safe (like a text file) temporarily

**✅ You now have a SendGrid API key**

---

## Step 4: Verify a Sender Email in SendGrid

SendGrid needs to know which email address you'll be sending from.

1. **In SendGrid dashboard:**
   - Go to "Settings" → "Sender Authentication"
   - Click "Verify a Single Sender"

2. **Fill in the form:**
   - **From Email Address**: Enter the email you want to send from
     - Example: `noreply@gamereadyapp.com` or `hello@gamereadyapp.com`
     - If you don't have a custom domain, you can use a Gmail address like `yourname@gmail.com`
   - **From Name**: `GameReady` (or your app name)
   - **Reply To**: Same as From Email Address
   - **Company Address**: Your address (required)
   - **City, State, Zip**: Your location
   - **Country**: Your country

3. **Verify the email:**
   - SendGrid will send a verification email to the address you entered
   - Check your inbox and click the verification link
   - The email address will now show as "Verified" in SendGrid

**✅ You now have a verified sender email**

---

## Step 5: Set Environment Variables in Render

Now we'll tell your Render app how to connect to SendGrid.

1. **Go to your Render dashboard:**
   - Visit: https://dashboard.render.com
   - Log in if needed

2. **Find your GameReady service:**
   - Click on your GameReady web service
   - If you have multiple services, find the one that's running your Django app

3. **Go to Environment tab:**
   - In your service page, click on "Environment" in the left sidebar
   - You'll see a list of environment variables

4. **Add the email configuration variables:**
   Click "Add Environment Variable" for each of these:

   **Variable 1:**
   - **Key**: `EMAIL_BACKEND`
   - **Value**: `django.core.mail.backends.smtp.EmailBackend`
   - Click "Save Changes"

   **Variable 2:**
   - **Key**: `EMAIL_HOST`
   - **Value**: `smtp.sendgrid.net`
   - Click "Save Changes"

   **Variable 3:**
   - **Key**: `EMAIL_PORT`
   - **Value**: `587`
   - Click "Save Changes"

   **Variable 4:**
   - **Key**: `EMAIL_USE_TLS`
   - **Value**: `True`
   - Click "Save Changes"

   **Variable 5:**
   - **Key**: `EMAIL_HOST_USER`
   - **Value**: `apikey`
   - (This is literally the word "apikey" - it's what SendGrid expects)
   - Click "Save Changes"

   **Variable 6:**
   - **Key**: `EMAIL_HOST_PASSWORD`
   - **Value**: `SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - (Paste your SendGrid API key from Step 3 here)
   - Click "Save Changes"

   **Variable 7:**
   - **Key**: `DEFAULT_FROM_EMAIL`
   - **Value**: The verified email address from Step 4
   - Example: `noreply@gamereadyapp.com` or `yourname@gmail.com`
   - Click "Save Changes"

   **Variable 8:**
   - **Key**: `BASE_URL`
   - **Value**: Your Render app URL
   - Example: `https://gameready.onrender.com` or `https://start.gamereadyapp.com`
   - (Check your Render service URL if you're not sure)
   - Click "Save Changes"

**✅ All environment variables are now set!**

---

## Step 6: Restart Your Render Service

After adding environment variables, you need to restart your service.

1. **In your Render service page:**
   - Click "Manual Deploy" → "Deploy latest commit"
   - OR click the three dots (⋯) menu → "Restart"
   - This will restart your app with the new environment variables

2. **Wait for deployment:**
   - Render will show "Deploying..." or "Building..."
   - Wait until it says "Live" (usually 1-2 minutes)

**✅ Your app is now restarted with email configuration**

---

## Step 7: Test Your Email Configuration

Let's verify that email is working!

1. **Open Render Shell (optional but recommended):**
   - In your Render service page, click "Shell" tab
   - This opens a terminal connected to your app

2. **Run the test command:**
   ```bash
   python manage.py test_email --to your-email@example.com
   ```
   - Replace `your-email@example.com` with your actual email address
   - Press Enter

3. **Check the output:**
   - If successful, you'll see: `✅ Test email sent successfully!`
   - Check your email inbox for the test email
   - If there's an error, the command will tell you what's wrong

**Alternative: Test by creating an account:**
- Go to your app's signup page
- Create a test account
- Check if you receive the verification email

**✅ Email is working if you received the test email!**

---

## Troubleshooting

### Problem: "Email is NOT properly configured"

**Solution:**
- Double-check that all 8 environment variables are set in Render
- Make sure there are no typos
- Make sure `EMAIL_HOST_PASSWORD` has your full SendGrid API key
- Restart your Render service after adding variables

### Problem: "Failed to send test email"

**Solution:**
- Verify your SendGrid API key is correct (check for typos)
- Make sure your sender email is verified in SendGrid
- Check SendGrid dashboard → Activity → see if emails are being attempted
- Make sure you haven't exceeded SendGrid's free tier limit (100 emails/day)

### Problem: "Test email sent but I don't receive it"

**Solution:**
- Check your spam/junk folder
- Wait a few minutes (sometimes there's a delay)
- Check SendGrid dashboard → Activity to see email status
- Try a different email address

### Problem: "I can't find my SendGrid API key"

**Solution:**
- You'll need to create a new one (you can't view old keys)
- Go to SendGrid → Settings → API Keys
- Create a new API key
- Update `EMAIL_HOST_PASSWORD` in Render with the new key
- Restart your Render service

---

## Quick Reference: All Environment Variables

Here's a checklist of all the variables you need in Render:

```
✅ EMAIL_BACKEND = django.core.mail.backends.smtp.EmailBackend
✅ EMAIL_HOST = smtp.sendgrid.net
✅ EMAIL_PORT = 587
✅ EMAIL_USE_TLS = True
✅ EMAIL_HOST_USER = apikey
✅ EMAIL_HOST_PASSWORD = SG.your-actual-api-key-here
✅ DEFAULT_FROM_EMAIL = your-verified-email@example.com
✅ BASE_URL = https://your-app-url.onrender.com
```

---

## What Happens Next?

Once email is configured:

1. **New users can verify their accounts** - They'll receive verification emails when they sign up
2. **Users can resend verification emails** - If they don't receive the first one, they can click "Resend" on the verification page
3. **Daily reminders work** - Athletes will receive daily reminder emails at 12pm their local time
4. **You'll see email errors in logs** - If something goes wrong, you'll see helpful error messages in Render logs

---

## Need Help?

If you're stuck:
1. Check Render logs: Service → Logs tab
2. Run the test command: `python manage.py test_email`
3. Check SendGrid dashboard → Activity to see if emails are being sent
4. Verify all environment variables are set correctly

---

**You're all set! 🎉**

Your GameReady app should now be able to send emails. Try creating a test account to verify everything works!

