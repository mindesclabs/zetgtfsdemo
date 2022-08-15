from datetime import timedelta, datetime
from airflow import DAG
from airflow.models import Variable
from airflow.operators.python_operator import PythonOperator

from google.transit import gtfs_realtime_pb2
import requests
from protobuf_to_dict import protobuf_to_dict
import pandas as pd
from flatten_json import flatten
import geopandas
from boxsdk import JWTAuth, Client
import os
import json


def parse_zet_feed_data(static_data_path: str, export_path: str):

    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(
        'https://zet.hr/gtfs-rt-protobuf', allow_redirects=True)
    feed.ParseFromString(response.content)

    zet_dict = protobuf_to_dict(feed)

    stops = pd.read_csv(static_data_path+'/stops.txt', sep=',')
    routes = pd.read_csv(static_data_path+'/routes.txt', sep=',')

    zet_df = pd.DataFrame(flatten(record, '.')
                          for record in zet_dict['entity'])
    zet_df = zet_df[['id', 'trip_update.trip.trip_id', 'trip_update.trip.route_id',
                    'trip_update.stop_time_update.0.stop_sequence', 'trip_update.stop_time_update.0.arrival.time',
                     'trip_update.stop_time_update.0.departure.time', 'trip_update.stop_time_update.0.stop_id',
                     'trip_update.stop_time_update.0.departure.delay']]

    zet_df.set_axis(['id', 'trip_id', 'route_id', 'stop_sequence', 'arrival_time', 'departure_time', 'stop_id', 'delay'],
                    axis=1, inplace=True)

    zet_df = zet_df.merge(stops[['stop_id', 'stop_name', 'stop_lat',
                          'stop_lon']], left_on='stop_id', right_on='stop_id', how='left')
    zet_df = zet_df.astype({"route_id": int})
    zet_df = zet_df.merge(routes[['route_id', 'route_long_name']],
                          left_on='route_id', right_on='route_id', how='left')

    zet_df = geopandas.GeoDataFrame(
        zet_df, geometry=geopandas.points_from_xy(zet_df.stop_lon, zet_df.stop_lat))

    zet_df.to_file(export_path+"/zet_feed.json", driver="GeoJSON")

    # export files for populating dropdown:

    df_feed = zet_df[['route_id', 'route_long_name']].drop_duplicates()
    df_feed.loc[df_feed['route_id'] < 100, 'label'] = df_feed['route_id'].astype(str) + \
        ": Tram line " + \
        df_feed["route_long_name"]
    df_feed.loc[df_feed['route_id'] >= 100, 'label'] = df_feed['route_id'].astype(str) + \
        ": Bus line " \
        + df_feed["route_long_name"]

    df_feed.rename(columns={'route_id': 'value'}, inplace=True)

    dd_options = df_feed[['value', 'label']].sort_values(
        by=['value']).to_dict('records')
    dd_defaults = [o["value"] for o in dd_options]

    with open(export_path+'/routes.json', 'w') as f:
        json.dump(dd_options, f)

    with open(export_path+'/route_ids.json', 'w') as f:
        json.dump(dd_defaults, f)


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
    dag_id='zet_feed_data',
    default_args={
        'owner': 'Mladen Dragicevic',
        'depends_on_past': False,
        'start_date': datetime(2022, 1, 1),
        'retries': 0,
    },
    description='Parse and upload new ZET GTFS feed data',
    schedule_interval=timedelta(seconds=15),
    catchup=False
) as dag:

    task_parse_zet_feed_data = PythonOperator(
        task_id='parse_zet_feed_data',
        python_callable=parse_zet_feed_data,
        op_kwargs={
            'static_data_path': '/path/to/exported/zetgtfs/static/folder',
            'export_path': '/path/to/exported/zetgtfs/feed/folder'
        }
    )

    task_upload_to_box = PythonOperator(
        task_id='upload_to_box',
        python_callable=upload_to_box,
        op_kwargs={
            'local_directory': '/path/to/exported/zetgtfs/feed/folder',
            'box_folder': '<box_cloud_folder_id_number>',
            'BOX_JWT_CONFIG': Variable.get("zetgtfs_box_jwt_config")
        }
    )


task_parse_zet_feed_data >> task_upload_to_box
