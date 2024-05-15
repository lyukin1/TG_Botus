#!/bin/bash

export PGUSER="{{ hostvars[inventory_hostname]['DB_USER'] }}"
export PGPASSWORD="{{ hostvars[inventory_hostname]['DB_PASSWORD'] }}"
export PGDATABASE="{{ hostvars[inventory_hostname]['DB_DATABASE'] }}"

psql -c "SELECT 1 FROM pg_database WHERE datname='$PGDATABASE'" | grep -q 1 || psql -c "CREATE DATABASE $PGDATABASE"

psql <<EOSQL
ALTER USER "$PGUSER" WITH PASSWORD '$PGPASSWORD';
DROP ROLE IF EXISTS "{{ hostvars[inventory_hostname]['DB_REPL_USER'] }}";
CREATE ROLE "{{ hostvars[inventory_hostname]['DB_REPL_USER'] }}" WITH REPLICATION LOGIN PASSWORD '{{ hostvars[inventory_hostname]['DB_REPL_PASSWORD'] }}';
CREATE TABLE IF NOT EXISTS phone (Phone_id SERIAL PRIMARY KEY, phone_number VARCHAR(18) NOT NULL);
CREATE TABLE IF NOT EXISTS mail (Mail_id SERIAL PRIMARY KEY, name_mail VARCHAR(255) NOT NULL);
INSERT INTO phone (phone_number) VALUES ('+7 (123) 456 78 90');
INSERT INTO mail (name_mail) VALUES ('test@test.com');
EOSQL

unset PGUSER PGPASSWORD PGDATABASE