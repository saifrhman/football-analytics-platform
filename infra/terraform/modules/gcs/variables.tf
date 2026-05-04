variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCS bucket location."
  type        = string
}

variable "bronze_bucket" {
  description = "Bronze bucket name."
  type        = string
}

variable "silver_bucket" {
  description = "Silver bucket name."
  type        = string
}

variable "gold_bucket" {
  description = "Gold bucket name."
  type        = string
}
