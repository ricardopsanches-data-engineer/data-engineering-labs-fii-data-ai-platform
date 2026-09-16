variable "workgroup_name" {
  description = "Name of the Athena workgroup."
  type        = string
}

variable "database_name" {
  description = "Glue Data Catalog database used by Athena."
  type        = string
}

variable "data_lake_bucket_name" {
  description = "S3 bucket containing the Data Lake and Athena query results."
  type        = string
}

variable "data_lake_bucket_arn" {
  description = "ARN of the S3 Data Lake bucket."
  type        = string
}

variable "query_results_prefix" {
  description = "S3 prefix used to store Athena query results."
  type        = string
  default     = "athena-results"
}

variable "bytes_scanned_cutoff_per_query" {
  description = "Maximum number of bytes a single Athena query can scan."
  type        = number
  default     = 1073741824
}

variable "tags" {
  description = "Tags applied to Athena resources."
  type        = map(string)
  default     = {}
}