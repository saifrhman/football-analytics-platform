output "bronze_dataset_id" {
  value = google_bigquery_dataset.bronze.dataset_id
}

output "silver_dataset_id" {
  value = google_bigquery_dataset.silver.dataset_id
}

output "gold_dataset_id" {
  value = google_bigquery_dataset.gold.dataset_id
}
