window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, latlng) {
                const zet_icon = feature.properties.route_id < 100 ?
                    L.icon({
                        iconUrl: `/assets/tram.png`,
                        iconSize: [37, 50],
                        iconAnchor: [19, 50]
                    }) :
                    L.icon({
                        iconUrl: `/assets/bus.png`,
                        iconSize: [37, 50],
                        iconAnchor: [19, 50]
                    });

                var marker = L.marker(latlng, {
                    icon: zet_icon
                });

                if (!feature.properties.arrival_time) {

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

            ,
        function1: function(feature, context) {
                return context.props.hideout.includes(feature.properties.route_id);
            }

            ,
        function2: function(feature, layer) {
            layer.bindPopup(feature.properties.route_id);
        }

    }
});