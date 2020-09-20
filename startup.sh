#!/bin/sh
gunicorn --workers 4 --threads 4 --bind 0.0.0.0:8080 wsgi:app