from datetime import timedelta, datetime
from airflow import DAG
from airflow.models import Variable
from airflow.operators.python_operator import PythonOperator

import requests
from bs4 import BeautifulSoup
import zipfile
import io
import os
from pyrosm import get_data, OSM
import pandas as pd
import re
import geopandas
from boxsdk import JWTAuth, Client


def download_zet_static_data(local_path: str, ti):

    ti.xcom_push(key='local_path_zet_files', value=local_path)

    url = "https://zet.hr/gtfs2"

    reqs = requests.get(url)
    soup = BeautifulSoup(reqs.text, 'html.parser')
    zet_latest_static_url = 'https://zet.hr' + \
        soup.find('a', text='GTFS Static Data Latest')['href']

    reqs = requests.get(zet_latest_static_url, allow_redirects=True)
    z = zipfile.ZipFile(io.BytesIO(reqs.content))
    z.extractall(local_path)

    return 'ZET static GTFS data downloaded to ' + local_path


def download_osm_static_data(city: str, local_path: str, ti):
    fp = get_data(city, directory=local_path)
    ti.xcom_push(key='osm_data', value=fp)
    return 'OSM data for ' + city + ' downloaded to ' + local_path


def parse_zet_data(export_path: str, ti):

    # Get the data:
    temp_folder = ti.xcom_pull(key='local_path_zet_files',
                               task_ids='download_zet_static_data')

    routes = pd.read_csv(temp_folder + '/routes.txt', sep=',')
    osm = OSM(ti.xcom_pull(key='osm_data', task_ids='download_osm_static_data'))

    # Parse it:

    tram_net = osm.get_data_by_custom_criteria({"railway": ["tram"]})

    bus_net = osm.get_data_by_custom_criteria({"route": ["bus"]})
    bus_net = bus_net[bus_net['network'] == 'ZET']
    bus_net['bus_line'] = bus_net['tags'].apply(
        lambda x: int(re.search('\d+', x).group()))
    rj = routes.merge(bus_net, left_on='route_id', right_on='bus_line',
                      how='left').drop_duplicates(subset='route_id', keep="first")
    bus_net = rj[~rj['from'].isna()]

    # Export it:

    tram_net['geometry'].to_file(
        export_path+"/tram_net.json", driver="GeoJSON")

    geopandas.GeoDataFrame(bus_net['geometry'],
                           geometry=bus_net.geometry).to_file(export_path+"/bus_net.json", driver="GeoJSON")

    os.system('cp ' + temp_folder + '/routes.txt ' +
              export_path + '/routes.txt')

    os.system('cp ' + temp_folder + '/stops.txt ' + export_path + '/stops.txt')

    # Clean the temp folder:

    os.system('rm -r ' + temp_folder)

    return 'ZET static data parsed and exporeted to: ' + export_path


def upload_to_box(local_directory: str, box_folder: str, BOX_JWT_CONFIG: str):

    config = JWTAuth.from_settings_file(BOX_JWT_CONFIG)
    client = Client(config)

    for filename in os.listdir(local_directory):

        items = client.search().query(query=f'"{filename}"',
                                      file_extensions=['json'],
                                      content_types=['name'],
                                      ancestor_folder_ids=[box_folder])
        for item in items:
            client.file(item.id).update_contents(
                os.path.join(local_directory, filename))

    return 'Files uploaded to Box account'


with DAG(
    dag_id='zet_static_data',
    default_args={
        'owner': 'Mladen Dragicevic',
        'depends_on_past': False,
        'start_date': datetime(2022, 1, 1),
        'retries': 1,
        'retry_delay': timedelta(minutes=1)
    },
    description='Parse and upload new ZET GTFS static data',
    schedule_interval=timedelta(days=1),
    catchup=False
) as dag:

    task_download_zet_static_data = PythonOperator(
        task_id='download_zet_static_data',
        python_callable=download_zet_static_data,
        op_kwargs={
            'local_path': '/path/to/temp/donwload/folder'
        }
    )

    task_download_osm_static_data = PythonOperator(
        task_id='download_osm_static_data',
        python_callable=download_osm_static_data,
        op_kwargs={
            'city': 'zagreb',
            'local_path': '/path/to/temp/donwload/folder'
        }
    )

    task_parse_zet_data = PythonOperator(
        task_id='parse_zet_data',
        python_callable=parse_zet_data,
        op_kwargs={
            'export_path': '/path/to/exported/zetgtfs/static/folder'
        }
    )

    task_upload_to_box = PythonOperator(
        task_id='upload_to_box',
        python_callable=upload_to_box,
        op_kwargs={
            'local_directory': '/path/to/exported/zetgtfs/static/folder',
            'box_folder': '<box_cloud_folder_id_number>',
            'BOX_JWT_CONFIG': Variable.get("zetgtfs_box_jwt_config")
        }
    )


task_download_zet_static_data >> task_download_osm_static_data \
    >> task_parse_zet_data >> task_upload_to_box
