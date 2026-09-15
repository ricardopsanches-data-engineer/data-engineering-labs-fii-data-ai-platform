# Phase 2 — AWS Data Lake Foundation Closure

Phase 2 established the cloud Data Lake and the first production-style serverless ingestion and transformation workflows of the FII Data & AI Platform.

The phase moved the project from a local engineering foundation into an AWS-based data platform with versioned storage, automated ingestion, event-driven processing, observability and auditable execution.

---

# Scope

Phase 2 includes:

```text
Amazon S3 Data Lake
RAW data ingestion
B3 ingestion
CVM ingestion
Scheduled serverless ingestion
AWS Lambda
Amazon ECR
B3 RAW to Silver transformation
Parquet Silver datasets
S3 event-driven processing
Idempotency
SHA-256 validation
S3 versioning
CloudWatch logs
CloudWatch metrics
CloudWatch dashboard
Operational observability scripts
Terraform-managed infrastructure

Phase 2 explicitly excludes:

AWS Glue Data Catalog
Amazon Athena
Gold analytical datasets
Apache Iceberg
Advanced orchestration
Airflow / MWAA
Advanced data quality framework
Machine Learning infrastructure
Generative AI infrastructure

These capabilities belong to later phases.

Data Lake

Primary Data Lake bucket:

fii-data-ai-platform-dev-datalake-625685670804

Primary region:

sa-east-1

Main logical layers:

raw/
silver/
gold/

Current active layers:

RAW
SILVER

The GOLD layer is reserved for future analytical datasets.

RAW Layer

RAW ingestion currently supports:

B3
CVM

Partitioning pattern:

raw/<source>/year=YYYY/month=MM/day=DD/

Example:

raw/b3/year=2026/month=09/day=14/

RAW data is preserved as close as possible to its source representation.

The RAW layer is treated as an immutable historical foundation.

Daily Ingestion

Daily ingestion Lambda:

fii-data-ai-platform-dev-daily-ingestion

Primary responsibilities:

B3 ingestion
CVM ingestion
RAW S3 storage
metadata validation
SHA-256 comparison
idempotent upload behavior

The Lambda runs using:

Python 3.12
AWS Lambda
Amazon S3
CloudWatch Logs
Scheduling

Daily ingestion is scheduled with:

Amazon EventBridge Scheduler

Schedule:

MON-FRI
07:00
America/Sao_Paulo

The scheduler invokes the daily ingestion Lambda automatically.

Retry behavior is enabled.

B3 RAW to Silver Pipeline

B3 RAW objects are transformed into Parquet Silver datasets.

Flow:

B3 RAW ZIP
    |
    v
S3 RAW
    |
    v
S3 ObjectCreated Event
    |
    v
B3 RAW to Silver Lambda
    |
    v
Parse B3 XML
    |
    v
Validated DataFrame
    |
    v
Parquet
    |
    v
S3 SILVER

Silver partitioning:

silver/b3/year=YYYY/month=MM/day=DD/

Output file:

b3_trades.parquet
B3 Silver Lambda

Lambda:

fii-data-ai-platform-dev-b3-raw-to-silver

Deployment model:

Container image
Amazon ECR
AWS Lambda

Architecture:

x86_64

Timeout:

120 seconds

Final configured memory:

1536 MB

The Lambda processes S3 events automatically.

Amazon ECR

Repository:

fii-data-ai-platform-dev-b3-silver

Image tags are immutable.

Container builds use:

linux/amd64

The Lambda currently uses a validated container release built specifically for AWS Lambda compatibility.

Idempotency

The platform implements idempotent storage behavior using SHA-256 fingerprints.

Behavior:

Object absent
→ upload

Object exists with same SHA-256
→ skip

Object exists with different SHA-256
→ block unless explicit force/reprocessing is requested

This prevents silent overwrite of historical data.

S3 Versioning

The Data Lake bucket has S3 versioning enabled.

This provides:

historical object versions
auditability
recovery capability
controlled reprocessing
protection against accidental overwrite

Delete operations create delete markers rather than immediately destroying historical versions.

Observability

Operational observability uses:

CloudWatch Logs
CloudWatch Metrics
CloudWatch Dashboard
PowerShell operational scripts

Dashboard:

fii-data-ai-platform-dev

The dashboard monitors:

Daily Ingestion Lambda

- Invocations
- Errors
- Throttles
- Duration
- Error Rate

B3 RAW to Silver Lambda

- Invocations
- Errors
- Throttles
- Duration
- Error Rate
Operational Scripts

Primary observability scripts include:

scripts/check_daily_ingestion.ps1
scripts/check_lambda_metrics.ps1
scripts/check_ingestion_observability.ps1
scripts/check_b3_silver_observability.ps1

The B3 Silver observability script evaluates:

Lambda state
configured memory
timeout
latest execution duration
maximum memory used
memory usage percentage
timeout usage percentage
invocations
errors
error rate
throttles
Lambda Memory Tuning

Initial B3 Silver configuration:

Memory:
1024 MB

Max Memory Used:
844 MB

Memory Usage:
82.42%

Duration:
18281.35 ms

This was considered too close to the configured memory limit.

The Lambda was increased to:

1536 MB

Validation after tuning:

Max Memory Used:
843 MB

Memory Usage:
54.88%

Duration:
12309.26 ms

Timeout Usage:
10.26%

Throttles:
0

The adjustment increased operational headroom and reduced execution duration.

Cost Engineering

Phase 2 continues the cost-control principles established in Phase 1.

The architecture intentionally avoids:

EC2
NAT Gateway
always-on clusters
always-on compute
managed services without demonstrated need

Current workload design is primarily:

serverless
event-driven
request-based
storage-based

Recurring cost sources are primarily:

S3 storage
ECR image storage
CloudWatch log storage
Lambda execution

These costs remain small and proportional to actual usage.

Terraform

Phase 2 infrastructure is managed with Terraform.

New infrastructure includes:

S3 Data Lake
Daily ingestion Lambda
EventBridge Scheduler
ECR repository
B3 Silver Lambda
S3 Lambda trigger
IAM policies
CloudWatch dashboard
CloudWatch log groups

Final Terraform validation:

terraform fmt
PASS

terraform validate
PASS

terraform plan
No changes

Final drift status:

NONE
IAM

Phase 2 continued the least-privilege model established in Phase 1.

Dedicated policies were created for:

B3 Silver Lambda administration
ECR administration
Lambda execution
S3 RAW and Silver access
CloudWatch Logs access

The original Phase 1 administrative policy was not expanded beyond its safe policy-size limit.

New scoped policies were created instead.

Validation

The following behaviors were validated:

Daily ingestion execution
B3 RAW ingestion
CVM RAW ingestion
S3 upload
idempotent RAW behavior
B3 RAW parsing
Parquet creation
Silver S3 upload
Silver idempotency
S3 event notification
automatic Lambda invocation
container Lambda execution
CloudWatch logging
CloudWatch metrics
dashboard visibility
memory tuning
Terraform convergence
Known Limitations
CVM historical ingestion

The current CVM source endpoint represents the current snapshot.

Historical execution using an arbitrary date must not be interpreted as true historical CVM data.

Historical CVM backfill requires a source that actually exposes historical snapshots.

RAW to Silver lineage metadata

Current Silver metadata records information such as:

source
raw file
trade date
record count
SHA-256

A future improvement should also persist:

RAW S3 key
RAW S3 VersionId
RAW object SHA-256

This will strengthen exact source-to-output lineage.

Reprocessing strategy

A logically equivalent Parquet file may produce a different binary SHA after library or runtime upgrades.

For this reason, reprocessing historical Silver data must remain explicit and auditable.

Silent replacement is not allowed.

Engineering Decisions

Phase 2 established the following durable decisions:

Amazon S3 is the primary Data Lake.

RAW data is preserved.

S3 versioning is mandatory for historical protection.

SHA-256 is used for idempotency.

Silent overwrite is blocked.

Serverless processing is preferred.

S3 events drive RAW to Silver processing.

AWS Lambda is used for lightweight processing.

Amazon ECR is used for dependency-heavy Lambda workloads.

Parquet is the current Silver storage format.

CloudWatch provides workload observability.

Terraform remains the source of truth for infrastructure.
Lessons Learned
1. Idempotency must be designed, not assumed

S3 event delivery and scheduled workloads can produce retries or duplicate execution.

Idempotency protects the platform from creating duplicate or conflicting data.

2. Historical data requires explicit protection

RAW data must not be silently overwritten.

Versioning and fingerprints provide traceability and recovery.

3. Real execution reveals infrastructure requirements

The B3 ingestion Lambda exposed the need for S3 ListBucket permissions during object existence checks.

This was discovered through real execution rather than static IAM design.

4. Lambda memory is also a performance parameter

Increasing memory from 1024 MB to 1536 MB reduced memory pressure and improved processing time.

The final configuration provides significantly better operational headroom.

5. Serverless architecture keeps the platform proportional

The platform achieved automated ingestion and transformation without always-on infrastructure.

This supports both cost control and operational simplicity.

Phase 2 Validation Matrix
Control	Final Status
S3 Data Lake	PASS
RAW B3 ingestion	PASS
RAW CVM ingestion	PASS
Daily scheduler	PASS
Lambda ingestion	PASS
B3 RAW to Silver	PASS
Parquet Silver	PASS
ECR container	PASS
S3 event trigger	PASS
RAW idempotency	PASS
Silver idempotency	PASS
S3 versioning	ENABLED
Encryption	ENABLED
Public access	BLOCKED
CloudWatch logs	ENABLED
CloudWatch metrics	ENABLED
CloudWatch dashboard	PASS
Silver observability	PASS
Lambda memory tuning	PASS
Terraform formatting	PASS
Terraform validation	PASS
Terraform drift	NONE
Git working tree before documentation	CLEAN
Phase Boundary

Phase 2 ends at:

AWS Data Lake Foundation
Serverless ingestion
RAW to Silver processing
Operational observability

Phase 3 begins at:

AWS Analytics Foundation

Phase 3 will introduce analytical discovery and query capabilities over the Data Lake.

Next Phase
Phase 3 — AWS Analytics Foundation

Planned initial architecture:

S3 SILVER
    |
    v
AWS Glue Data Catalog
    |
    v
Metadata / Schema
    |
    v
Amazon Athena
    |
    v
Analytical Queries

The next phase will make the Data Lake analytically discoverable without compromising the lineage, auditability and cost discipline established so far.

# Release and Repository Closure

Phase 2 implementation branch:

```text
feature/phase2-aws-data-lake-foundation

Phase 2 Pull Request:

#3
feat: complete Phase 2 AWS Data Lake Foundation

Merge commit:

c40c562

Release tag:

v0.3.0-phase2

Repository closure status:

Documentation:         COMPLETE
Pull Request:          MERGED
Merge to main:         COMPLETE
Release tag:           v0.3.0-phase2
Feature branch cleanup:PENDING

Closure Declaration

Phase 2 technical implementation is complete.

Phase 2 — AWS Data Lake Foundation
COMPLETE

Data Lake:
OPERATIONAL

RAW ingestion:
OPERATIONAL

RAW to Silver:
OPERATIONAL

Observability:
OPERATIONAL

Terraform drift:
NONE

Documentation:
COMPLETE

Git:
MERGED

Pull Request:
#3

Release:
v0.3.0-phase2

Next:
Phase 3 — AWS Analytics Foundation