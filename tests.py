#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import docker
import requests

client = docker.from_env()

# Testing Symfony build

for c in client.containers.list():
    print("{}: {}".format(c.name, c.status))
    if c.status != 'running':
        print(c.logs())

time.sleep(20)  # we expect all containers are up and running in 20 secs

# NGINX
nginx = client.containers.get('nginx')
nginx_cfg = nginx.exec_run("/usr/sbin/nginx -T")
assert nginx.status == 'running'
assert 'server_name localdomain;' in nginx_cfg.output.decode()
assert "error_log /proc/self/fd/2" in nginx_cfg.output.decode()
assert "location = /.well-known/acme-challenge/" in nginx_cfg.output.decode()
assert 'HTTP/1.1" 500' not in nginx.logs()

# test restart
nginx.restart()
time.sleep(3)
assert nginx.status == 'running'

# Kibana
kibana = client.containers.get('kibana')
assert kibana.status == 'running'
response = requests.get("http://127.0.0.1:5601")
assert response.status_code == 200
assert "var hashRoute = '/app/kibana'" in response.text
assert 'Server running at http://0.0.0.0:5601' in kibana.logs()

# Logstash
logstash = client.containers.get('logstash')
assert logstash.status == 'running'
assert 'Successfully started Logstash API endpoint {:port=>9600}' in logstash.logs()
assert 'Starting input listener {:address=>"0.0.0.0:5044"}' in logstash.logs()
assert 'Pipeline main started' in logstash.logs()

# Elasticsearch
elastic = client.containers.get('elasticsearch')
assert elastic.status == 'running'
response = requests.get("http://127.0.0.1:9200")
assert response.status_code == 200
assert '"number" : "5.4.3"' in response.text
assert ' bound_addresses {0.0.0.0:9200}' in elastic.logs()

# Symfony PHP
php = client.containers.get('php')
php_log = php.logs()
assert php.status == 'running'
php_conf = php.exec_run("php-fpm -t")
assert 'configuration file /usr/local/etc/php-fpm.conf test is successful' in php_conf.output.decode()
php_proc = php.exec_run("sh -c 'ps aux |grep php-fpm'")
assert 'php-fpm: master process (/usr/local/etc/php-fpm.conf)' in php_proc.output.decode()
assert 'fpm is running, pid' in php.logs()

redis = client.containers.get('redis')
assert redis.status == 'running'
redis_cli = redis.exec_run("redis-cli ping")
assert 'PONG' in redis_cli.output.decode()
redis_log = redis.logs()
assert "Ready to accept connections" in redis_log.decode()

mysql = client.containers.get('db')
assert mysql.status == 'running'
mycnf = mysql.exec_run("/usr/sbin/mysqld --verbose  --help")
assert '/usr/sbin/mysqld  Ver 5.7.26' in mycnf.output.decode()
mysql_log = mysql.logs()
assert "mysqld: ready for connections." in mysql_log.decode()

# db = client.containers.get('db')
# assert db.status == 'running'
# cnf = db.exec_run('psql -U sylius -h 127.0.0.1 -p 5432 -c "select 1"')
# log = db.logs()
# assert '(1 row)' in cnf.output.decode()

mq = client.containers.get('mq')
assert mq.status == 'running'
logs = mq.logs()
assert 'Server startup complete; 3 plugins started' in logs.decode()

response = requests.get("http://localdomain/")
assert response.status_code == 200
assert '<title>Sylius</title>' in response.text
