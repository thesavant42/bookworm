"""models.py: Data models for the bookworm CLI utility"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BookFormat:
    """Represents a downloadable book format"""
    format_type: str  # e.g., 'epub', 'pdf', 'mobi'
    url: str
    size: Optional[str] = None


@dataclass
class Author:
    """Represents a book author"""
    name: str
    uri: Optional[str] = None


@dataclass
class Book:
    """Represents a book from an OPDS catalog"""
    id: str
    title: str
    authors: List[Author] = field(default_factory=list)
    formats: List[BookFormat] = field(default_factory=list)
    timestamp: Optional[str] = None
    updated: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    cover_url: Optional[str] = None
    library_id: Optional[str] = None

    def get_best_format(self) -> Optional[BookFormat]:
        """Get the best available format for download"""
        # Priority: azw3 > epub > mobi > pdf > other
        format_priority = ['azw3', 'epub', 'mobi', 'pdf']
        
        for priority_format in format_priority:
            for fmt in self.formats:
                if fmt.format_type.lower() == priority_format:
                    return fmt
        
        # Return first available format if no priority match
        return self.formats[0] if self.formats else None

    def get_download_url(self, format_type: Optional[str] = None) -> Optional[str]:
        """Get download URL for a specific format or best available"""
        if format_type:
            for fmt in self.formats:
                if fmt.format_type.lower() == format_type.lower():
                    return fmt.url
            return None  # Format not found
        return self.get_best_format().url if self.get_best_format() else None
