import os
import shutil
import hashlib
import smtplib
import logging
import time
from email.message import EmailMessage
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load configuration from environment variables
SOURCE_DIR = os.getenv("SOURCE_DIR")
DEST_DIR = os.getenv("DEST_DIR")
MODE = os.getenv("MODE", "copy").lower()  # "move" or "copy"
EMAIL = os.getenv("EMAIL")
SCHEDULE = os.getenv("SCHEDULE", "daily").lower()  # New scheduling variable

# Load permissions setting from environment variable
PERMISSIONS = os.getenv("PERMISSIONS", "original").lower()


# SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

# Define category mapping for file extensions
CATEGORY_MAP = {
    "pdf": "Documents", "doc": "Documents", "docx": "Documents",
    "xls": "Documents", "xlsx": "Documents", "txt": "Documents",
    "jpg": "Images", "jpeg": "Images", "png": "Images", "gif": "Images",
    "mp3": "Music", "wav": "Music", "flac": "Music",
    "exe": "ExecutableWindowsSoftware", "msi": "ExecutableWindowsSoftware",
    "dmg": "ExecutableMac", "pkg": "ExecutableMac", "app": "ExecutableMac",
    "sh": "ExecutableLinux", "deb": "ExecutableLinux", "rpm": "ExecutableLinux"
}

# List to track errors for notification
error_files = []

# Track directories that have been moved
moved_dirs = set()

# Validate environment variables
if not SOURCE_DIR or not DEST_DIR:
    logging.error("Please set SOURCE_DIR and DEST_DIR environment variables.")
    exit(1)

def organize_file(src_path):
    """Organize a single file from source to destination."""
    file_name = os.path.basename(src_path)
    ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
    category = CATEGORY_MAP.get(ext, "Others")

    mod_time = os.path.getmtime(src_path)
    year = datetime.fromtimestamp(mod_time).strftime("%Y")
    month = datetime.fromtimestamp(mod_time).strftime("%B")

    dest_dir = os.path.join(DEST_DIR, year, month, category)
    dest_path = os.path.join(dest_dir, file_name)
    os.makedirs(dest_dir, exist_ok=True)

    if os.path.exists(dest_path):
        dest_mtime = os.path.getmtime(dest_path)
        if dest_mtime >= mod_time:
            logging.info(f"Skipping {src_path} -> {dest_path} (destination is newer or same).")
            return

        if os.path.getsize(dest_path) == os.path.getsize(src_path):
            if compute_hash(src_path) == compute_hash(dest_path):
                logging.info(f"Skipping duplicate {src_path} -> {dest_path} (same content).")
                return
        logging.info(f"Replacing {src_path} with newer version at {dest_path}.")
    else:
        logging.info(f"Organizing {src_path} -> {dest_dir}")

    try:
        if MODE == "move":
            shutil.move(src_path, dest_path)
        else:
            shutil.copy2(src_path, dest_path)
        set_permissions(dest_path)
    except Exception as e:
        error_files.append((src_path, str(e)))
        logging.error(f"Error moving {src_path} to {dest_path}: {e}")

def organize_folder(src_folder):
    """Organize a folder as a whole, keeping its contents intact."""

    # Get the oldest modification date from all files in the folder
    oldest_mod_time = float('inf')
    for root, dirs, files in os.walk(src_folder):
        for name in files:
            file_path = os.path.join(root, name)
            mod_time = os.path.getmtime(file_path)
            if mod_time < oldest_mod_time:
                oldest_mod_time = mod_time

    # If no files are found, use the folder's own modification time
    if oldest_mod_time == float('inf'):
        oldest_mod_time = os.path.getmtime(src_folder)

    # Use the oldest modification date for year and month
    year = datetime.fromtimestamp(oldest_mod_time).strftime("%Y")
    month = datetime.fromtimestamp(oldest_mod_time).strftime("%B")

    folder_name = os.path.basename(src_folder)
    dest_dir = os.path.join(DEST_DIR, year, "Folders")
    dest_path = os.path.join(dest_dir, folder_name)
    os.makedirs(dest_dir, exist_ok=True)

    if os.path.exists(dest_path):
        dest_mtime = os.path.getmtime(dest_path)
        if dest_mtime >= oldest_mod_time:
            logging.info(f"Skipping folder {src_folder} -> {dest_path} (destination is newer or same).")
            moved_dirs.add(src_folder)
            return
        
        logging.info(f"Replacing folder {src_folder} with newer version.")
        shutil.rmtree(dest_path)  # Remove the older version

    logging.info(f"Copying folder {src_folder} -> {dest_dir}")
    try:
        if MODE == "move":
            shutil.move(src_folder, dest_path)
        else:
            shutil.copytree(src_folder, dest_path)
        moved_dirs.add(src_folder)
        set_permissions(dest_path)
    except Exception as e:
        error_files.append((src_folder, str(e)))
        logging.error(f"Error moving folder {src_folder}: {e}")


