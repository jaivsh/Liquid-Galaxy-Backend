from flask import Flask, request, jsonify, Response
import ee
import json

# Initialize Earth Engine
service_account = 'acc-1-liquid-galaxy@accenture-hackathon-457015.iam.gserviceaccount.com'
key_path = 'key.json'
credentials = ee.ServiceAccountCredentials(service_account, key_path)
ee.Initialize(credentials)

app = Flask(__name__)

def json_to_kml(features, max_features=10):
    kml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '  <Document>',
        '    <Style id="buildingStyle">',
        '      <LineStyle><color>ff0000ff</color><width>2</width></LineStyle>',
        '      <PolyStyle><color>7d00ff00</color></PolyStyle>',
        '    </Style>'
    ]

    def add_polygon(coords):
        kml.append('    <Polygon>')
        kml.append('      <altitudeMode>clampToGround</altitudeMode>')
        kml.append('      <outerBoundaryIs>')
        kml.append('        <LinearRing>')
        kml.append('          <coordinates>')
        for lng, lat in coords:
            kml.append(f'            {lng},{lat},0')
        kml.append('          </coordinates>')
        kml.append('        </LinearRing>')
        kml.append('      </outerBoundaryIs>')
        kml.append('    </Polygon>')

    for feat in features[:max_features]:
        geom = feat.get('geometry', {})
        props = feat.get('properties', {})
        conf = props.get('confidence', 'N/A')

        kml.append('  <Placemark>')
        kml.append('    <styleUrl>#buildingStyle</styleUrl>')
        kml.append(f'    <name>Confidence: {conf}</name>')

        if geom.get('type') == 'Polygon':
            add_polygon(geom['coordinates'][0])
        elif geom.get('type') == 'MultiPolygon':
            for poly in geom['coordinates']:
                add_polygon(poly[0])

        kml.append('  </Placemark>')

    kml.append('  </Document>')
    kml.append('</kml>')
    return "\n".join(kml)

@app.route('/fetch-buildings', methods=['GET'])
def fetch_buildings():
    try:
        # Read bounding box and output format
        min_lng = float(request.args['min_lng'])
        min_lat = float(request.args['min_lat'])
        max_lng = float(request.args['max_lng'])
        max_lat = float(request.args['max_lat'])
        fmt = request.args.get('format', 'kml').lower()

        # Query Earth Engine
        region = ee.Geometry.Rectangle([min_lng, min_lat, max_lng, max_lat])
        col = (ee.FeatureCollection("GOOGLE/Research/open-buildings/v3/polygons")
               .filterBounds(region)
               .limit(50)
               .select(['lowpoly', 'confidence']))
        features = col.getInfo()['features']

        # If user requests KML
        if fmt == 'kml':
            kml_str = json_to_kml(features)
            return Response(kml_str, mimetype='application/vnd.google-earth.kml+xml')

        # Return JSON by default
        fc = {"type": "FeatureCollection", "features": features}
        return jsonify(fc)

    except Exception as e:
        return Response(f"Error: {e}", status=500, mimetype='text/plain')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
