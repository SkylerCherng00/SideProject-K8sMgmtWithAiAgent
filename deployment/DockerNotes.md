# Project Documentation for PrjAPI

## Tutorial to Deploy loki_api and prometheus_api

1. **Create Dockerfiles**: Ensure the Dockerfiles in both `loki` and `prom` directories are correctly set up to build the respective APIs.

2. **Create docker-compose.yml**: Create a `docker-compose.yml` file in the `PrjAPI` directory

3. **Build and Run the Services**: Open a terminal in the `PrjAPI` directory and run the following command to build and start the services:
```bash
# Force rebuild of images before starting, run in foreground
# After Dockerfile or code changes, development
docker compose up --build

# Deploy updates silently in background
docker compose up -d --build

# Build (if needed), create, start, attach, run in foreground
docker compose up

# Same as above, but run in background (detached)
docker compose up -d

# Run a one-time command in a new container
## Does not expose service ports by default
docker compose run

```

4. **Access the APIs**: Once the services are running, you can access the Loki API at `http://localhost:10001/loki` and the Prometheus API at `http://localhost:10002/prom`.

5. **Check Logs**: You can view the logs of the services in the terminal where you ran the `docker compose` command.

6. **Stop the Services**: To stop the services, press `Ctrl+C` in the terminal or run:
```bash
docker compose down
```

7. **Renew the image**
- upgrade the image with the same tag
```bash
# Upgrade, this command will create new images
docker compose build

# Start up
docker compose up

# Prune old images
docker image prune
```

8. About the configuration about `llm_client`
- One of the tool use ssh in the jumper server for query the condition about K8s.
- Therefore, the `llm_client` container have to use passwordless between container and jumper server
- The following shows the steps to create key exchange bewteen container and jumper server
```bash
# Use sh to login container
docker exec -it prjapi_llmclient sh

# Generate ssh private key
ssh-keygen

# Public key exchange bewteen jump server and container
ssh-copy-id <username>@jumpserver
```

### Debug
- Login to container
```bash
# login to the container with sh and check the environment
docker compose run --rm loki sh
```
- About restart policy
  - no: Do not restart automatically (default)
  - on-failure: Restart only if the container exits with a non-zero status
  - unless-stopped: Restart always except if stopped manually
  - always: Always restart the container regardless of exit status
```bash
# Check the current restart policy of a container
docker inspect <container_name_or_id>

# Look for the "RestartPolicy" section in the output to see the current policy
docker inspect --format='{{.HostConfig.RestartPolicy.Name}}' <container_name_or_id>

# Example: To set a container to always restart
docker update --restart=always <container_name_or_id>
```

### Additional Notes
- Ensure Docker and Docker Compose are installed on your machine.
- Modify the configuration files as needed to point to the correct Prometheus and Loki server URLs.
- The APIs can be further tested using tools like Postman or curl.