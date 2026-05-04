output "bronze_bucket_name" {
  value = google_storage_bucket.bronze.name
}

output "silver_bucket_name" {
  value = google_storage_bucket.silver.name
}

output "gold_bucket_name" {
  value = google_storage_bucket.gold.name
}
