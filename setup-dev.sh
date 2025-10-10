#!/bin/bash

# NRTaxAI Development Setup Script

set -e

echo "🚀 Setting up NRTaxAI development environment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed."
    exit 1
fi

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is required but not installed."
    exit 1
fi

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "❌ Redis is required but not installed."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Backend setup
echo "📦 Setting up backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Copy environment file
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit backend/.env with your configuration"
fi

echo "✅ Backend setup complete"

# Frontend setup
echo "📦 Setting up frontend..."
cd ../frontend

# Install dependencies
echo "Installing Node.js dependencies..."
npm install

# Copy environment file
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cat > .env << EOF
REACT_APP_API_URL=http://localhost:8000/api/v1
EOF
    echo "✅ Frontend environment file created"
fi

echo "✅ Frontend setup complete"

# Database setup instructions
echo ""
echo "🗄️  Database Setup Required:"
echo "1. Create a PostgreSQL database named 'nrtaxai'"
echo "2. Update backend/.env with your database credentials"
echo "3. Run: cd backend && python init_db.py"
echo ""

# Redis setup instructions
echo "🔴 Redis Setup Required:"
echo "1. Start Redis server: redis-server"
echo "2. Or use Docker: docker run -d -p 6379:6379 redis:alpine"
echo ""

# Final instructions
echo "🎉 Setup complete!"
echo ""
echo "To start development:"
echo "1. Start Redis: redis-server"
echo "2. Start backend: cd backend && source venv/bin/activate && python main.py"
echo "3. Start frontend: cd frontend && npm start"
echo ""
echo "The application will be available at:"
echo "- Frontend: http://localhost:3000"
echo "- Backend API: http://localhost:8000"
echo "- API Docs: http://localhost:8000/docs"
echo ""
echo "Happy coding! 🚀"
