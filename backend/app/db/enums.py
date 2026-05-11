from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class StoryStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class StoryVisibility(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"
    UNLISTED = "unlisted"


class MediaType(str, Enum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"


class DatePrecision(str, Enum):
    YEAR = "year"
    DATE = "date"


class NotificationEventType(str, Enum):
    STORY_LIKED = "story_liked"
    STORY_COMMENTED = "story_commented"
    STORY_BOOKMARKED = "story_bookmarked"


class ReportReason(str, Enum):
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    MISINFORMATION = "misinformation"
    OFFENSIVE_LANGUAGE = "offensive_language"


class ReportStatus(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    REMOVED = "removed"
    RESOLVED = "reviewed"


class BadgeRuleType(str, Enum):
    FIRST_STORY = "first_story"
    STORY_MILESTONE_5 = "story_milestone_5"
    STORY_MILESTONE_10 = "story_milestone_10"
