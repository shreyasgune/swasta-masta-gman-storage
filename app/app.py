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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_FILE = os.path.join(SCRIPT_DIR, "client_secret.json")

BUCKET_NAME = "gman-archives"
PREFIX = "Gman-Monu-Pooz-Demos"
SCOPES = ["https://www.googleapis.com/auth/devstorage.read_write"]


def resource_path(filename):
    """Get absolute path to resource."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)


CLIENT_SECRET_FILE = resource_path("client_secret.json")

def get_credentials():
    """Obtain OAuth credentials, refreshing or prompting login if necessary."""
    token_path = os.path.join(os.path.expanduser("~"), "gman_token.json")

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds

def browse_folder():
    folder = filedialog.askdirectory()
    folder_entry.delete(0, tk.END)
    folder_entry.insert(0, folder)

def file_checksum(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def run_sync():
    folder = folder_entry.get()
    if not folder or not os.path.isdir(folder):
        messagebox.showerror("Error", "Please select a valid folder.")
        return

    start_button.config(state="disabled")

    def sync():
        try:
            os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
            creds = get_credentials()
            client = storage.Client(credentials=creds, project="angelic-digit-297517")
            bucket = client.bucket(BUCKET_NAME)

            log_text.insert(tk.END, "Logged in successfully.\n")
            log_text.see(tk.END)

            for root_dir, dirs, files in os.walk(folder):
                for file in files:
                    local_path = os.path.join(root_dir, file)
                    if not os.path.isfile(local_path):
                        continue
                    try:
                        relative_path = os.path.relpath(local_path, folder)
                    except ValueError as e:
                        log_text.insert(tk.END, f"Skipping {local_path}: {e}\n")
                        continue

                    blob_path = f"{PREFIX}/{relative_path}".replace("\\", "/")

                    blob = bucket.get_blob(blob_path)

                    with open(local_path, "rb") as f:
                        local_hash = base64.b64encode(hashlib.md5(f.read()).digest()).decode()

                    if blob is not None and blob.md5_hash is not None:
                        if blob.md5_hash == local_hash:
                            log_text.insert(tk.END, f"Skipping {relative_path}, already up to date.\n")
                            continue

                    blob = bucket.blob(blob_path)
                    log_text.insert(tk.END, f"Uploading {relative_path}...\n")
                    log_text.see(tk.END)
                    blob.upload_from_filename(local_path)

            messagebox.showinfo("Done", "Sync completed!")

        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            start_button.config(state="normal")

    threading.Thread(target=sync, daemon=True).start()

# UI Setup
root = tk.Tk()
root.title("GMAN BACKUP TOOL SUPREME")
root.geometry("600x400")

tk.Label(root, text="Folder:").pack()
folder_entry = tk.Entry(root, width=80)
folder_entry.pack()
tk.Button(root, text="Browse", command=browse_folder).pack()

start_button = tk.Button(root, text="Start Sync", command=run_sync)
start_button.pack(pady=10)

log_text = tk.Text(root)
log_text.pack(fill="both", expand=True)

root.mainloop()