def compute_hash(file_path, chunk_size=8192):
    """Compute MD5 hash of a file (used to compare file content)."""
    md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                md5.update(chunk)
    except Exception as e:
        return None
    return md5.hexdigest()

def get_sleep_interval():
    """Determine the sleep interval based on the SCHEDULE value."""
    if SCHEDULE == "hourly":
        return 3600   # 1 hour
    elif SCHEDULE == "daily":
        return 86400  # 24 hours
    elif SCHEDULE == "weekly":
        return 604800 # 7 days
    else:
        try:
            return int(SCHEDULE)  # Custom interval in seconds
        except ValueError:
            logging.error("Invalid SCHEDULE value. Falling back to daily.")
            return 86400

def send_error_email():
    """Send an email notification for any errors that occurred."""
    if not error_files or not EMAIL:
        return
    body = "Errors occurred while organizing files:\n"
    for path, err in error_files:
        body += f"- {path}: {err}\n"
    msg = EmailMessage()
    msg['Subject'] = "File Organizer Errors"
    msg['From'] = SMTP_USER
    msg['To'] = EMAIL
    msg.set_content(body)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        logging.info(f"Error report emailed to {EMAIL}.")
    except Exception as e:
        logging.error(f"Failed to send error email: {e}")

def set_permissions(target_path):
    """Set permissions for all files and directories in the target path based on the PERMISSIONS setting."""
    try:
        # Determine the permission mode
        if PERMISSIONS == "original":
            logging.info(f"Preserving original permissions for {target_path}")
            return  # Do nothing, keep original permissions
        elif PERMISSIONS == "read":
            file_mode = 0o444  # Read-only for files
            dir_mode = 0o555   # Read and execute for directories
        elif PERMISSIONS == "write":
            file_mode = 0o666  # Read and write for files
            dir_mode = 0o777   # Read, write, and execute for directories
        elif PERMISSIONS == "full":
            file_mode = 0o777  # Full permissions for files
            dir_mode = 0o777   # Full permissions for directories
        else:
            logging.warning(f"Invalid PERMISSIONS value: {PERMISSIONS}. Using 'original'.")
            return

        # Apply the permissions recursively
        for root, dirs, files in os.walk(target_path):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                os.chmod(dir_path, dir_mode)
            for file_name in files:
                file_path = os.path.join(root, file_name)
                os.chmod(file_path, file_mode)
        
        # Change the root directory itself
        os.chmod(target_path, dir_mode)

        logging.info(f"Permissions set to {PERMISSIONS} for {target_path}")
    except Exception as e:
        logging.error(f"Failed to set permissions for {target_path}: {e}")


if __name__ == "__main__":
    logging.info("Starting File Organizer with internal scheduler.")
    while True:
        logging.info("Starting file organization.")
        for root, dirs, files in os.walk(SOURCE_DIR):
            for name in dirs:
                folder_path = os.path.join(root, name)
                organize_folder(folder_path)

            if any(root.startswith(moved_dir) for moved_dir in moved_dirs):
                logging.info(f"Skipping all files in {root} (directory was moved as a whole).")
                continue

            for name in files:
                file_path = os.path.join(root, name)
                organize_file(file_path)

        send_error_email()

        sleep_interval = get_sleep_interval()
        logging.info(f"Sleeping for {sleep_interval} seconds.")
        time.sleep(sleep_interval)
