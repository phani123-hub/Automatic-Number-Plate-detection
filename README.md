# 🚗 Night Plate Detection - License Plate Recognition System

A full-stack web application for detecting and recognizing vehicle license plates in nighttime conditions using YOLOv9 and OCR.

## 📋 Project Overview

This system provides real-time license plate detection and recognition optimized for low-light and nighttime conditions. It features a React frontend, Flask backend API, and MongoDB database for storing detection history.

### Key Features

- ✅ **Real-time Detection**: Process video streams, webcam feeds, or uploaded videos
- ✅ **Night Optimization**: Enhanced preprocessing for low-light conditions
- ✅ **OCR Recognition**: Multi-engine OCR (EasyOCR + Tesseract) for text extraction
- ✅ **User Authentication**: JWT-based authentication with bcrypt password hashing
- ✅ **Detection History**: MongoDB storage with user-specific detection logs
- ✅ **Duplicate Filtering**: Smart deduplication to show only unique detections
- ✅ **Export Functionality**: Download detection logs as CSV

## 🏗️ Architecture

### Frontend (React)
- **Framework**: React 19.2 with React Router
- **UI Library**: React Bootstrap 5.3
- **State Management**: Context API
- **Authentication**: JWT tokens with localStorage

### Backend (Flask)
- **Framework**: Flask 3.1 with Flask-CORS
- **ML Models**: YOLOv9 (PyTorch), EasyOCR, Tesseract
- **Database**: MongoDB with PyMongo
- **Authentication**: JWT + Bcrypt

### Database (MongoDB)
- User accounts and authentication
- Detection history with timestamps
- User-specific filtering

## 📦 Project Structure

```
night-plate-detection-yolov9c/
├── frontend/                 # React frontend
│   ├── public/              # Static assets
│   ├── src/
│   │   ├── api/            # API client functions
│   │   ├── components/     # React components
│   │   │   ├── Auth/       # Login/Register
│   │   │   ├── Dashboard/  # Main dashboard
│   │   │   ├── Detection/  # Detection UI
│   │   │   └── common/     # Shared components
│   │   ├── context/        # React Context (Auth, Config)
│   │   ├── hooks/          # Custom hooks
│   │   └── App.js          # Main app component
│   ├── package.json
│   └── SECURITY.md
│
├── backend/                 # Flask backend
│   ├── api/
│   │   ├── routes/         # API endpoints
│   │   └── services/       # Business logic
│   ├── auth/               # Authentication
│   ├── core/               # ML models
│   │   ├── detector.py     # YOLOv8x detector (trained for nighttime)
│   │   ├── ocr.py          # OCR engines
│   │   ├── preprocess.py   # Image preprocessing
│   │   ├── postprocess.py  # Text cleaning
│   │   └── tracking.py     # Vehicle tracking
│   ├── database/           # MongoDB repositories
│   ├── models/             # ML model files
│   ├── data/               # Data storage
│   ├── scripts/            # Utility scripts
│   ├── config.py           # Configuration
│   ├── app_factory.py      # Flask app factory
│   ├── run_flask.py        # Development server
│   └── requirements.txt    # Python dependencies
│
├── .gitignore
└── README.md
```

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+** (3.14 supported with limitations)
- **Node.js 18+** and npm
- **MongoDB** (local or cloud instance)
- **Tesseract OCR** (optional, for fallback OCR)

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Configure environment variables**:
   - Copy `.env.example` to `.env` (if exists)
   - Update MongoDB URI, JWT secret, etc.

6. **Run the backend**:
   ```bash
   python run_flask.py
   ```
   Backend runs on `http://localhost:5000`

### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start development server**:
   ```bash
   npm start
   ```
   Frontend runs on `http://localhost:3000`

### View the Dashboard Without the Backend

If Flask or MongoDB is unavailable, start only the frontend with `npm start` and select **Continue with demo dashboard** on the login page. This opens the dashboard and analytics with clearly labeled sample detection data; it does not contact the backend. Live camera and video detection still require the Flask backend.

## 🔧 Configuration

### Backend Configuration (`backend/.env`)

```env
# MongoDB
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DB_NAME=night_plate_detection

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# App
APP_NAME=Night Plate Detection
APP_VERSION=1.0.0
```

### Frontend Configuration (`frontend/src/.env`)

```env
REACT_APP_API_URL=http://localhost:5000/api
REACT_APP_NAME=Night Plate Detection
```

## 🎯 Usage

### 1. Register/Login
- Navigate to `http://localhost:3000`
- Create an account with strong password
- Login with credentials

### 2. Upload Video
- Click "Upload Video" tab
- Select a video file (MP4, AVI, etc.)
- Configure detection parameters (confidence, preprocessing)
- Start detection

### 3. View Results
- Real-time detection results appear on the right panel
- View detection history in the logs viewer
- Export detections as CSV

### 4. Manage Detections
- Filter by plate text
- Toggle between unique and all detections
- View detection statistics

## 🔐 Security

### Password Requirements
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character

### API Security
- JWT token authentication
- Bcrypt password hashing (12 rounds)
- CORS configured for local development
- Environment variables for secrets

### Development Vulnerabilities
See `frontend/SECURITY.md` for details on npm audit warnings (dev dependencies only).

## 📊 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/logout` - Logout user

### Detection
- `POST /api/detection/process-frame` - Process single frame
- `POST /api/detection/upload-video` - Upload video for detection
- `GET /api/detection/history` - Get detection history
- `GET /api/detection/export` - Export detections as CSV

### Configuration
- `GET /api/config` - Get current config
- `PUT /api/config` - Update configuration

## 🛠️ Development

### Running Tests
```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Building for Production
```bash
# Frontend
cd frontend
npm run build

# Backend (with gunicorn)
cd backend
gunicorn -w 4 -b 0.0.0.0:5000 "app_factory:create_app()"
```

## 📝 Environment Notes

### Python 3.14 Compatibility
- ✅ PyTorch inference supported
- ❌ ONNX Runtime not yet available (use PyTorch only)
- ✅ All Flask APIs functional
- ✅ MongoDB operations working

### Model Files
Place your trained YOLOv8x model at:
- `backend/models/yolov8x.pt` (PyTorch - nighttime trained)

If model is missing, the system will auto-download `yolov8n.pt` as fallback.

## 🐛 Troubleshooting

### Backend won't start
- Check Python version: `python --version`
- Verify MongoDB connection in `.env`
- Ensure all dependencies installed: `pip list`

### Frontend build fails
- Clear cache: `npm cache clean --force`
- Delete `node_modules` and `package-lock.json`
- Reinstall: `npm install`

### Detection not working
- Verify model file exists in `backend/models/`
- Check CUDA availability: `torch.cuda.is_available()`
- Review backend logs for errors

## 🙏 Acknowledgments

- YOLOv9 for object detection
- Ultralytics for YOLO implementation
- EasyOCR for text recognition
- React and Flask communities
