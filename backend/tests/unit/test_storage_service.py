from unittest.mock import patch

import pytest

from app.db.enums import MediaType


class TestCheckConnection:
    @patch("app.services.storage.storage_client")
    def test_calls_list_buckets(self, mock_client):
        from app.services.storage import check_connection

        check_connection()

        mock_client.list_buckets.assert_called_once()

    @patch("app.services.storage.storage_client")
    def test_raises_when_storage_unreachable(self, mock_client):
        from app.services.storage import check_connection

        mock_client.list_buckets.side_effect = Exception("Connection refused")

        with pytest.raises(Exception, match="Connection refused"):
            check_connection()


class TestGetBucketForMediaType:
    @patch("app.services.storage.settings")
    def test_image_returns_images_bucket(self, mock_settings):
        from app.services.storage import get_bucket_for_media_type

        mock_settings.STORAGE_BUCKET_IMAGES = "images"
        assert get_bucket_for_media_type(MediaType.IMAGE) == "images"

    @patch("app.services.storage.settings")
    def test_audio_returns_audio_bucket(self, mock_settings):
        from app.services.storage import get_bucket_for_media_type

        mock_settings.STORAGE_BUCKET_AUDIO = "audio"
        assert get_bucket_for_media_type(MediaType.AUDIO) == "audio"

    @patch("app.services.storage.settings")
    def test_video_returns_videos_bucket(self, mock_settings):
        from app.services.storage import get_bucket_for_media_type

        mock_settings.STORAGE_BUCKET_VIDEOS = "videos"
        assert get_bucket_for_media_type(MediaType.VIDEO) == "videos"

    @patch("app.services.storage.settings")
    def test_document_falls_back_to_images_bucket(self, mock_settings):
        from app.services.storage import get_bucket_for_media_type

        mock_settings.STORAGE_BUCKET_IMAGES = "images"
        assert get_bucket_for_media_type(MediaType.DOCUMENT) == "images"


class TestUploadBytes:
    @patch("app.services.storage.storage_client")
    def test_calls_put_object_with_correct_args(self, mock_client):
        from app.services.storage import upload_bytes

        upload_bytes(
            bucket_name="images",
            storage_key="stories/abc/media/photo.png",
            content=b"fake-image-bytes",
            content_type="image/png",
        )

        mock_client.put_object.assert_called_once_with(
            Bucket="images",
            Key="stories/abc/media/photo.png",
            Body=b"fake-image-bytes",
            ContentType="image/png",
        )

    @patch("app.services.storage.storage_client")
    def test_raises_when_upload_fails(self, mock_client):
        from app.services.storage import upload_bytes

        mock_client.put_object.side_effect = Exception("Upload failed")

        with pytest.raises(Exception, match="Upload failed"):
            upload_bytes(
                bucket_name="images",
                storage_key="key.png",
                content=b"data",
                content_type="image/png",
            )


class TestDeleteObject:
    @patch("app.services.storage.storage_client")
    def test_calls_delete_object_with_correct_args(self, mock_client):
        from app.services.storage import delete_object

        delete_object(bucket_name="images", storage_key="stories/abc/photo.png")

        mock_client.delete_object.assert_called_once_with(
            Bucket="images",
            Key="stories/abc/photo.png",
        )

    @patch("app.services.storage.storage_client")
    def test_raises_when_delete_fails(self, mock_client):
        from app.services.storage import delete_object

        mock_client.delete_object.side_effect = Exception("Delete failed")

        with pytest.raises(Exception, match="Delete failed"):
            delete_object(bucket_name="images", storage_key="key.png")


class TestBuildPublicObjectUrl:
    @patch("app.services.storage.settings")
    def test_builds_correct_url(self, mock_settings):
        from app.services.storage import build_public_object_url

        mock_settings.STORAGE_PUBLIC_URL = "http://localhost:9000"

        url = build_public_object_url(bucket_name="images", storage_key="stories/abc/photo.png")

        assert url == "http://localhost:9000/images/stories/abc/photo.png"

    @patch("app.services.storage.settings")
    def test_strips_trailing_slash_from_base_url(self, mock_settings):
        from app.services.storage import build_public_object_url

        mock_settings.STORAGE_PUBLIC_URL = "http://localhost:9000/"

        url = build_public_object_url(bucket_name="images", storage_key="stories/abc/photo.png")

        assert url == "http://localhost:9000/images/stories/abc/photo.png"

    @patch("app.services.storage.settings")
    def test_encodes_special_characters_in_key(self, mock_settings):
        from app.services.storage import build_public_object_url

        mock_settings.STORAGE_PUBLIC_URL = "http://localhost:9000"

        url = build_public_object_url(bucket_name="images", storage_key="stories/abc/photo with spaces.png")

        assert "photo%20with%20spaces.png" in url

    @patch("app.services.storage.settings")
    def test_strips_leading_slash_from_storage_key(self, mock_settings):
        from app.services.storage import build_public_object_url

        mock_settings.STORAGE_PUBLIC_URL = "http://localhost:9000"

        url = build_public_object_url(bucket_name="images", storage_key="/stories/abc/photo.png")

        assert url == "http://localhost:9000/images/stories/abc/photo.png"
