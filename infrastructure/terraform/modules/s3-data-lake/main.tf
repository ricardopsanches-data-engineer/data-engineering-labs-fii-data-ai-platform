resource "aws_s3_bucket" "data_lake" {
  bucket        = var.bucket_name
  force_destroy = var.force_destroy

  tags = merge(
    {
      Name        = var.bucket_name
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    },
    var.tags
  )
}

resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  depends_on = [
    aws_s3_bucket_versioning.data_lake
  ]

  rule {
    id     = "expire-raw-b3"
    status = "Enabled"

    filter {
      prefix = "raw/b3/"
    }

    expiration {
      days = var.raw_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.raw_noncurrent_retention_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = var.incomplete_multipart_retention_days
    }
  }

  rule {
    id     = "expire-raw-cvm"
    status = "Enabled"

    filter {
      prefix = "raw/cvm/"
    }

    expiration {
      days = var.raw_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.raw_noncurrent_retention_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = var.incomplete_multipart_retention_days
    }
  }

  rule {
    id     = "expire-raw-b3-instruments"
    status = "Enabled"

    filter {
      prefix = "raw/b3-instruments/"
    }

    expiration {
      days = var.raw_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.raw_noncurrent_retention_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = var.incomplete_multipart_retention_days
    }
  }
}