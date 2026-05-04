variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "BigQuery dataset location."
  type        = string
}

variable "bronze_dataset" {
  description = "Bronze dataset ID."
  type        = string
}

variable "silver_dataset" {
  description = "Silver dataset ID."
  type        = string
}

variable "gold_dataset" {
  description = "Gold dataset ID."
  type        = string
}
