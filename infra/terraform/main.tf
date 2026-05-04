terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "gcs" {
  source        = "./modules/gcs"
  project_id    = var.project_id
  region        = var.region
  bronze_bucket = var.bronze_bucket
  silver_bucket = var.silver_bucket
  gold_bucket   = var.gold_bucket
}

module "bigquery" {
  source          = "./modules/bigquery"
  project_id      = var.project_id
  region          = var.region
  bronze_dataset  = var.bronze_dataset
  silver_dataset  = var.silver_dataset
  gold_dataset    = var.gold_dataset
}
