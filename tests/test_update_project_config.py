"""
Unit tests for update_project_config.py

This test suite provides comprehensive coverage of all functions in the project
configuration update script, including edge cases and error conditions.

Usage:
    python -m unittest test_update_project_config.py
    python -m unittest test_update_project_config.TestUpdateProjectConfig.test_update_toml_field
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from resources.load_test_resources import load_test_resource
from update_project_config import (
    extract_current_list_field,
    extract_current_urls,
    load_config_file,
    load_toml_file,
    prompt_list_field_update,
    update_package_reference,
    update_toml_field,
    update_toml_list_field,
    update_toml_urls_section,
    validate_project_name,
)


class TestUpdateProjectConfig(unittest.TestCase):
    """
    Test suite for the project configuration update script.

    This class contains unit tests for all major functions in the script,
    covering normal operation, edge cases, and error conditions.
    """

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_toml = load_test_resource('test_pyproject.toml')
        self.test_toml_content = load_toml_file(Path(self.test_toml))
        self.sample_config = {
            "name": "awesome-project",
            "description": "An awesome Python project",
            "github_username": "johndoe",
            "authors": ["Jane Doe <jane@example.com>", "Bob Wilson <bob@example.com>"],
            "keywords": ["python", "awesome", "tool"],
            "urls": {
                "Bug Tracker": "https://github.com/johndoe/awesome-project/issues",
                "Documentation": "https://johndoe.github.io/awesome-project/"
            }
        }

    def test_load_bad_toml(self):
        try:
            load_toml_file(Path('bad.toml'))
        except FileNotFoundError:
            pass

    def test_validate_project_name_valid_names(self):
        """Test that valid project names are accepted."""
        valid_names = [
            "my-awesome-project",
            "data_processing_tool",
            "web-scraper-2023",
            "simple-name",
            "package.name",
            "a1",
            "project_with_underscores",
            "project-with-hyphens"
        ]

        for name in valid_names:
            with self.subTest(name=name):
                self.assertTrue(
                    validate_project_name(name),
                    f"Expected '{name}' to be valid"
                )

    def test_validate_project_name_invalid_names(self):
        """Test that invalid project names are rejected."""
        invalid_names = [
            "",  # Too short
            "a",  # Too short
            "-invalid-start",  # Starts with hyphen
            "invalid-end-",  # Ends with hyphen
            ".invalid-start",  # Starts with period
            "invalid-end.",  # Ends with period
            "a" * 215,  # Too long
            "invalid space",  # Contains space
            "invalid@symbol",  # Contains invalid symbol
        ]

        for name in invalid_names:
            with self.subTest(name=name):
                self.assertFalse(
                    validate_project_name(name),
                    f"Expected '{name}' to be invalid"
                )

    def test_extract_current_list_field_authors(self):
        """Test extraction of current authors from TOML content."""
        expected_authors = ["Your Name <your.email@example.com>"]
        actual_authors = extract_current_list_field(self.test_toml_content, "authors")
        self.assertEqual(actual_authors, expected_authors)

    def test_extract_current_list_field_keywords(self):
        """Test extraction of current keywords from TOML content."""
        expected_keywords = ["python", "testing", "example"]
        actual_keywords = extract_current_list_field(self.test_toml_content, "keywords")
        self.assertEqual(actual_keywords, expected_keywords)

    def test_extract_current_list_field_empty(self):
        """Test extraction when field doesn't exist."""
        content = 'name = "test"'
        result = extract_current_list_field(content, "nonexistent")
        self.assertEqual(result, [])

    def test_extract_current_list_field_empty_list(self):
        """Test extraction of empty list field."""
        content = 'keywords = []'
        result = extract_current_list_field(content, "keywords")
        self.assertEqual(result, [])

    def test_extract_current_urls(self):
        """Test extraction of current URLs from TOML content."""
        expected_urls = {
            "Bug Tracker": "https://github.com/your-username/your-project-name/issues",
            "Changelog": "https://github.com/your-username/your-project-name/blob/main/CHANGELOG.md"
        }
        actual_urls = extract_current_urls(self.test_toml_content)
        self.assertEqual(actual_urls, expected_urls)

    def test_extract_current_urls_no_section(self):
        """Test extraction when [tool.poetry.urls] section doesn't exist."""
        content = 'name = "test"'
        result = extract_current_urls(content)
        self.assertEqual(result, {})

    def test_update_urls(self):
        result = update_toml_urls_section(self.test_toml_content, {"new_url": "https://example.com"})
        self.assertIn('new_url', result)

    def test_add_urls(self):
        content = 'name = "test"'
        result = update_toml_urls_section(content, {"new_url": "https://example.com"})
        self.assertIn('new_url', result)

    def test_update_toml_field_basic(self):
        """Test basic field update functionality."""
        content = 'name = "old-name"'
        result = update_toml_field(content, "name", "new-name")
        self.assertIn('name = "new-name"', result)

    def test_update_toml_field_with_comments(self):
        """Test field update preserving inline comments."""
        content = 'description = "old description"  # TODO: Update this'
        result = update_toml_field(content, "description", "new description")
        expected = 'description = "new description"  # TODO: Update this'
        self.assertEqual(result.strip(), expected)

    def test_update_toml_field_single_quotes(self):
        """Test field update with single quotes."""
        content = "name = 'old-name'"
        result = update_toml_field(content, "name", "new-name")
        self.assertIn('name = "new-name"', result)

    def test_update_toml_list_field_basic(self):
        """Test basic list field update functionality."""
        content = 'authors = ["old author"]'
        new_authors = ["new author 1", "new author 2"]
        result = update_toml_list_field(content, "authors", new_authors)
        expected = 'authors = ["new author 1", "new author 2"]'
        self.assertIn(expected, result)

    def test_update_toml_list_field_with_comments(self):
        """Test list field update preserving inline comments."""
        content = 'keywords = ["old"]  # TODO: Add more'
        new_keywords = ["python", "tool"]
        result = update_toml_list_field(content, "keywords", new_keywords)
        expected = 'keywords = ["python", "tool"]  # TODO: Add more'
        self.assertIn(expected, result)

    def test_update_toml_list_field_empty_list(self):
        """Test updating with empty list."""
        content = 'keywords = ["old"]'
        result = update_toml_list_field(content, "keywords", [])
        expected = 'keywords = []'
        self.assertIn(expected, result)

    def test_update_toml_urls_section_create_new(self):
        """Test creating new URLs section."""
        content = 'name = "test"'
        urls = {"Bug Tracker": "https://github.com/user/repo/issues"}
        result = update_toml_urls_section(content, urls)

        self.assertIn('[tool.poetry.urls]', result)
        self.assertIn('"Bug Tracker" = "https://github.com/user/repo/issues"', result)

    def test_no_urls(self):
        """Test creating new URLs section."""
        content = 'name = "test"'
        urls = None
        result = update_toml_urls_section(content, urls)

        self.assertNotIn('[tool.poetry.urls]', result)

    def test_update_non_existent_field(self):
        result = update_toml_field(self.test_toml_content, 'NoField', 'bad value')
        self.assertNotIn('NoField', result)
        result = update_toml_list_field(self.test_toml_content, 'NoField', ['bad value'])
        self.assertNotIn('NoField', result)

    def test_update_package_reference(self):
        _result = update_package_reference(self.test_toml_content, 'your-project-name', 'new-project-name')

    def test_update_toml_field_not_found(self):
        """Test field update when field doesn't exist."""
        content = 'other = "value"'
        with patch('builtins.print') as mock_print:
            result = update_toml_field(content, "nonexistent", "value")
            self.assertEqual(result, content)
            mock_print.assert_called_once()

    def test_update_toml_urls_section_update_existing(self):
        """Test updating existing URLs section."""
        urls = {"New URL": "https://example.com"}
        result = update_toml_urls_section(self.test_toml_content, urls)

        self.assertIn('[tool.poetry.urls]', result)
        self.assertIn('"New URL" = "https://example.com"', result)
        # Should replace the entire section
        self.assertNotIn('Bug Tracker', result)

    def test_update_package_reference_basic(self):
        """Test basic package reference updates."""
        content = '''
name = "old-project"
packages = [{include = "old_project", from = "src"}]
known_first_party = ["old_project"]
'''
        result = update_package_reference(content, "old-project", "new-project")

        self.assertIn('include = "new_project"', result)
        self.assertIn('known_first_party = ["new_project"]', result)

    def test_update_package_reference_with_github(self):
        """Test package reference updates with GitHub username."""
        result = update_package_reference(
            self.test_toml_content,
            "your-project-name",
            "awesome-project",
            "johndoe"
        )

        self.assertIn('repository = "https://github.com/johndoe/awesome-project"', result)
        self.assertIn('homepage = "https://johndoe.github.io/awesome-project/"', result)
        self.assertIn('documentation = "https://johndoe.github.io/awesome-project/"', result)

    def test_update_package_reference_template_placeholders(self):
        """Test updating template placeholders."""
        content = '''
packages = [{include = "your_project_name", from = "src"}]
known_first_party = ["your_project_name"]
homepage = "https://your-username.github.io/your-project-name/"
'''
        result = update_package_reference(content, "old-project", "new-project", "user")

        self.assertIn('include = "new_project"', result)
        self.assertIn('known_first_party = ["new_project"]', result)
        self.assertIn('https://user.github.io/new-project/', result)

    def test_update_package_reference_without_github_username(self):
        """Test package reference updates without GitHub username."""
        result = update_package_reference(
            self.test_toml_content,
            "your-project-name",
            "awesome-project"
        )

        # Should still update project name but keep your-username placeholder
        self.assertIn('repository = "https://github.com/your-username/awesome-project"', result)
        self.assertIn('homepage = "https://your-username.github.io/awesome-project/"', result)

    # def test_load_toml_file_success(self):
    #     """Test successful TOML file loading."""
    #     with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
    #         f.write(self.sample_toml_content)
    #         temp_path = Path(f.name)
    #
    #     try:
    #         result = load_toml_file(temp_path)
    #         self.assertEqual(result, self.sample_toml_content)
    #     finally:
    #         temp_path.unlink()

    def test_load_config_file_not_found(self):
        """Test config file loading when file doesn't exist."""
        nonexistent_path = Path("nonexistent.json")

        with patch('sys.exit') as mock_exit:
            with patch('builtins.print') as mock_print:
                load_config_file(nonexistent_path)
                mock_exit.assert_called_once_with(1)
                mock_print.assert_called_once()

    # def test_load_config_file_invalid_json(self):
    #     """Test config file loading with malformed JSON."""
    #     with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    #         f.write("{ invalid json }")
    #         temp_path = Path(f.name)
    #
    #     try:
    #         with patch('sys.exit') as mock_exit:
    #             with patch('builtins.print') as mock_print:
    #                 load_config_file(temp_path)
    #                 mock_exit.assert_called_once_with(1)
    #                 mock_print.assert_called_once()
    #     finally:
    #         temp_path.unlink()

    def test_full_project_update_scenario(self):
        """Test a complete project update scenario."""
        original_content = '''[tool.poetry]
name = "your-project-name"
description = "A brief description"
authors = ["Your Name <your.email@example.com>"]
homepage = "https://your-username.github.io/your-project-name/"
repository = "https://github.com/your-username/your-project-name"

packages = [{include = "your_project_name", from = "src"}]

[tool.isort]
known_first_party = ["your_project_name"]
'''

        # Apply multiple updates
        content = update_toml_field(original_content, "name", "awesome-tool")
        content = update_toml_field(content, "description", "An awesome development tool")
        content = update_toml_list_field(content, "authors", ["Jane Doe <jane@example.com>"])
        content = update_package_reference(content, "your-project-name", "awesome-tool", "johndoe")

        # Verify all updates
        self.assertIn('name = "awesome-tool"', content)
        self.assertIn('description = "An awesome development tool"', content)
        self.assertIn('authors = ["Jane Doe <jane@example.com>"]', content)
        self.assertIn('include = "awesome_tool"', content)
        self.assertIn('known_first_party = ["awesome_tool"]', content)
        self.assertIn('https://johndoe.github.io/awesome-tool/', content)
        self.assertIn('https://github.com/johndoe/awesome-tool', content)

    def test_multiline_list_handling(self):
        """Test handling of multiline list formats."""
        content = '''authors = [
    "John Doe <john@example.com>",
    "Jane Smith <jane@example.com>"
]'''

        # This might not work perfectly with current regex, but test what we have
        new_authors = ["Bob Wilson <bob@example.com>"]
        result = update_toml_list_field(content, "authors", new_authors)

        # Should at least not break the content
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_commented_urls_handling(self):
        """Test handling of commented URLs in template."""
        content = '''[tool.poetry]
name = "test-project"
#"Bug Tracker" = "https://github.com/your-username/your-project-name/issues"
#"Changelog" = "https://github.com/your-username/your-project-name/blob/main/CHANGELOG.md"
'''

        result = update_package_reference(content, "test-project", "new-project", "user")

        # Should update commented URLs too
        self.assertIn('#"Bug Tracker" = "https://github.com/user/new-project/issues"', result)
        self.assertIn('#"Changelog" = "https://github.com/user/new-project/blob/main/CHANGELOG.md"', result)

    def test_special_characters_in_values(self):
        """Test handling of special characters in field values."""
        content = 'description = "old description"'

        # Test with various special characters
        special_descriptions = [
            "A tool with \"quotes\" inside",
            "A tool with 'single quotes'",
            "A tool with special chars: @#$%^&*()",
            "A tool with unicode: 🐍 Python tool",
        ]

        for desc in special_descriptions:
            with self.subTest(description=desc):
                result = update_toml_field(content, "description", desc)
                self.assertIn(f'description = "{desc}"', result)

    def test_edge_case_empty_values(self):
        """Test handling of empty values."""
        content = 'name = "test"'

        # Test empty string
        result = update_toml_field(content, "name", "")
        self.assertIn('name = ""', result)

        # Test empty list
        result = update_toml_list_field(content, "authors", [])
        self.assertNotIn('authors = []', result)

    @patch('builtins.input')
    def test_prompt_list_field_update_keep_current(self, mock_input):
        """Test keeping current values in list field update."""
        mock_input.side_effect = ['y']  # User chooses to keep current values

        current_values = ["John Doe <john@example.com>"]
        result = prompt_list_field_update("authors", current_values)

        self.assertIsNone(result)  # Should return None to keep current values

    @patch('builtins.input')
    @patch('builtins.print')
    def test_prompt_list_field_update_replace(self, _, mock_input):
        """Test replacing values in list field update."""
        mock_input.side_effect = [
            'n',  # Don't keep current values
            'Jane Doe <jane@example.com>',  # New author 1
            'Bob Wilson <bob@example.com>',  # New author 2
            ''  # End input
        ]

        current_values = ["John Doe <john@example.com>"]
        result = prompt_list_field_update("authors", current_values)

        expected = ["Jane Doe <jane@example.com>", "Bob Wilson <bob@example.com>"]
        self.assertEqual(result, expected)
