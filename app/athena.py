import os, time, csv, io
import boto3
from botocore.config import Config

REGION = os.getenv("AWS_REGION", "us-east-1")
ATHENA_DB = os.getenv("ATHENA_DB", "pharmatrack")
ATHENA_OUTPUT = os.getenv("ATHENA_OUTPUT")  # s3://bucket/prefix/

_cfg = Config(retries={"max_attempts": 10, "mode": "standard"})
athena = boto3.client("athena", region_name=REGION, config=_cfg)
s3 = boto3.client("s3", region_name=REGION, config=_cfg)

def _wait(qid, timeout=180):
    start = time.time()
    while True:
        st = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"]
        if st in ("SUCCEEDED","FAILED","CANCELLED"): return st
        if time.time() - start > timeout: raise TimeoutError("Athena timeout")
        time.sleep(1.2)

def run_query(sql: str):
    assert ATHENA_OUTPUT and ATHENA_OUTPUT.startswith("s3://"), "Config ATHENA_OUTPUT s3://..."
    q = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": ATHENA_DB},
        ResultConfiguration={"OutputLocation": ATHENA_OUTPUT},
    )
    st = _wait(q["QueryExecutionId"])
    if st != "SUCCEEDED": raise RuntimeError(f"Athena error: {st}")
    out = athena.get_query_execution(QueryExecutionId=q["QueryExecutionId"])["QueryExecution"]["ResultConfiguration"]["OutputLocation"]
    path = out[len("s3://"):]
    bucket, key = path.split("/", 1)
    obj = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(obj)))
