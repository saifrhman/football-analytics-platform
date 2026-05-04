resource "google_bigquery_dataset" "bronze" {
  dataset_id = var.bronze_dataset
  location   = var.region
}

resource "google_bigquery_dataset" "silver" {
  dataset_id = var.silver_dataset
  location   = var.region
}

resource "google_bigquery_dataset" "gold" {
  dataset_id = var.gold_dataset
  location   = var.region
}
