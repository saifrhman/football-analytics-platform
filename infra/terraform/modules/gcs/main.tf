resource "google_storage_bucket" "bronze" {
  name                        = var.bronze_bucket
  location                    = var.region
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "silver" {
  name                        = var.silver_bucket
  location                    = var.region
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "gold" {
  name                        = var.gold_bucket
  location                    = var.region
  uniform_bucket_level_access = true
}
