#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$DB_USER" --dbname "$DB_DATABASE" <<-EOSQL
    ALTER USER "$DB_USER" WITH PASSWORD '$DB_PASSWORD';
    CREATE ROLE $DB_REPL_USER WITH REPLICATION LOGIN PASSWORD '$DB_REPL_PASSWORD';
    CREATE TABLE phone (Phone_id SERIAL PRIMARY KEY, phone_number VARCHAR(18) NOT NULL);
    CREATE TABLE mail (Mail_id SERIAL PRIMARY KEY, name_mail VARCHAR(255) NOT NULL);
    INSERT INTO phone (phone_number) VALUES ('+7 (123) 456 78 90');
    INSERT INTO mail (name_mail) VALUES ('test@test.com');
EOSQL

echo "host replication ${DB_REPL_USER} ${DB_REPL_HOST}/24 md5" >> /var/lib/postgresql/data/pg_hba.conf

exec "$@"