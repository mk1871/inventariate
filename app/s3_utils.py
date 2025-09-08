import boto3
import os
from botocore.exceptions import NoCredentialsError, ClientError
from io import BytesIO
import uuid


def get_s3_client():
    """
    Inicializa y retorna un cliente de S3 usando las variables de entorno
    """
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region_name = os.getenv('AWS_REGION', 'us-east-1')

    if not aws_access_key_id or not aws_secret_access_key:
        raise Exception("AWS credentials not found in environment variables")

    return boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name
    )


def upload_file_to_s3(file_path, bucket_name, s3_file_name=None):
    """
    Sube un archivo local a S3
    """
    if s3_file_name is None:
        s3_file_name = os.path.basename(file_path)

    s3_client = get_s3_client()

    try:
        s3_client.upload_file(file_path, bucket_name, s3_file_name)
        print(f"File {file_path} uploaded to {bucket_name}/{s3_file_name}")
        return True
    except FileNotFoundError:
        print("The file was not found")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False
    except ClientError as e:
        print(f"Client error: {e}")
        return False


def upload_file_obj_to_s3(file_obj, bucket_name, s3_file_name, content_type='application/octet-stream'):
    """
    Sube un objeto de archivo (como BytesIO) a S3
    """
    s3_client = get_s3_client()

    try:
        file_obj.seek(0)
        s3_client.upload_fileobj(
            file_obj,
            bucket_name,
            s3_file_name,
            ExtraArgs={'ContentType': content_type}
        )
        print(f"File object uploaded to {bucket_name}/{s3_file_name}")
        return True
    except Exception as e:
        print(f"Error uploading file object: {e}")
        return False


def download_file_from_s3(bucket_name, s3_file_name, local_path):
    """
    Descarga un archivo desde S3 al sistema local
    """
    s3_client = get_s3_client()

    try:
        s3_client.download_file(bucket_name, s3_file_name, local_path)
        print(f"File {s3_file_name} downloaded from {bucket_name} to {local_path}")
        return True
    except FileNotFoundError:
        print("The file was not found")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False
    except ClientError as e:
        print(f"Client error: {e}")
        return False


def download_file_obj_from_s3(bucket_name, s3_file_name):
    """
    Descarga un archivo desde S3 y retorna un objeto BytesIO
    """
    s3_client = get_s3_client()
    file_obj = BytesIO()

    try:
        s3_client.download_fileobj(bucket_name, s3_file_name, file_obj)
        file_obj.seek(0)
        print(f"File {s3_file_name} downloaded from {bucket_name} to memory")
        return file_obj
    except Exception as e:
        print(f"Error downloading file: {e}")
        return None


def generate_presigned_url(bucket_name, object_name, expiration=3600):
    """
    Genera una URL pre-firmada para descargar un archivo desde S3
    """
    s3_client = get_s3_client()

    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_name},
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        return None


def list_files_in_bucket(bucket_name, prefix=''):
    """
    Lista todos los archivos en un bucket de S3 con un prefijo opcional
    """
    s3_client = get_s3_client()

    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        if 'Contents' in response:
            return [obj['Key'] for obj in response['Contents']]
        return []
    except Exception as e:
        print(f"Error listing files: {e}")
        return []


def delete_file_from_s3(bucket_name, s3_file_name):
    """
    Elimina un archivo de S3
    """
    s3_client = get_s3_client()

    try:
        s3_client.delete_object(Bucket=bucket_name, Key=s3_file_name)
        print(f"File {s3_file_name} deleted from {bucket_name}")
        return True
    except Exception as e:
        print(f"Error deleting file: {e}")
        return False