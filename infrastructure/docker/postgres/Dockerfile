# syntax=docker/dockerfile:1
# PostGIS *and* pgvector in one image.
#
# The stock postgis/postgis image ships PostGIS only, so init.sql's
# `CREATE EXTENSION vector` aborted the entrypoint and the container never
# became healthy — which took every service that depends_on it down with it.
# pgvector comes from the same PGDG repo the base image already configures.
FROM postgis/postgis:16-3.4

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*
