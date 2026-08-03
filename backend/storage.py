import boto3
from botocore.exceptions import ClientError
from config import get_settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class S3Storage:
    """S3-compatible storage service"""

    def __init__(self):
        """Create the boto3 S3 client if credentials are configured"""
        self.s3_client = None
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region,
                # Custom endpoint for S3-compatible storage such as MinIO
                endpoint_url=settings.s3_endpoint_url or None,
            )

    def upload_file(self, file_obj, filename: str, bucket: Optional[str] = None) -> dict:
        """Upload a file to S3"""
        if not self.s3_client:
            raise Exception("S3 client not configured. Please set AWS credentials.")

        bucket_name = bucket or settings.s3_bucket_name

        try:
            # Upload file
            self.s3_client.upload_fileobj(
                file_obj,
                bucket_name,
                filename,
                ExtraArgs={'ACL': 'private'}
            )

            return {
                "success": True,
                "bucket": bucket_name,
                "key": filename,
                "message": "File uploaded successfully"
            }
        except ClientError as e:
            logger.exception("Error uploading file to S3")
            raise RuntimeError(f"Failed to upload file: {e}") from e

    def get_presigned_url(self, file_key: str, bucket: Optional[str] = None, expiration: int = 3600) -> str:
        """Generate a presigned URL for file download"""
        if not self.s3_client:
            raise Exception("S3 client not configured")

        bucket_name = bucket or settings.s3_bucket_name

        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': file_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.exception("Error generating presigned URL")
            raise RuntimeError(f"Failed to generate download URL: {e}") from e

    def delete_file(self, file_key: str, bucket: Optional[str] = None) -> bool:
        """Delete a file from S3"""
        if not self.s3_client:
            raise Exception("S3 client not configured")

        bucket_name = bucket or settings.s3_bucket_name

        try:
            self.s3_client.delete_object(Bucket=bucket_name, Key=file_key)
            return True
        except ClientError:
            logger.exception("Error deleting file from S3")
            return False


# Singleton instance
s3_storage = S3Storage()
