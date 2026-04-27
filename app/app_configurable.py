import tkinter as tk
from tkinter import filedialog, messagebox
import os
import threading
import hashlib
import json
import base64
import sys

from google.cloud import storage
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/devstorage.read_write"]

# Configuration storage
config = {
    "bucket_name": "",
    "credentials_file": "",
    "upload_prefix": ""
}

def resource_path(filename):
    """Get absolute path to resource."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

def browse_credentials():
    """Browse and select credentials JSON file."""
    file = filedialog.askopenfilename(
        title="Select Google Cloud Credentials JSON",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if file:
        credentials_entry.delete(0, tk.END)
        credentials_entry.insert(0, file)
        config["credentials_file"] = file

def browse_folder():
    """Browse and select folder to upload."""
    folder = filedialog.askdirectory(title="Select Folder to Upload")
    if folder:
        folder_entry.delete(0, tk.END)
        folder_entry.insert(0, folder)

def validate_config():
    """Validate all configuration inputs."""
    bucket_name = bucket_entry.get().strip()
    credentials_file = credentials_entry.get().strip()
    upload_prefix = prefix_entry.get().strip()
    folder = folder_entry.get().strip()
    
    if not bucket_name:
        messagebox.showerror("Error", "Please enter a bucket name.")
        return False
    
    if not credentials_file or not os.path.isfile(credentials_file):
        messagebox.showerror("Error", "Please select a valid credentials JSON file.")
        return False
    
    if not upload_prefix:
        messagebox.showerror("Error", "Please enter an upload path prefix.")
        return False
    
    if not folder or not os.path.isdir(folder):
        messagebox.showerror("Error", "Please select a valid folder to upload.")
        return False
    
    config["bucket_name"] = bucket_name
    config["credentials_file"] = credentials_file
    config["upload_prefix"] = upload_prefix
    
    return True

def get_credentials():
    """Obtain OAuth credentials, refreshing or prompting login if necessary."""
    token_path = os.path.join(os.path.expanduser("~"), "gman_token.json")

    creds = None
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(config["credentials_file"], SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds

def run_sync():
    """Validate config and start sync process."""
    if not validate_config():
        return

    start_button.config(state="disabled")
    folder = folder_entry.get()

    def sync():
        try:
            os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
            creds = get_credentials()
            client = storage.Client(credentials=creds)
            bucket = client.bucket(config["bucket_name"])

            log_text.insert(tk.END, f"Logged in successfully.\n")
            log_text.insert(tk.END, f"Bucket: {config['bucket_name']}\n")
            log_text.insert(tk.END, f"Upload prefix: {config['upload_prefix']}\n")
            log_text.insert(tk.END, "Starting sync...\n\n")
            log_text.see(tk.END)
            root.update()

            for root_dir, dirs, files in os.walk(folder):
                for file in files:
                    local_path = os.path.join(root_dir, file)
                    if not os.path.isfile(local_path):
                        continue
                    
                    try:
                        relative_path = os.path.relpath(local_path, folder)
                    except ValueError as e:
                        log_text.insert(tk.END, f"Skipping {local_path}: {e}\n")
                        log_text.see(tk.END)
                        root.update()
                        continue

                    blob_path = f"{config['upload_prefix']}/{relative_path}".replace("\\", "/")

                    blob = bucket.get_blob(blob_path)

                    with open(local_path, "rb") as f:
                        local_hash = base64.b64encode(hashlib.md5(f.read()).digest()).decode()

                    if blob is not None and blob.md5_hash is not None:
                        if blob.md5_hash == local_hash:
                            log_text.insert(tk.END, f"Skipping {relative_path}, already up to date.\n")
                            log_text.see(tk.END)
                            root.update()
                            continue

                    blob = bucket.blob(blob_path)
                    log_text.insert(tk.END, f"Uploading {relative_path}...\n")
                    log_text.see(tk.END)
                    root.update()
                    blob.upload_from_filename(local_path)

            log_text.insert(tk.END, "\nSync completed successfully!\n")
            log_text.see(tk.END)
            messagebox.showinfo("Done", "Sync completed!")

        except Exception as e:
            log_text.insert(tk.END, f"\nError: {str(e)}\n")
            log_text.see(tk.END)
            messagebox.showerror("Error", str(e))
        finally:
            start_button.config(state="normal")

    threading.Thread(target=sync, daemon=True).start()

# UI Setup
root = tk.Tk()
root.title("GMAN BACKUP TOOL - CONFIGURABLE")
root.geometry("700x600")

# Bucket Name
tk.Label(root, text="Google Cloud Bucket Name:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
bucket_entry = tk.Entry(root, width=80)
bucket_entry.pack(padx=10, pady=(0, 10))

# Credentials File
tk.Label(root, text="Credentials JSON File:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
credentials_frame = tk.Frame(root)
credentials_frame.pack(padx=10, pady=(0, 10), fill="x")
credentials_entry = tk.Entry(credentials_frame, width=60)
credentials_entry.pack(side="left", fill="x", expand=True)
tk.Button(credentials_frame, text="Browse", command=browse_credentials).pack(side="left", padx=(5, 0))

# Upload Path Prefix
tk.Label(root, text="Upload Path Prefix:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
prefix_entry = tk.Entry(root, width=80)
prefix_entry.pack(padx=10, pady=(0, 10))

# Source Folder
tk.Label(root, text="Source Folder to Upload:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
folder_frame = tk.Frame(root)
folder_frame.pack(padx=10, pady=(0, 10), fill="x")
folder_entry = tk.Entry(folder_frame, width=60)
folder_entry.pack(side="left", fill="x", expand=True)
tk.Button(folder_frame, text="Browse", command=browse_folder).pack(side="left", padx=(5, 0))

# Start Button
start_button = tk.Button(root, text="Start Sync", command=run_sync, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"))
start_button.pack(pady=10)

# Log Display
tk.Label(root, text="Sync Log:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
log_text = tk.Text(root, height=15)
log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

root.mainloop()
