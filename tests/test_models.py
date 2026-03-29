"""Tests for the models module"""

import pytest
from models import Book, Author, BookFormat


class TestBookFormat:
    """Tests for BookFormat dataclass"""

    def test_create_format(self):
        fmt = BookFormat(format_type='epub', url='http://example.com/book.epub')
        assert fmt.format_type == 'epub'
        assert fmt.url == 'http://example.com/book.epub'

    def test_create_format_with_size(self):
        fmt = BookFormat(format_type='pdf', url='http://example.com/book.pdf', size='1.2MB')
        assert fmt.size == '1.2MB'


class TestAuthor:
    """Tests for Author dataclass"""

    def test_create_author(self):
        author = Author(name='John Doe')
        assert author.name == 'John Doe'
        assert author.uri is None

    def test_create_author_with_uri(self):
        author = Author(name='John Doe', uri='http://example.com/author')
        assert author.uri == 'http://example.com/author'


class TestBook:
    """Tests for Book dataclass"""

    def test_create_book(self):
        book = Book(id='123', title='Test Book')
        assert book.id == '123'
        assert book.title == 'Test Book'
        assert book.authors == []
        assert book.formats == []

    def test_create_book_with_authors(self):
        authors = [Author(name='Author One'), Author(name='Author Two')]
        book = Book(id='123', title='Test Book', authors=authors)
        assert len(book.authors) == 2
        assert book.authors[0].name == 'Author One'

    def test_create_book_with_formats(self):
        formats = [
            BookFormat(format_type='epub', url='http://example.com/book.epub'),
            BookFormat(format_type='pdf', url='http://example.com/book.pdf')
        ]
        book = Book(id='123', title='Test Book', formats=formats)
        assert len(book.formats) == 2

    def test_get_best_format_epub(self):
        formats = [
            BookFormat(format_type='pdf', url='http://example.com/book.pdf'),
            BookFormat(format_type='epub', url='http://example.com/book.epub'),
            BookFormat(format_type='mobi', url='http://example.com/book.mobi')
        ]
        book = Book(id='123', title='Test Book', formats=formats)
        best = book.get_best_format()
        assert best.format_type == 'epub'

    def test_get_best_format_azw3(self):
        formats = [
            BookFormat(format_type='pdf', url='http://example.com/book.pdf'),
            BookFormat(format_type='azw3', url='http://example.com/book.azw3'),
            BookFormat(format_type='epub', url='http://example.com/book.epub')
        ]
        book = Book(id='123', title='Test Book', formats=formats)
        best = book.get_best_format()
        assert best.format_type == 'azw3'

    def test_get_best_format_no_formats(self):
        book = Book(id='123', title='Test Book')
        assert book.get_best_format() is None

    def test_get_download_url_specific_format(self):
        formats = [
            BookFormat(format_type='epub', url='http://example.com/book.epub'),
            BookFormat(format_type='pdf', url='http://example.com/book.pdf')
        ]
        book = Book(id='123', title='Test Book', formats=formats)
        url = book.get_download_url('pdf')
        assert url == 'http://example.com/book.pdf'

    def test_get_download_url_best_format(self):
        formats = [
            BookFormat(format_type='pdf', url='http://example.com/book.pdf'),
            BookFormat(format_type='epub', url='http://example.com/book.epub')
        ]
        book = Book(id='123', title='Test Book', formats=formats)
        url = book.get_download_url()
        assert url == 'http://example.com/book.epub'

    def test_get_download_url_nonexistent_format(self):
        formats = [
            BookFormat(format_type='epub', url='http://example.com/book.epub')
        ]
        book = Book(id='123', title='Test Book', formats=formats)
        url = book.get_download_url('mobi')
        assert url is None
