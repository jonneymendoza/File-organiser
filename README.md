# File Organizer Docker Image

## Overview
The **File Organizer** is an automated background service that:
- **Moves or copies files** from a source directory to a destination directory.
- Organizes files by:
  - **File type**: Documents, Images, Music, Executables, Folders, Others.
  - **Modification date**: Organized by Year and Month.
  - **Folder integrity**: Moves entire directories intact, preserving internal folder structures.
- **Supports Multiple Modes**:
  - `copy`: Copies files to the destination while retaining the original.
  - `move`: Moves files to the destination, removing them from the source.
- **Dynamic Permission Control**:
  - Configurable file permissions using `PERMISSIONS` environment variable:
    - `original`: Preserve original permissions
    - `read`: Read-only (`444` for files, `555` for directories)
    - `write`: Read and write (`666` for files, `777` for directories)
    - `full`: Full read, write, and execute (`777` for both)
- **Custom Scheduling**:
  - Runs periodically based on the `SCHEDULE` setting (e.g., every 10 minutes, hourly, daily).
- **Error Notifications via Email**:
  - Sends email notifications if errors occur during file movement.

This Docker image is designed to run on **Linux-based servers** and **Windows 11** using Docker Desktop with **WSL 2**.

---

## Prerequisites
- **Docker** and **Docker Compose** installed on the system.
- On **Windows 11**, ensure:
  - **Docker Desktop** is installed with **WSL 2** integration.
  - Network paths are accessible (e.g., `\\minipc-samba.local\shared-folder`).

---

## Installation and Setup

### Step 1: Clone the Repository
Clone this repository to your local machine:
```sh
git clone https://github.com/your-username/file-organizer.git
cd file-organizer

tep 2: Build the Docker Image
Before you can run the service, you need to build the Docker image using Docker Compose:

sh
Copy
Edit
docker-compose -f file-organiser-compose.yml build
This command builds the Docker image based on the Dockerfile in the current directory.
It prepares the container for running the fileOrganiser.py script.
The image is named fileorganizer:latest by default.
