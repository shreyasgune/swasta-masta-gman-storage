variable "credentials" {
    type = string
}

variable "project" {
    type = string
}

variable "region" {
    type = string
}

variable "sa_email" {
    type = string
}

provider "google" {
  credentials = var.credentials
  project     = var.project
  region      = var.region
}

resource "google_storage_bucket" "gman_bucket" {
  name          = "gman-bucket"
  location      = "us-central1"
  storage_class = "COLDLINE"
  force_destroy = true
  public_access_prevention = "inherited" #set to "enforced" to block all public access
  uniform_bucket_level_access = true
}

data "google_iam_policy" "allUsers" {
    binding {
        role = "roles/storage.objectViewer"
        members = ["allUsers"]
    }
}

resource "google_storage_bucket_iam_policy" "gman_bucket_policy" {
  bucket = google_storage_bucket.gman_bucket.name
  policy_data = data.google_iam_policy.allUsers.policy_data
}


resource "google_storage_bucket_iam_member" "bucket_iam" {
  bucket = google_storage_bucket.gman_bucket.name
  role   = "roles/storage.admin"
  member = "serviceAccount:${var.sa_email}"
}

# resource "google_service_account" "gman_service_account" {
#   account_id   = "gman-service-account"
#   display_name = "GMAN Service Account"
# }

# resource "google_project_iam_binding" "sa_storage_admin" {
#   project = var.project
#   role    = "roles/storage.admin"

#   members = [
#     "serviceAccount:${google_service_account.gman_service_account.email}",
#   ]
# }