#!/bin/bash

# Log in and append bind address to last line in /etc/my.cnf
# LINE='include "/configs/projectname.conf"'
# LINE='bind-address = 0.0.0.0'
# FILE=/etc/my.cnf
# grep -qF -- "$LINE" "$FILE" || echo "$LINE" >> "$FILE"

# Change the password
# https://www.howtoforge.com/setting-changing-resetting-mysql-root-passwords
# run the mysql docker command with -e MYSQL_ROOT_PASSWORD=root
# "$MYSQL_ROOT_PASSWORD" -a -z "$MYSQL_ALLOW_EMPTY_PASSWORD
# mysqladmin -u root -p password root

# sed -i -e "\$abind-address = 0.0.0.0" /etc/my.cnf
# https://unix.stackexchange.com/questions/20573/sed-insert-text-after-the-last-line
# https://stackoverflow.com/questions/9591744/how-to-add-to-the-end-of-lines-containing-a-pattern-with-sed-or-awk
tail -F /entrypoint.sh
docker create --rm -e MYSQL_ROOT_PASSWORD=root --name=mysql1 -p 3307:3306 -p 33060:33060 -d mysql/mysql-server:latest
docker cp my.cnf mysql1:/etc/my.cnf
docker start mysql1
