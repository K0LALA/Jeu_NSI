#!/bin/bash
mv worlds.db worlds_.db
sqlite3 worlds_.db .dump > worlds_dump.sql
sqlite3 worlds.db < worlds_dump.sql
rm worlds_.db worlds_dump.sql

