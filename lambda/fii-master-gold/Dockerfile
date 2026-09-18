FROM public.ecr.aws/lambda/python:3.12

COPY pyproject.toml ${LAMBDA_TASK_ROOT}/
COPY src ${LAMBDA_TASK_ROOT}/src

RUN pip install --no-cache-dir \
    pandas==3.0.5 \
    pyarrow==25.0.1 \
    boto3 \
    botocore[crt]

CMD ["src.handlers.fii_master_gold.lambda_handler"]