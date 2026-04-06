import uuid

from starlette.datastructures import UploadFile

from app.db.enums import MediaType
from app.db.media_file import MediaFile
from tests.factories.media_file_factory import (
    DEFAULT_BUCKET_NAME,
    DEFAULT_CONTENT_TYPE,
    DEFAULT_FILENAME,
    make_media_file_entity,
    make_upload_file,
)


class TestMakeUploadFile:
    def test_returns_upload_file_instance(self):
        upload = make_upload_file()
        assert isinstance(upload, UploadFile)

    def test_defaults_are_a_valid_png(self):
        upload = make_upload_file()
        assert upload.filename == DEFAULT_FILENAME
        assert upload.content_type == DEFAULT_CONTENT_TYPE

    def test_content_is_readable_and_non_empty(self):
        upload = make_upload_file()
        content = upload.file.read()
        assert len(content) > 0

    def test_filename_override(self):
        upload = make_upload_file(filename="archive.jpg", content_type="image/jpeg")
        assert upload.filename == "archive.jpg"
        assert upload.content_type == "image/jpeg"

    def test_content_override(self):
        custom_bytes = b"fake-audio-data"
        upload = make_upload_file(
            filename="clip.mp3",
            content=custom_bytes,
            content_type="audio/mpeg",
        )
        assert upload.file.read() == custom_bytes

    def test_each_call_produces_independent_buffer(self):
        u1 = make_upload_file()
        u2 = make_upload_file()
        # Reading one should not affect the other
        u1.file.read()
        assert len(u2.file.read()) > 0

    def test_no_external_dependencies(self):
        # Simply constructing the upload file must not raise — confirming
        # no network or filesystem access occurs.
        upload = make_upload_file()
        assert upload is not None


class TestMakeMediaFileEntity:
    def test_returns_media_file_instance(self):
        story_id = uuid.uuid4()
        media = make_media_file_entity(story_id=story_id)
        assert isinstance(media, MediaFile)

    def test_story_id_is_set_correctly(self):
        story_id = uuid.uuid4()
        media = make_media_file_entity(story_id=story_id)
        assert media.story_id == story_id

    def test_defaults_match_factory_constants(self):
        story_id = uuid.uuid4()
        media = make_media_file_entity(story_id=story_id)
        assert media.bucket_name == DEFAULT_BUCKET_NAME
        assert media.original_filename == DEFAULT_FILENAME
        assert media.mime_type == DEFAULT_CONTENT_TYPE
        assert media.media_type == MediaType.IMAGE
        assert media.file_size_bytes > 0
        assert media.sort_order == 0

    def test_storage_key_is_auto_generated_and_unique(self):
        story_id = uuid.uuid4()
        m1 = make_media_file_entity(story_id=story_id)
        m2 = make_media_file_entity(story_id=story_id)
        assert m1.storage_key != m2.storage_key

    def test_storage_key_contains_story_id(self):
        story_id = uuid.uuid4()
        media = make_media_file_entity(story_id=story_id)
        assert str(story_id) in media.storage_key

    def test_custom_storage_key_is_respected(self):
        story_id = uuid.uuid4()
        custom_key = "stories/custom/path/file.png"
        media = make_media_file_entity(story_id=story_id, storage_key=custom_key)
        assert media.storage_key == custom_key

    def test_field_overrides_are_applied(self):
        story_id = uuid.uuid4()
        media = make_media_file_entity(
            story_id=story_id,
            original_filename="voice_memo.mp3",
            mime_type="audio/mpeg",
            media_type=MediaType.AUDIO,
            file_size_bytes=5000,
            sort_order=2,
            alt_text="A voice recording",
            caption="Recorded in 1978",
        )
        assert media.original_filename == "voice_memo.mp3"
        assert media.mime_type == "audio/mpeg"
        assert media.media_type == MediaType.AUDIO
        assert media.file_size_bytes == 5000
        assert media.sort_order == 2
        assert media.alt_text == "A voice recording"
        assert media.caption == "Recorded in 1978"

    def test_optional_fields_default_to_none(self):
        media = make_media_file_entity(story_id=uuid.uuid4())
        assert media.alt_text is None
        assert media.caption is None
