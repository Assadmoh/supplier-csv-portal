# api/generate_csv/__init__.py
import logging
import azure.functions as func
import os
import io
import csv
from datetime import datetime
from azure.storage.blob import BlobServiceClient

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
    except:
        return func.HttpResponse('Invalid JSON', status_code=400)

    # Basic fields expected
    required = ['supplier','item_code','item_name','unit_price','quantity']
    for r in required:
        if r not in data:
            return func.HttpResponse(f'Missing field {r}', status_code=400)

    # Build CSV row
    now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    filename = f"{data.get('supplier','unknown')}_{data.get('item_code')}_{now}.csv"

    # CSV header and row (adjust to your BC import columns)
    header = ['Supplier','ItemCode','ItemName','UnitPrice','Quantity','Category','CreatedUTC']
    row = [
        data.get('supplier'),
        data.get('item_code'),
        data.get('item_name'),
        data.get('unit_price'),
        data.get('quantity'),
        data.get('category',''),
        now
    ]

    # Create CSV in memory
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(header)
    writer.writerow(row)
    csv_bytes = csv_buffer.getvalue().encode('utf-8')

    # Upload to Blob Storage
    conn_str = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
    container = os.environ.get('CSV_CONTAINER', 'csv-exports')

    if not conn_str:
        return func.HttpResponse('Storage connection string not configured', status_code=500)

    blob_service = BlobServiceClient.from_connection_string(conn_str)
    blob_client = blob_service.get_blob_client(container=container, blob=filename)
    blob_client.upload_blob(csv_bytes, overwrite=True, content_settings=None)

    # Optionally: send email / notification here (see options below).
    # For now, just return the blob URL (SAS URL recommended if you want a link).
    return func.HttpResponse(
        body = '{"message":"CSV created","filename":"%s"}' % filename,
        status_code=200,
        mimetype='application/json'
    )
try:
    data = req.get_json()
except Exception as e:
    return func.HttpResponse(
        body = '{"error":"Invalid JSON: %s"}' % str(e),
        status_code=400,
        mimetype='application/json'
    )

try:
    # Blob upload code...
    blob_client.upload_blob(csv_bytes, overwrite=True)
except Exception as e:
    return func.HttpResponse(
        body = '{"error":"Blob upload failed: %s"}' % str(e),
        status_code=500,
        mimetype='application/json'
    )

# Success
return func.HttpResponse(
    body = '{"message":"CSV created","filename":"%s"}' % filename,
    status_code=200,
    mimetype='application/json'
)

