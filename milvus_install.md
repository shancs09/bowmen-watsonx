Install Milvus Stand-alone:

https://milvus.io/docs/install_standalone-docker-compose.md

✅ Prerequisites
1. Operating System: Linux (Redhat, CentOS, etc.)
2. Docker: Installed and running
3. Docker Compose: Installed

# Install Docker
``` bash
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io
sudo yum install -y net-tools
sudo systemctl start docker
sudo systemctl enable docker
```

# Install Docker Compose
``` bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```
   
# Step-by-Step: Install Milvus with Docker Compose

1. Create a working directory
``` bash
mkdir milvus && cd milvus
```
2. Download the Docker Compose file
Milvus provides ready-to-use Docker Compose files. You can download a minimal one:
``` bash
wget https://github.com/milvus-io/milvus/releases/download/v2.5.8/milvus-standalone-docker-compose.yml -O docker-compose.yml
```

3. Start Milvus
```bash
sudo docker compose up -d
```
This will start Milvus in standalone mode (including etcd, MinIO, and Milvus server).

4. Check that it’s running
``` bash
sudo docker compose ps
or
docker ps
```
You should see containers like milvus-standalone, minio, etcd.

# 5. Test the connection (Optional)
Install the Python client to connect:
``` bash
pip install pymilvus
```
Then test with:

from pymilvus import connections
connections.connect("default", host="127.0.0.1", port="19530")

📁 File Structure After Setup
markdown
```
milvus/
├── docker-compose.yml
└── volumes/
    ├── etcd/
    ├── minio/
    └── milvus/
```
🛑 To Stop Milvus
``` bash
docker-compose down
```
# Docker Resource Allocation

🧠 Memory & CPU
Ensure Docker has access to enough memory and CPU:
Minimum: 4 CPU / 8 GB RAM
Recommended: 8+ CPU / 16+ GB RAM for production or heavy workloads
For Docker Desktop:

Go to Docker settings → Resources
Increase Memory and CPUs accordingly
If using Docker Engine (Linux):
```bash
Use --cpus and --memory flags in the docker-compose.yml:
services:
  milvus-standalone:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G

# Storage Tuning (MinIO)

If you're storing large vector datasets, MinIO (object storage) may become a bottleneck.

Allocate more volume space for minio and milvus:
volumes:
  milvus:
    driver: local
    driver_opts:
      o: size=20g
  minio:
    driver: local
    driver_opts:
      o: size=20g
Use external storage (e.g., an NFS mount or SSD-based volume) for performance
```

# Firewall 
``` bash
sudo ufw status
sudo systemctl status firewalld
sudo firewall-cmd --permanent --add-port=22/tcp    # SSH
sudo firewall-cmd --permanent --add-port=8000/tcp  # FastAPI
sudo firewall-cmd --permanent --add-port=8080/tcp  # Optional app port
sudo firewall-cmd --permanent --add-port=19530/tcp # Milvus
sudo firewall-cmd --permanent --add-port=9091/tcp  # Milvus

sudo systemctl start firewalld

sudo firewall-cmd --list-ports
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
```
