import dash_leaflet as dl
from dash import Dash, html, dcc, Output, Input, dash_table
from dash_extensions.javascript import assign
import urllib.request
import json


url = 'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png'
attribution = '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a> '

external_stylesheets = [
    'https://fonts.googleapis.com/css?family=Open Sans',
    'https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css'
]


with urllib.request.urlopen('https://app.box.com/index.php?rm=box_download_shared_file&shared_name=yd7cx7zt8eiu46d8b9wu9x35m3q7hi3n&file_id=f_996278820986') as url_route_ids:
    dd_defaults = json.loads(url_route_ids.read().decode())


# Get icons and popup info:
draw_zet_icon = assign("""
        function(feature, latlng){
            const zet_icon = feature.properties.route_id<100 ? 
                L.icon({iconUrl: `/assets/tram.png`, iconSize: [37, 50], iconAnchor: [19, 50]}) :
                L.icon({iconUrl: `/assets/bus.png`, iconSize: [37, 50], iconAnchor: [19, 50]});

            var marker = L.marker(latlng, {icon: zet_icon});

            if (!feature.properties.arrival_time){

                var local_time = "Not provided"

            } else {

                var date = new Date(parseInt(feature.properties.arrival_time) * 1000);
                local_time = date.toLocaleTimeString("it-IT");

            }

            var zet_tooltip_info = `

                    <table class="zet_tooltip_info">
                    <tr>
                        <th>Route ID:</th>
                        <td>${feature.properties.route_id}</td>
                    </tr>
                    <tr>
                        <th>Route Name:</th>
                        <td>${feature.properties.route_long_name}</td>
                    </tr>
                    <tr>
                        <th>Stop Name:</th>
                        <td>${feature.properties.stop_name}</td>
                    </tr>
                    <tr>
                        <th>Arrival Time:</th>
                        <td>${local_time}</td>
                    </tr>
                    </table>
            `;
        
            return marker.bindTooltip(zet_tooltip_info);
            
        }
""")

# Create javascript function that filters on feature name.
geojson_filter = assign("""
    function(feature, context){
        return context.props.hideout.includes(feature.properties.route_id);
    }
""")


zet_popup_info = assign("""
    function (feature, layer) {
          layer.bindPopup(feature.properties.route_id);
      }
""")

app = Dash(__name__, external_stylesheets=external_stylesheets,
           update_title=None)


app.layout = html.Div([

    html.Div([
        html.Div(children='Near Real-Time ZET Demo Dashboard',
                 id='site_title'),
        html.Div(html.A('__minDesc', href='https://mdlabs.hr/'),
                 id='mdlabs_logo'),
    ], id='header'),

    html.Div([
        html.Div([
            dl.Map(center=[45.8008, 15.99], zoom=12, children=[
                dl.TileLayer(url=url,
                             maxZoom=20,
                             attribution=attribution),

                dl.GeoJSON(url="https://app.box.com/index.php?rm=box_download_shared_file&shared_name=r3t9egzok8iche5celsk0y818gt87smw&file_id=f_996258889860", id="bus_networks",
                           options=dict(style=dict(color="#4682B4", opacity=0.5, weight=2))),
                dl.GeoJSON(url="https://app.box.com/index.php?rm=box_download_shared_file&shared_name=y6uer80zo949e1neg0rdr05hy5xejl1p&file_id=f_996248629232", id="tram_networks",
                           options=dict(style=dict(color="#FFD700", opacity=0.5, weight=2))),
                dl.GeoJSON(id="stops",
                           options=dict(pointToLayer=draw_zet_icon,
                                        filter=geojson_filter),
                           # onEachFeature=zet_popup_info),
                           hideout=dd_defaults,
                           # children=[dl.Popup(id="zet_popup_info")]
                           ),
                dl.LocateControl(options={'locateOptions': {
                                 'enableHighAccuracy': True}})
            ], id="zet_map"),

        ], id='map_container'),
        html.Div([
            dcc.Dropdown(id="dd", value=dd_defaults,
                 clearable=True, multi=True, placeholder='Plese search or select routes...'),
        ], id='info_container'),
    ], id='app_container'),

    html.Div([
        html.Div(['Designed by ',
                  html.A('Minimum Description Labs',
                         href='https://mdlabs.hr/'),
                  ], className='footer_block'),
        html.Div(['Based on ', html.A('Dash', href='https://plotly.com/dash/'), ' by Plotly'],
                 className='footer_block'),
        html.Div(['Open licence data provided by ', html.A('ZET', href='https://www.zet.hr/en')],
                 className='footer_block'),
    ], id='footer'),

    dcc.Interval(
        id='trigger-update',
        interval=15*1000,  # in milliseconds
        n_intervals=0
    )
], id="dash_app")


app.clientside_callback("function(x){return x;}",
                        Output("stops", "hideout"),
                        Input("dd", "value")
                        )


@app.callback([Output('stops', 'data'), Output('dd', 'options')],
              Input('trigger-update', 'n_intervals'))
def update_positions(n):

    with urllib.request.urlopen('https://app.box.com/index.php?rm=box_download_shared_file&shared_name=jajk44mof0ur711q14w7cnvlyfln35wz&file_id=f_996275882578') as url:
        data = json.loads(url.read().decode())

    with urllib.request.urlopen('https://app.box.com/index.php?rm=box_download_shared_file&shared_name=dg23yu0sx5yim92t6lkes6k5l0lj4k6j&file_id=f_996276315784') as url_routes:
        dd_options = json.loads(url_routes.read())

    return data, dd_options


if __name__ == '__main__':
    app.run_server()
