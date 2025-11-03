#!/bin/bash
set -e

echo "Running database initialization..."
python3 /docker-entrypoint-initdb.d/init_db.py

echo "Database initialization complete!"

