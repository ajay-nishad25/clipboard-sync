Absolutely. Below is a complete root README.md you can use for the project. It explains what Clipboard Sync is, architecture, features, project structure, complete local setup, backend, admin, desktop agent, Android build/install, pairing, and end-to-end usage.

The commands are based on the current project state through Phase 9C. Django's standard development flow uses migrate followed by runserver, and Android's Gradle wrapper can build/install the debug APK.

# Clipboard Sync

A secure cross-device clipboard synchronization system that allows users to synchronize plain-text clipboard content between their Windows laptop and Android smartphone through a Django backend.

The project consists of three main components:

- **Django Backend** — handles users, devices, authentication, pairing, clipboard state, REST APIs, and WebSockets.
- **Desktop Agent** — monitors the Windows clipboard and synchronizes clipboard data with the backend.
- **Android Application** — allows users to manually send and receive clipboard data while respecting Android clipboard security restrictions.

---

# Table of Contents

- [Project Overview](#project-overview)
- [How the Project Works](#how-the-project-works)
- [Main Features](#main-features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Requirements](#requirements)
- [Initial Setup](#initial-setup)
- [1. Backend Setup](#1-backend-setup)
- [2. Django Admin Setup](#2-django-admin-setup)
- [3. Desktop Agent Setup](#3-desktop-agent-setup)
- [4. Android Setup](#4-android-setup)
- [5. Build Android Application](#5-build-android-application)
- [6. Connect Android Phone](#6-connect-android-phone)
- [7. Pair Desktop and Android](#7-pair-desktop-and-android)
- [8. Run the Complete System](#8-run-the-complete-system)
- [9. Laptop to Android Flow](#9-laptop-to-android-flow)
- [10. Android to Laptop Flow](#10-android-to-laptop-flow)
- [11. Multi-User Isolation](#11-multi-user-isolation)
- [12. Device Authentication](#12-device-authentication)
- [13. Clipboard Storage](#13-clipboard-storage)
- [14. Loop Prevention](#14-loop-prevention)
- [15. Run Tests](#15-run-tests)
- [16. Useful Commands](#16-useful-commands)
- [17. Troubleshooting](#17-troubleshooting)
- [18. Current Development Status](#18-current-development-status)
- [19. Production Roadmap](#19-production-roadmap)
- [20. Privacy and Security](#20-privacy-and-security)

---

# Project Overview

Clipboard Sync is designed to make it easy to move text between a Windows laptop and an Android phone.

For example:

```text
Windows Laptop
      │
      │ Copy text
      ▼
Desktop Agent
      │
      │ WebSocket
      ▼
Django Backend
      │
      │ REST API
      ▼
Android Phone

The reverse direction is also supported:

Android Phone
      │
      │ SEND CLIPBOARD
      ▼
Django Backend
      │
      │ WebSocket
      ▼
Desktop Agent
      │
      ▼
Windows Clipboard

The system is designed for multiple users.

For example:

User A
├── Laptop A
└── Android A

User B
├── Laptop B
└── Android B

User A must never receive User B's clipboard data.

How the Project Works

The complete system contains three major components.

                    ┌─────────────────────┐
                    │   Django Backend    │
                    │                     │
                    │ REST API            │
                    │ WebSocket           │
                    │ Users               │
                    │ Devices             │
                    │ Pairing              │
                    │ Authentication      │
                    │ ClipboardState      │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
              WebSocket                    REST
                 │                           │
                 ▼                           ▼
       ┌──────────────────┐       ┌──────────────────┐
       │  Desktop Agent   │       │   Android App    │
       │                  │       │                  │
       │ Clipboard       │       │ SEND CLIPBOARD   │
       │ Monitor         │       │ RECEIVE CLIPBOARD│
       │                  │       │                  │
       │ WebSocket Client │       │ Pairing          │
       └──────────────────┘       └──────────────────┘
Main Features
Desktop Agent
Windows clipboard monitoring
Automatic laptop-to-backend synchronization
Receives Android clipboard updates
Updates Windows clipboard automatically
Clipboard loop prevention
Persistent device ID
Persistent authentication token
Desktop pairing code generation
WebSocket authentication
WebSocket reconnection
Latest clipboard catch-up after reconnect
Android Application
Manual SEND CLIPBOARD
Manual RECEIVE CLIPBOARD
Android clipboard security compliant
No background clipboard harvesting
Desktop pairing
Persistent Android device ID
Persistent authentication token
WebSocket communication
REST API communication
Django Backend
Django REST Framework
Django Channels
WebSocket communication
User/device relationships
Device pairing
Device authentication
User-scoped clipboard synchronization
One active clipboard state per user
10-minute clipboard expiration
Django Admin
Token revocation
Multi-user isolation
Architecture
High-Level Architecture
                         INTERNET
                            │
                            ▼
                  ┌──────────────────┐
                  │  Django Backend  │
                  │                  │
                  │ REST API         │
                  │ WebSocket        │
                  │ Authentication   │
                  │ Device Pairing   │
                  │ User Isolation   │
                  └────────┬─────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
      ┌───────────────┐         ┌────────────────┐
      │ Desktop Agent │         │ Android App    │
      │               │         │                │
      │ Windows       │         │ Android        │
      │ Clipboard     │         │ Clipboard      │
      └───────────────┘         └────────────────┘
User and Device Architecture

Every device belongs to a Django user.

User
 │
 ├── Desktop Device
 │
 ├── Android Device
 │
 └── ClipboardState

For multiple users:

User A
 │
 ├── Desktop A
 ├── Android A
 └── Clipboard A

User B
 │
 ├── Desktop B
 ├── Android B
 └── Clipboard B

The backend uses user-scoped WebSocket groups.

clipboard_user_<user_id>

This prevents clipboard data from crossing between users.

Device Pairing

The Desktop Agent generates a temporary pairing code.

Example:

AB7K-29XM

The code:

Contains 8 characters
Uses uppercase characters
Expires after 5 minutes
Can only be used once
Cannot be reused after successful pairing

The pairing flow is:

Desktop Agent
      │
      │ Generate Pairing Code
      ▼
Django Backend
      │
      │ Display Code
      ▼
User
      │
      │ Enter Code
      ▼
Android App
      │
      │ POST pairing request
      ▼
Django Backend
      │
      │ Validate Code
      ▼
Desktop Device
      │
      ▼
Desktop Owner User
      │
      ▼
Android Device

The Android application does not decide which Django user it belongs to.

The backend determines ownership using the pairing code.

Device Authentication

After pairing, each device receives a persistent device credential.

Example:

devtok_<32 hexadecimal characters>

The raw token is not stored in the database.

Instead:

Raw Token
    │
    ▼
SHA-256
    │
    ▼
Token Hash
    │
    ▼
Database

REST requests use:

Authorization: Bearer <device-token>

WebSocket connections use the authenticated token.

Clipboard Storage

Each user has exactly one active clipboard state.

Example:

User A
   │
   └── ClipboardState
          │
          ├── content
          ├── updated_at
          └── expires_at

If the user copies:

Hello

then:

ClipboardState = Hello

If the user immediately copies:

Hello World

the previous value is replaced:

ClipboardState = Hello World

Clipboard history is not maintained.

Clipboard Expiration

Each clipboard state expires after 10 minutes.

Example:

Copied at:
10:00 AM

Expires at:
10:10 AM

After expiration, the backend no longer returns the clipboard data.

This minimizes unnecessary storage of potentially sensitive clipboard information.

Android Clipboard Security

Modern Android versions restrict background clipboard access.

Therefore the Android application intentionally does not attempt to silently read the clipboard whenever another application copies something.

Instead, the user manually controls clipboard synchronization.

Send
Copy something on Android
        ↓
Open Clipboard Sync
        ↓
SEND CLIPBOARD
Receive
Laptop clipboard
        ↓
Django
        ↓
Open Clipboard Sync
        ↓
RECEIVE CLIPBOARD
        ↓
Android clipboard

This is an intentional design decision.

Project Structure
clipboard-sync/
│
├── backend/
│   │
│   ├── clipboard/
│   │   ├── admin.py
│   │   ├── consumers.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── tests.py
│   │   ├── tests_websocket.py
│   │   └── migrations/
│   │
│   ├── config/
│   ├── manage.py
│   ├── db.sqlite3
│   └── README.md
│
├── desktop-agent/
│   │
│   ├── src/
│   │   └── clipboard_agent/
│   │       ├── cli.py
│   │       ├── config.py
│   │       ├── monitor.py
│   │       └── ws_client.py
│   │
│   ├── tests/
│   ├── pyproject.toml
│   └── README.md
│
├── android-app/
│   │
│   ├── app/
│   │   ├── src/
│   │   │   ├── main/
│   │   │   └── test/
│   │   │
│   │   └── build.gradle
│   │
│   ├── gradlew
│   ├── gradlew.bat
│   └── README.md
│
├── docs/
│   ├── architecture.md
│   ├── development.md
│   ├── protocol.md
│   └── progress.md
│
└── README.md
Technology Stack
Backend
Python
Django
Django REST Framework
Django Channels
SQLite
WebSockets
Desktop
Python
Pyperclip
WebSocket client
Android
Java
Android SDK
Gradle
OkHttp
Android ClipboardManager
Requirements

Before running the project, install:

Windows
Windows 10/11
Python 3.x
Git
PowerShell
Android Development
Android Studio
Android SDK
Android SDK Platform Tools
Java 17
Android device
USB debugging enabled
Initial Setup

Clone the repository:

git clone <repository-url>

Enter the project:

cd clipboard-sync

The project contains three independently runnable components:

backend/
desktop-agent/
android-app/
1. Backend Setup

Open PowerShell.

Go to the backend:

cd "C:\Users\Ajay Nishad\Documents\clipboard-sync\backend"
Activate Virtual Environment

If the virtual environment already exists:

.\.venv\Scripts\Activate.ps1

You should see something similar to:

(.venv) PS C:\Users\...\backend>
Install Dependencies

If a requirements file is available:

pip install -r requirements.txt
Run Database Migrations

Run:

python manage.py migrate

This creates/updates the Django database tables.

Check Django

Run:

python manage.py check

Expected:

System check identified no issues
Start Django Server

Run:

python manage.py runserver 0.0.0.0:8000

The development server will be available at:

http://127.0.0.1:8000/

Django's runserver is intended for development, not production deployment.

Keep this terminal running.

2. Django Admin Setup

Create a Django superuser.

Run:

python manage.py createsuperuser

Django will ask:

Username:
Email address:
Password:
Password (again):

After successful creation:

Superuser created successfully.

Start the server if it is not already running:

python manage.py runserver 0.0.0.0:8000

Open:

http://127.0.0.1:8000/admin/

Login with the superuser credentials.

Django Admin

The admin panel allows inspection of:

Users
Devices
Clipboard States
Pairing Codes
Device Credentials

For example:

User A
 │
 ├── Desktop Device
 ├── Android Device
 └── Clipboard State

The raw device authentication token should not be stored/displayed in plaintext.

3. Desktop Agent Setup

Open a second PowerShell terminal.

Go to:

cd "C:\Users\Ajay Nishad\Documents\clipboard-sync\desktop-agent"
Activate Desktop Virtual Environment
.\.venv\Scripts\Activate.ps1
Install Desktop Dependencies

If required:

pip install -e .
Start Desktop Agent

Run:

clipboard-agent

Or:

python -m clipboard_agent.cli

The Desktop Agent should start monitoring the Windows clipboard.

Desktop Pairing Code

When the Desktop Agent starts, it generates a pairing code.

Example:

==================================================
Clipboard Sync Desktop Agent
==================================================

Pair your Android device using this code:

        AB7K-29XM

Code expires in 5 minutes.

==================================================

Keep this terminal open.

Desktop Device ID

The Desktop Agent generates a persistent device ID.

Example:

desktop-4f2a91c8

The ID is stored locally so that restarting the Desktop Agent does not create a new device identity every time.

Desktop Authentication Token

The Desktop Agent also maintains a persistent device authentication token.

The token is stored locally.

Do not commit this token to Git.

Do not share the token publicly.

4. Android Setup

Open Android Studio.

Open:

clipboard-sync/android-app

Allow Android Studio to:

Sync Gradle
Download required SDK components
Index the project
Android Requirements

The project currently uses:

Java 17
Android SDK
Gradle Wrapper

Make sure Android Studio recognizes the correct Java installation.

Connect Physical Android Device

On the Android phone:

Settings
   ↓
About Phone
   ↓
Build Number
   ↓
Tap multiple times
   ↓
Developer Options
   ↓
USB Debugging

Enable USB debugging.

Connect the phone to the Windows laptop using USB.

Verify Android Device

Open PowerShell:

adb devices

Expected:

List of devices attached
XXXXXXXXXXXX    device

If the phone displays an authorization dialog, accept it.

5. Build Android Application

Go to the Android project:

cd "C:\Users\Ajay Nishad\Documents\clipboard-sync\android-app"

Run:

.\gradlew.bat assembleDebug

Expected:

BUILD SUCCESSFUL

The debug APK will be generated inside:

android-app/app/build/outputs/apk/debug/

The APK is normally named:

app-debug.apk

Android's Gradle wrapper supports building the debug APK through assembleDebug.

Install Android Application

With the phone connected:

.\gradlew.bat installDebug

Or install the generated APK manually:

adb install app\build\outputs\apk\debug\app-debug.apk

Open:

Clipboard Sync

on the phone.

6. Connect Android to Local Django

Because the Android application is running on a physical phone, 127.0.0.1 on the phone normally refers to the phone itself.

For local development, use:

adb reverse tcp:8000 tcp:8000

This forwards the phone's local port 8000 to the computer's port 8000.

Verify the reverse connection:

adb reverse --list

Expected:

8000 8000

If the phone is disconnected/reconnected, run the reverse command again.

7. Pair Desktop and Android

Make sure these are running:

Django Backend
       ↓
Desktop Agent
       ↓
Android Application
Step 1 — Get Pairing Code

Look at the Desktop Agent terminal.

Example:

AB7K-29XM
Step 2 — Open Android App

Open:

Clipboard Sync

Find:

Pair Desktop
Step 3 — Enter Pairing Code

Enter:

AB7K-29XM

Tap:

PAIR DEVICE
Expected Result

Android should display something similar to:

Status: Device paired successfully

The Android device is now associated with the same Django user as the Desktop device.

8. Run the Complete System

For normal development, use three terminals.

Terminal 1 — Django
cd "C:\Users\Ajay Nishad\Documents\clipboard-sync\backend"

.\.venv\Scripts\Activate.ps1

python manage.py migrate

python manage.py runserver 0.0.0.0:8000

Keep running.

Terminal 2 — Desktop Agent
cd "C:\Users\Ajay Nishad\Documents\clipboard-sync\desktop-agent"

.\.venv\Scripts\Activate.ps1

clipboard-agent

Keep running.

Terminal 3 — Android / ADB
cd "C:\Users\Ajay Nishad\Documents\clipboard-sync\android-app"

adb devices

adb reverse tcp:8000 tcp:8000

.\gradlew.bat installDebug

Then open the application on the phone.

Complete Startup Order

The recommended startup order is:

1. Start Django
        ↓
2. Verify Django is running
        ↓
3. Start Desktop Agent
        ↓
4. Get pairing code
        ↓
5. Connect Android phone
        ↓
6. Run adb reverse
        ↓
7. Build/install Android app
        ↓
8. Open Android app
        ↓
9. Pair Android with Desktop
        ↓
10. Start Android synchronization service
        ↓
11. Test clipboard synchronization
9. Laptop → Android

This is the laptop-to-phone workflow.

Step 1

Copy some text on Windows.

Example:

Hello from Windows Laptop
Step 2

The Desktop Agent detects the clipboard change.

The Desktop Agent sends the data to Django through WebSocket.

Windows Clipboard
       ↓
Desktop Agent
       ↓
WebSocket
       ↓
Django
       ↓
ClipboardState
Step 3

Open:

Clipboard Sync

on Android.

Step 4

Tap:

RECEIVE CLIPBOARD

The Android application calls:

GET /api/clipboard/latest/

with the authenticated device token.

Step 5

Django returns the latest clipboard belonging to that user.

Android places the returned text into the system clipboard.

Step 6

Paste somewhere on Android.

Expected:

Hello from Windows Laptop
10. Android → Laptop

This is the phone-to-laptop workflow.

Step 1

Copy text on Android.

Example:

Hello from Android Phone
Step 2

Open:

Clipboard Sync
Step 3

Tap:

SEND CLIPBOARD
Step 4

The Android application reads the clipboard while the application is in focus.

The text is sent through the authenticated WebSocket.

Android Clipboard
       ↓
SEND CLIPBOARD
       ↓
Android WebSocket
       ↓
Django
       ↓
ClipboardState
       ↓
User-scoped WebSocket
       ↓
Desktop Agent
Step 5

Android should display:

Sending clipboard...

Then:

Clipboard sent successfully
Step 6

The Desktop Agent receives the remote update.

It updates the Windows clipboard.

Step 7

Open Notepad and press:

Ctrl + V

Expected:

Hello from Android Phone
11. Multi-User Isolation

This is one of the most important security features.

Suppose there are two users:

User A
├── Desktop A
└── Android A

User B
├── Desktop B
└── Android B

User A sends:

Private Clipboard A

Only User A's devices should receive it.

User B must never receive:

Private Clipboard A

Likewise:

User B Clipboard

must never reach User A.

User-Scoped WebSocket Groups

The backend uses groups similar to:

clipboard_user_1
clipboard_user_2
clipboard_user_3

A clipboard update from User A is broadcast only to:

clipboard_user_A

It is not broadcast globally.

12. Clipboard Expiration

Each user has only one active clipboard value.

Example:

10:00
User copies "Hello"

10:01
User copies "Hello World"

Database:
"Hello World"

The previous value is replaced.

After 10 minutes:

ClipboardState
      ↓
Expired
      ↓
Deleted / unavailable

The API should no longer return the expired value.

13. Loop Prevention

The system must prevent:

Android
   ↓
Django
   ↓
Desktop
   ↓
Windows Clipboard
   ↓
Desktop detects clipboard again
   ↓
Django
   ↓
Desktop
   ↓
...

The Desktop Agent keeps track of remotely applied clipboard content.

When remote clipboard content is written to Windows:

pyperclip.copy(content)

the monitor's internal state is also updated.

Therefore the same clipboard value is not immediately sent back to Django.

14. Desktop Catch-Up

The Desktop Agent can recover the latest clipboard state when reconnecting.

Example:

Android
   ↓
Django
   ↓
ClipboardState

Desktop Agent is offline.

Later:

Desktop Agent starts
        ↓
WebSocket connects
        ↓
GET latest clipboard
        ↓
Recover clipboard
        ↓
Windows Clipboard

This allows the Desktop Agent to recover the latest available clipboard state.

15. Device Authentication

Every device has a credential.

Desktop:

Desktop Device
      ↓
Device Token

Android:

Android Device
      ↓
Device Token

The backend validates the credential before allowing access.

REST Authentication

Requests contain:

Authorization: Bearer <device-token>
WebSocket Authentication

WebSocket connections use the authenticated device token.

Unauthenticated devices are rejected.

16. Django Admin Verification

Open:

http://127.0.0.1:8000/admin/

Login with the Django superuser.

You can inspect:

Users
Devices
Clipboard States
Pairing Codes
Device Credentials
Devices

You should see relationships such as:

User A
 ├── desktop-xxxxxxxx
 └── android-xxxxxxxx
Clipboard States

You should see one active clipboard state per user.

Example:

User:
user_A

Content:
Hello from Android

Updated:
10:20

Expires:
10:30
Pairing Codes

You can inspect:

Code
Desktop Device
Created At
Expires At
Used
Used At
Device Credentials

You can inspect the credential records associated with devices.

The backend stores the token hash rather than the raw credential.

17. Run Tests

The project contains automated tests for backend, desktop, and Android components.

Backend Tests

Go to:

cd backend

Run:

.\.venv\Scripts\python.exe manage.py check

Then:

.\.venv\Scripts\python.exe manage.py test

Expected:

OK
Desktop Tests

Go to:

cd desktop-agent

Run:

.\.venv\Scripts\python.exe -m unittest discover -s tests -v

Expected:

OK
Android Tests

Go to:

cd android-app

Run:

.\gradlew.bat test

Expected:

BUILD SUCCESSFUL
Android Build Test

Run:

.\gradlew.bat assembleDebug

Expected:

BUILD SUCCESSFUL
18. Useful Commands
Start Django
python manage.py runserver 0.0.0.0:8000
Apply migrations
python manage.py migrate
Check Django
python manage.py check
Create Admin
python manage.py createsuperuser
Backend Tests
python manage.py test
Check Android Devices
adb devices
Connect Android Localhost to PC
adb reverse tcp:8000 tcp:8000
Check ADB Reverse
adb reverse --list
Remove ADB Reverse
adb reverse --remove tcp:8000
Build Android
.\gradlew.bat assembleDebug
Install Android
.\gradlew.bat installDebug
Android Tests
.\gradlew.bat test
Start Desktop Agent
clipboard-agent

or:

python -m clipboard_agent.cli
19. Troubleshooting
Django Does Not Start

Run:

python manage.py check

If migrations are pending:

python manage.py migrate

Then:

python manage.py runserver 0.0.0.0:8000
Android Cannot Connect to Django

First verify:

adb devices

Then:

adb reverse tcp:8000 tcp:8000

Verify:

adb reverse --list

Then restart the Android application.

Android Device Not Showing

Run:

adb devices

If it shows:

unauthorized

unlock the phone and accept the USB debugging authorization dialog.

Pairing Code Not Working

Check:

Desktop Agent is running.
Django is running.
Android has network access to Django.
adb reverse is active.
Pairing code has not expired.
Pairing code has not already been used.

Generate a new pairing code if necessary.

WebSocket Not Connecting

Check:

Django running
        ↓
Desktop Agent running
        ↓
Correct backend URL
        ↓
Device credential available
        ↓
Token not revoked

For Android local development, also check:

adb reverse tcp:8000 tcp:8000
Android Build Fails

Try:

.\gradlew.bat clean

Then:

.\gradlew.bat assembleDebug

If Android Studio reports an SDK problem, open the project in Android Studio and allow Gradle/SDK synchronization to complete.

Clipboard Does Not Sync

Check the direction.

Laptop → Android

Make sure:

Desktop Agent
     ↓
Django
     ↓
Android RECEIVE CLIPBOARD
Android → Laptop

Make sure:

Android SEND CLIPBOARD
     ↓
Django
     ↓
Desktop Agent
20. Current Development Status
Phase	Feature	Status
Phase 1	Project Foundation	✅ Complete
Phase 2	Backend REST API	✅ Complete
Phase 3	Desktop Clipboard Monitoring	✅ Complete
Phase 4	WebSocket Infrastructure	✅ Complete
Phase 5	Desktop WebSocket Sync	✅ Complete
Phase 6	Android Manual Clipboard Sync	✅ Complete
Phase 7	Remote Broadcasting & Loop Prevention	✅ Complete
Phase 8	Catch-up & Persistent Device Identity	✅ Complete
Phase 9A	Multi-user Data Isolation	✅ Complete
Phase 9B	Desktop ↔ Android Pairing	✅ Complete
Phase 9C	Device Authentication	✅ Complete
Phase 9D	Production Configuration	🔲 Planned
Phase 9E	Production Deployment & Hardening	🔲 Planned
21. Production Roadmap

The current project is still primarily a development/POC environment.

The next major phase is production readiness.

Phase 9D — Production Configuration

Planned:

Production backend URL
HTTPS
Secure WebSockets (WSS)
Environment variables
Secret management
Production Android configuration
Production Desktop configuration
Production API endpoints
Production CORS/host configuration
Secure transport configuration
Phase 9E — Production Deployment

Planned:

PostgreSQL
Redis
Production ASGI deployment
Daphne or equivalent ASGI server
Secure environment configuration
Production logging
Monitoring
Backup strategy
Security hardening
Android release APK/AAB
Desktop distribution/package
Production domain
HTTPS certificates
22. Development vs Production
Current Development Setup
Django
   ↓
127.0.0.1:8000

Android
   ↓
adb reverse

Desktop
   ↓
127.0.0.1:8000

Current development communication uses local development endpoints.

Future Production Setup

The final architecture will look more like:

                 Internet
                    │
                    ▼
          ┌──────────────────┐
          │ Production Server│
          │                  │
          │ Django           │
          │ REST API         │
          │ WebSocket        │
          │ PostgreSQL       │
          │ Redis            │
          └────────┬─────────┘
                   │
          ┌────────┴─────────┐
          │                  │
          ▼                  ▼
    Windows Agent       Android App

Production communication will use:

HTTPS
WSS

instead of local development endpoints.

23. Privacy and Security

Clipboard contents can contain sensitive information such as:

Passwords
Authentication codes
Personal messages
Private URLs
API keys
Sensitive business information

Therefore the project follows these principles:

Plain-text clipboard synchronization only.
No clipboard history.
One active clipboard state per user.
Clipboard state expires after 10 minutes.
User-scoped WebSocket communication.
Device authentication.
Device pairing.
Token hashing on the backend.
Token revocation support.
Clipboard content is not intentionally written to logs.
Android does not silently harvest clipboard data in the background.
24. Important Security Notes

Never commit:

.env
database credentials
Django SECRET_KEY
device tokens
API keys
production passwords
private certificates

Use environment variables and secret management for production.

The Django development server must not be used as the production server. Use a proper production deployment architecture during Phase 9D/9E.

25. Complete Startup Checklist

Use this checklist whenever you want to run the entire project locally.

[ ] Start Windows
        ↓
[ ] Connect Android phone
        ↓
[ ] adb devices
        ↓
[ ] Start Django
        ↓
[ ] python manage.py migrate
        ↓
[ ] python manage.py runserver 0.0.0.0:8000
        ↓
[ ] Start Desktop Agent
        ↓
[ ] Get pairing code
        ↓
[ ] adb reverse tcp:8000 tcp:8000
        ↓
[ ] Build/install Android APK
        ↓
[ ] Open Clipboard Sync
        ↓
[ ] Pair Android with Desktop
        ↓
[ ] Start Android service
        ↓
[ ] Test Laptop → Android
        ↓
[ ] Test Android → Laptop
        ↓
[ ] Verify Django Admin
26. Complete System Flow
Laptop → Android
Windows Clipboard
        ↓
Desktop Agent
        ↓
Authenticated WebSocket
        ↓
Django
        ↓
User ClipboardState
        ↓
Android RECEIVE CLIPBOARD
        ↓
Authenticated REST API
        ↓
Android Clipboard
Android → Laptop
Android Clipboard
        ↓
User opens Clipboard Sync
        ↓
SEND CLIPBOARD
        ↓
Authenticated WebSocket
        ↓
Django
        ↓
User ClipboardState
        ↓
User-scoped WebSocket Broadcast
        ↓
Desktop Agent
        ↓
Windows Clipboard
27. Final Project Goal

The final goal of Clipboard Sync is to provide a secure and private clipboard synchronization system where each user's devices are isolated from every other user.

                    Clipboard Sync
                         │
             ┌───────────┴───────────┐
             │                       │
        Windows Laptop          Android Phone
             │                       │
             └───────────┬───────────┘
                         │
                         ▼
                  Django Backend

For multiple users:

User A
 │
 ├── Laptop A
 └── Android A
        │
        ▼
   Clipboard A


User B
 │
 ├── Laptop B
 └── Android B
        │
        ▼
   Clipboard B

The fundamental security rule is:

User A ❌→ User B Clipboard

User B ❌→ User A Clipboard

Each user can synchronize clipboard data only between their own paired devices.

📚 Documentation

Additional project documentation:

docs/
│
├── architecture.md
├── development.md
├── protocol.md
└── progress.md

Component documentation:

backend/README.md
desktop-agent/README.md
android-app/README.md

These documents contain deeper implementation and protocol details.

🤝 Development Workflow

When starting a new development phase:

Read docs/progress.md.
Read docs/architecture.md.
Read docs/protocol.md.
Understand the current implementation.
Plan the changes.
Modify only the required components.
Add/update automated tests.
Run backend tests.
Run desktop tests.
Run Android tests.
Build the Android application.
Perform manual end-to-end testing.
Update documentation.
Review the complete architecture.
Commit changes only when explicitly required.
📌 Current Project State

Clipboard Sync has completed:

Phase 1
    ↓
Phase 2
    ↓
Phase 3
    ↓
Phase 4
    ↓
Phase 5
    ↓
Phase 6
    ↓
Phase 7
    ↓
Phase 8
    ↓
Phase 9A
    ↓
Phase 9B
    ↓
Phase 9C









=======================================================

# Clipboard Sync

A cross-platform clipboard synchronization system between a Python desktop agent (Windows) and a Java Android app through a Django backend.

## Current Status (Verified Baseline)

Phases 1–9 are **complete and verified**:
- **Real-Time Desktop Sync**: Windows desktop agent syncs clipboard updates over WebSocket (`clipboard.update` / `clipboard.remote_update`).
- **Manual Android Sync**: Java Android application uses `[ SEND CLIPBOARD ]` (WebSocket) and `[ RECEIVE CLIPBOARD ]` (`GET /api/clipboard/latest/`) to respect Android 10+ background clipboard restrictions.
- **Desktop Catch-Up**: Desktop Agent fetches the latest server entry on startup or reconnection without triggering feedback loops.
- **Persistent Device IDs**: Auto-generated persistent UUIDs for Desktop and Android installations.

See [Phase 9 Roadmap](#phase-9-roadmap--target-architecture-planned--next) for upcoming multi-user identity and production isolation architecture.

---

## Repository Layout

```text
clipboard-sync/
├── backend/         # Django REST API, SQLite, Channels WebSocket (Daphne)
├── desktop-agent/   # Python clipboard detector, listener thread & WebSocket client
├── android-app/     # Java Android application (Manual SEND/RECEIVE UI & Service)
├── docs/            # Architecture, protocol, development, and progress docs
├── README.md
├── AGENTS.md
└── .gitignore
```

---

## Technology Stack

- **Backend**: Python, Django, Django REST Framework, Django Channels, Daphne, SQLite (`InMemoryChannelLayer`).
- **Desktop Agent**: Python, `pyperclip`, `websockets` (sync client with background listener thread).
- **Android App**: Java 17, Android SDK API 34, `OkHttp 5.5.0` (WebSocket & HTTP REST).

See [architecture](docs/architecture.md), [development](docs/development.md), [protocol](docs/protocol.md), and [progress](docs/progress.md) for complete details.

---

## Endpoints (Current POC Baseline)

| Protocol | Endpoint | Purpose |
|----------|----------|---------|
| HTTP | `POST /api/clipboard/` | Store a clipboard entry (regression testing) |
| HTTP | `GET /api/clipboard/latest/` | Retrieve newest clipboard entry (Android RECEIVE & Desktop Catch-Up) |
| WebSocket | `ws://127.0.0.1:8000/ws/clipboard/?device_id=<id>` | Real-time bidirectional clipboard sync & remote update broadcast |

---

## Phase 9 Roadmap & Target Architecture (PLANNED / NEXT)

Phase 9 transitions the project from a single-user local proof-of-concept into a multi-user, production-ready architecture focused on **User Data Isolation**:

```text
User A (User ID A)                          User B (User ID B)
  ├── Desktop A (Authenticated)               ├── Desktop B (Authenticated)
  └── Android A (Paired)                      └── Android B (Paired)
        │                                           │
        ▼                                           ▼
Channel: clipboard_user_A                   Channel: clipboard_user_B
  (Isolated to User A)                        (Isolated to User B)
```

### Key Target Features
1. **User Data Isolation**: Multi-user model with user-scoped channel routing (`clipboard_user_<USER_ID>`). User A and User B cannot access or receive each other's clipboard data.
2. **Device Pairing**: Desktop Agent generates a short enrollment code (e.g. `AB7K-29XM`); Android app exchanges code for a persistent device credential token.
3. **Single Active Clipboard & 10-Minute Expiration**: Each user retains exactly one current clipboard entry with automatic 10-minute retention expiration (`expires_at = now + 10m`).
4. **Production Security & Transport**: HTTPS (`https://`) and WSS (`wss://`), token authentication, restricted admin panel, and no clipboard text in logs.

---

## Scope and Safety

- Plain text clipboard only. Images, files, rich text, screenshots, and passwords are excluded.
- Android 10+ background clipboard rules are respected (no background harvesting).
- Never commit real credentials or `.env` files.
