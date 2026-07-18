#!/bin/bash

docker compose exec -T postgres psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'test_production_control'" | grep -q 1 || \
docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE test_production_control;"

docker compose exec -T -e TEST_DB_HOST=postgres api pytest
