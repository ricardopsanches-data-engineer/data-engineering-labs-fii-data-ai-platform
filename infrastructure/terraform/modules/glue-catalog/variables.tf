variable "database_name" {
  description = "Name of the AWS Glue Data Catalog database."
  type        = string
}

variable "data_lake_bucket_name" {
  description = "Name of the S3 bucket containing the Data Lake."
  type        = string
}

variable "b3_table_name" {
  description = "Name of the Glue Catalog table for B3 Silver data."
  type        = string
  default     = "b3_trades"
}

variable "tags" {
  description = "Tags applied to Glue resources where supported."
  type        = map(string)
  default     = {}
}