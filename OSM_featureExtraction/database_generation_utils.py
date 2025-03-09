#!/usr/bin/python3

import argparse
import os
import subprocess
import sys
import time
import urllib.request as r

import psycopg2


def check_db_exists(dbname, db_host="172.18.0.2", db_port="5432"):
    try:
        conn = psycopg2.connect(f"dbname={dbname} host={db_host} port={db_port} user=docker password=docker")
        conn.close()
        return True
    except psycopg2.DatabaseError:
        return False


def reporthook(count, block_size, total_size):
    global start_time
    if count == 0:
        start_time = time.time()
        return
    duration = time.time() - start_time
    progress_size = int(count * block_size)
    speed = int(progress_size / (1024 * duration))
    percent = int(count * block_size * 100 / total_size)
    sys.stdout.write("\r...%d%%, %d MB, %d KB/s, %d seconds passed" %
                     (percent, progress_size / (1024 * 1024), speed, duration))
    sys.stdout.flush()


def download(outfile):
    r.urlretrieve('https://ftp5.gwdg.de/pub/misc/openstreetmap/planet.openstreetmap.org/pbf/planet-latest.osm.pbf',
                  outfile, reporthook)
    return outfile


def download_bbox(outfile, latmin, latmax, lonmin, lonmax):
    r.urlretrieve('https://overpass-api.de/api/map?bbox={},{},{},{}'.format(lonmin, latmin, lonmax, latmax), outfile,
                  reporthook)
    return outfile


def download_panet_osm(path):
    outfile = path + '/planet-latest.osm.pbf'

    if os.path.isfile(outfile):
        print('File {} already exists.'.format(outfile))
        ans = input('Use it? (Y/n')
        if ans == 'n':
            download(outfile)
        elif (ans == 'Y') | (ans == ''):
            sys.exit(0)
        else:
            print('please give valid answer')
            sys.exit(1)
    else:
        download(outfile)

    return outfile


def crop(infile, outfile, latmin, latmax, lonmin, lonmax):
    start = time.time()
    print("Cropping OSM file")
    subprocess.call(["osmconvert", infile, "-b={},{},{},{}".format(lonmin, latmin, lonmax, latmax), "-o={}".format(
        outfile)])
    print("time needed: {} seconds.".format(time.time() - start))


def load_db(infile, dbname, db_host="172.18.0.2", db_port="5432"):
    print("Drop and create DB")
    try:
        conn = psycopg2.connect(dbname="template1", user="docker", password="docker", port=db_port, host=db_host)
    except psycopg2.DatabaseError:
        raise psycopg2.DatabaseError(f'I am unable to connect to the database template1 at {db_host}:{db_port}.')

    cur = conn.cursor()
    conn.set_isolation_level(0)

    cur.execute("""DROP DATABASE IF EXISTS {};""".format(dbname))

    # cur.fetchall()
    cur.execute("""CREATE DATABASE {};""".format(dbname))
    # cur.fetchall()

    cur.close()
    conn.close()

    print("Create extensions")
    try:
        conn_new = psycopg2.connect(dbname=dbname, user="docker", password="docker", port=db_port, host=db_host)
        conn_new.autocommit = True
    except psycopg2.DatabaseError:
        raise psycopg2.DatabaseError(f'I am unable to connect to the database {dbname} at {db_host}:{db_port}.')

    cur_new = conn_new.cursor()

    cur_new.execute("CREATE EXTENSION postgis; CREATE EXTENSION hstore;")

    print("Load data to db: {}".format(infile))
    subprocess.call(["osm2pgsql", "--create", "--database", dbname, "--username", "docker", "--password", "--host", db_host, "--port", db_port, infile])

    print("Creating indexes")
    fd = open('OSM_featureExtraction/table_geography_creation.sql', 'r')
    sql_file = fd.read()
    fd.close()

    sql_commands = sql_file.split('\n')
    for command in sql_commands:
        if command:
            # print(command)
            try:
                cur_new.execute(command)
            except Exception as msg:
                print(msg)
                print("Command skipped: ", command)

    print("Created Tables:")
    table_name = ["planet_osm_polygon", "planet_osm_line", "planet_osm_point"]
    for table in table_name:
        cur_new.execute("SELECT COUNT(*) from {};".format(table))
        print(table + ": {} rows".format(cur_new.fetchone()))

    cur_new.close()
    conn_new.close()


def crop_load(infile, dbname, latmin, latmax, lonmin, lonmax, db_host="172.18.0.2", db_port="5432"):
    outfile = "/".join(infile.split("/")[:-1]) + '/{}.osm.pbf'.format(dbname)
    crop(infile, outfile, latmin, latmax, lonmin, lonmax)
    load_db(outfile, dbname, db_host, db_port)


def create_db(dbname, latmin, latmax, lonmin, lonmax, osmfile=None, rebuild=False, db_host="172.18.0.2", db_port="5432"):
    print(f"DEBUG: Attempting to connect to database at {db_host}:{db_port}")
    exists = check_db_exists(dbname, db_host, db_port)
    if exists:
        print("Database {} already exists".format(dbname))

    if (not exists) | rebuild:
        print("Creating DB for lon: {}/{}, lat: {}/{}".format(lonmin, lonmax, latmin, latmax))
        downloadtime = time.time()
        if not osmfile:
            osmfile = download_bbox("OSM_featureExtraction/OSM-data/{}.osm".format(dbname), latmin - 0.1, latmax + 0.1,
                                    lonmin - 0.1, lonmax + 0.1)
        downloadtime = time.time() - downloadtime

        croploadtime = time.time()
        # cropLoadOSM.cropLoad(osmfile, dbname, latmin-0.1, latmax+0.1, lonmin-0.1, lonmax+0.1)
        load_db(osmfile, dbname, db_host, db_port)
        croploadtime = time.time() - croploadtime
        print("Times needed:\n\tDownload: {}s \n\tcropping and loading: {}s.".format(int(downloadtime),
                                                                                     int(croploadtime)))


def main(infile, dbname, latmin, latmax, lonmin, lonmax, db_host="172.18.0.2", db_port="5432"):
    crop_load(infile, dbname, latmin, latmax, lonmin, lonmax, db_host, db_port)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('infile', type=str, help='.osm.pbf file with OSM data')
    parser.add_argument('dbname', type=str, help='name of the DB (cityname)')
    parser.add_argument('latmin', type=float, help='minimum latitude')
    parser.add_argument('latmax', type=float, help='maximum latitude')
    parser.add_argument('lonmin', type=float, help='minimum longitude')
    parser.add_argument('lonmax', type=float, help='maximum longitude')
    parser.add_argument('--db-host', type=str, help='Database host IP address', default='172.18.0.2')
    parser.add_argument('--db-port', type=str, help='Database port', default='5432')

    args = parser.parse_args()
    starttime = time.time()
    main(args.infile, args.dbname.lower(), args.latmin, args.latmax, args.lonmin, args.lonmax, args.db_host, args.db_port)
    print("total time used: {} seconds".format(time.time() - starttime))