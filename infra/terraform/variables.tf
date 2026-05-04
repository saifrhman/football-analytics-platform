variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "Default GCP region."
  type        = string
  default     = "europe-west2"
}

variable "bronze_bucket" {
  description = "GCS bucket for raw bronze assets."
  type        = string
}

variable "silver_bucket" {
  description = "GCS bucket for curated silver assets."
  type        = string
}

variable "gold_bucket" {
  description = "GCS bucket for gold data products."
  type        = string
}

variable "bronze_dataset" {
  description = "BigQuery bronze dataset name."
  type        = string
  default     = "football_bronze"
}

variable "silver_dataset" {
  description = "BigQuery silver dataset name."
  type        = string
  default     = "football_silver"
}

variable "gold_dataset" {
  description = "BigQuery gold dataset name."
  type        = string
  default     = "football_gold"
}
