# Setup Guide
- download map data from https://download.geofabrik.de
   - wget https://download.geofabrik.de/north-america/us/massachusetts-latest.osm.pbf
### Unpack the map data
```bash
docker run -t -v ./data:/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/massachusetts-latest.osm.pbf
docker run -t -v "./data:/data" osrm/osrm-backend osrm-partition /data/massachusetts-latest.osm.pbf
docker run -t -v "./data:/data" osrm/osrm-backend osrm-customize /data/massachusetts-latest.osm.pbf
```
### Run the server
docker run  -dt -p 5001:5000 -v ./data:/data osrm/osrm-backend osrm-routed --algorithm mld /data/massachusetts-latest.osm.pbf

### Run the frontend
## Not needed for creating distance matrix
docker run -d -p 9966:9966 -e OSRM_BACKEND='http://localhost:5001' ghcr.io/project-osrm/osrm-frontend:latest

### Run Geocoding server
docker pull mediagis/nominatim:5.2
docker run -it -v ./data:/data \
  -e PBF_PATH=/data/massachusetts-latest.osm.pbf \
  -p 8080:8080 \
  --name nominatim \
  mediagis/nominatim:5.2

### Run VROOM server
docker run -dt --name vroom \
    --net host \
    -p 3000:3000 \
    -v ./conf:/conf \
    -e VROOM_ROUTER=osrm \
    ghcr.io/vroom-project/vroom-docker:v1.14.0
docker logs -f <contain>
docker ps
docker stop <container>
