import unittest
import os
from unittest.mock import patch
from src.analyze_solution import get_files_by_extension

class TestGetFilesByExtension(unittest.TestCase):

    @patch('os.walk')
    def test_no_files(self, mock_walk):
        mock_walk.return_value = [('/path/to/dir', [], [])]
        result = get_files_by_extension('/path/to/dir', '.txt')
        self.assertEqual(result, [])

    @patch('os.walk')
    def test_single_file(self, mock_walk):
        mock_walk.return_value = [('/path/to/dir', [], ['file.txt'])]
        result = get_files_by_extension('/path/to/dir', '.txt')
        self.assertEqual(result, ['/path/to/dir/file.txt'])

    @patch('os.walk')
    def test_multiple_files(self, mock_walk):
        mock_walk.return_value = [('/path/to/dir', [], ['file1.txt', 'file2.txt', 'other.pdf'])]
        result = get_files_by_extension('/path/to/dir', '.txt')
        self.assertEqual(result, ['/path/to/dir/file1.txt', '/path/to/dir/file2.txt'])

    @patch('os.walk')
    def test_subdirectories(self, mock_walk):
        mock_walk.return_value = [
            ('/path/to/dir', ['subdir'], ['file1.txt']),
            ('/path/to/dir/subdir', [], ['file2.txt'])
        ]
        result = get_files_by_extension('/path/to/dir', '.txt')
        self.assertEqual(result, ['/path/to/dir/file1.txt', '/path/to/dir/subdir/file2.txt'])

    @patch('os.walk')
    def test_no_matching_files(self, mock_walk):
        mock_walk.return_value = [('/path/to/dir', [], ['file1.pdf', 'file2.jpg'])]
        result = get_files_by_extension('/path/to/dir', '.txt')
        self.assertEqual(result, [])

    @patch('os.walk')
    def test_hidden_files(self, mock_walk):
        mock_walk.return_value = [('/path/to/dir', [], ['.hidden.txt', 'file.txt'])]
        result = get_files_by_extension('/path/to/dir', '.txt')
        self.assertEqual(result, ['/path/to/dir/.hidden.txt', '/path/to/dir/file.txt'])

    @patch('os.path.join')
    @patch('os.walk')
    def test_os_path_join_called(self, mock_walk, mock_join):
      mock_walk.return_value = [('/path/to/dir', [], ['file.txt'])]
      mock_join.return_value = '/path/to/dir/file.txt' # Ensure consistent return value for testing
      get_files_by_extension('/path/to/dir', '.txt')
      mock_join.assert_called_with('/path/to/dir','file.txt')


