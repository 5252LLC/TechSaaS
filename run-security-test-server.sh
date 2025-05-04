#!/bin/bash

# Run Flask development server with test routes enabled
export ENABLE_TEST_ROUTES=true
export TESTING=true
export FLASK_ENV=testing
export FLASK_DEBUG=1
export FLASK_APP=ai-service/api/v1/app.py

# Start the server
echo "Starting TechSaaS API with security test routes enabled..."
echo "----------------------------------------------------"
echo "IMPORTANT: Test routes should NEVER be enabled in production!"
echo "----------------------------------------------------"
echo ""
echo "API will be available at: http://localhost:5000"
echo "Security test endpoints available:"
echo "- Public: /api/v1/status, /api/v1/docs"
echo "- User: /api/v1/protected/user-profile, /api/v1/protected/dashboard"
echo "- Premium: /api/v1/premium/features, /api/v1/premium/reports"
echo "- Admin: /api/v1/admin/dashboard, /api/v1/admin/users, /api/v1/admin/settings"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run Flask in development mode
flask run
