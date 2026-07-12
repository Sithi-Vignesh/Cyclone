"""Unit tests for app/backend/tools/folder_tools.py."""
import os
from unittest.mock import patch, MagicMock

import pytest

from app.backend.tools.folder_tools import (
    build_folder_index,
    open_folder,
)


@pytest.fixture
def mock_filesystem():
    """Mocks the filesystem for predictable folder indexing."""
    fake_parents = [
        r"C:\Fake\Coding",
        r"C:\Fake\Documents",
    ]
    
    fake_dirs = {
        r"C:\Fake\Coding": ["cyclone", "Notes", "TestProject"],
        r"C:\Fake\Documents": ["Personal", "notes", "Taxes2025"],
    }
    
    def fake_listdir(path):
        if path in fake_dirs:
            return fake_dirs[path]
        raise FileNotFoundError(f"Path not found: {path}")

    def fake_isdir(path):
        # We'll just treat anything returned by our fake_listdir as a directory
        return True

    with patch("app.backend.tools.folder_tools.INDEX_PARENTS", fake_parents), \
         patch("app.backend.tools.folder_tools.os.listdir", side_effect=fake_listdir), \
         patch("app.backend.tools.folder_tools.os.path.isdir", side_effect=fake_isdir):
        yield


class TestFolderTools:
    def test_build_folder_index_structure(self, mock_filesystem):
        """Case 1: Index builds a flat dict with lowercase keys."""
        index = build_folder_index()
        
        # Check parents
        assert "coding" in index
        assert r"C:\Fake\Coding" in index["coding"]
        assert "documents" in index
        assert r"C:\Fake\Documents" in index["documents"]
        
        # Check subfolders
        assert "cyclone" in index
        assert r"C:\Fake\Coding\cyclone" in index["cyclone"]
        
        assert "testproject" in index
        assert r"C:\Fake\Coding\TestProject" in index["testproject"]
        
        # Check fixed alias
        assert "downloads" in index
        assert r"C:\Users\sithi\Downloads" in index["downloads"]
        
        # Check duplicates (notes is in both Fake/Coding and Fake/Documents)
        assert "notes" in index
        assert len(index["notes"]) == 2
        assert r"C:\Fake\Coding\Notes" in index["notes"]
        assert r"C:\Fake\Documents\notes" in index["notes"]

    def test_single_clean_match(self, mock_filesystem):
        """Case 2: Single clean match resolves and opens."""
        build_folder_index()
        
        with patch("app.backend.tools.folder_tools.subprocess.Popen") as mock_popen:
            result = open_folder(folder_name="cyclone")
            
        expected_path = r"C:\Fake\Coding\cyclone"
        mock_popen.assert_called_once_with(f'explorer "{expected_path}"', shell=True)
        assert result == f"Opened {expected_path} in explorer."

    def test_app_param_passed_through(self, mock_filesystem):
        """Case 3: App param passed through correctly."""
        build_folder_index()
        
        with patch("app.backend.tools.folder_tools.subprocess.Popen") as mock_popen:
            result = open_folder(folder_name="cyclone", app="code")
            
        expected_path = r"C:\Fake\Coding\cyclone"
        mock_popen.assert_called_once_with(f'code "{expected_path}"', shell=True)
        assert result == f"Opened {expected_path} in code."

    def test_fuzzy_match(self, mock_filesystem):
        """Case 4: Fuzzy match tolerates case/typo."""
        build_folder_index()
        expected_path = r"C:\Fake\Coding\cyclone"
        
        # Test case difference
        with patch("app.backend.tools.folder_tools.subprocess.Popen") as mock_popen:
            result_case = open_folder(folder_name="Cyclone")
        mock_popen.assert_called_once_with(f'explorer "{expected_path}"', shell=True)
        assert result_case == f"Opened {expected_path} in explorer."
        
        # Test typo
        with patch("app.backend.tools.folder_tools.subprocess.Popen") as mock_popen:
            result_typo = open_folder(folder_name="cyclon")
        mock_popen.assert_called_once_with(f'explorer "{expected_path}"', shell=True)
        assert result_typo == f"Opened {expected_path} in explorer."

    def test_collision_returns_candidates(self, mock_filesystem):
        """Case 5: Collision returns both candidates, opens nothing."""
        build_folder_index()
        
        with patch("app.backend.tools.folder_tools.subprocess.Popen") as mock_popen:
            result = open_folder(folder_name="notes")
            
        mock_popen.assert_not_called()
        
        expected_paths = [r"C:\Fake\Coding\Notes", r"C:\Fake\Documents\notes"]
        expected_str = f"Found 'notes' in multiple places: {', '.join(expected_paths)}. Which one did you mean?"
        assert result == expected_str

    def test_no_match(self, mock_filesystem):
        """Case 6: No match at all."""
        build_folder_index()
        
        with patch("app.backend.tools.folder_tools.subprocess.Popen") as mock_popen:
            result = open_folder(folder_name="totally_fake_xyz_folder")
            
        mock_popen.assert_not_called()
        assert result == "Couldn't find a folder matching 'totally_fake_xyz_folder'."

    def test_exception_safety(self, mock_filesystem):
        """Case 7: Exception safety inside tool call."""
        build_folder_index()
        
        with patch("app.backend.tools.folder_tools.subprocess.Popen", side_effect=OSError("Access Denied")):
            result = open_folder(folder_name="cyclone")
            
        assert "An error occurred while opening the folder" in result
        assert "Access Denied" in result

    def test_bad_parent_does_not_crash(self):
        """Case 8: One bad parent doesn't crash the whole index build."""
        fake_parents = [r"C:\Good\Parent", r"C:\Bad\Parent"]
        
        def fake_listdir(path):
            if path == r"C:\Good\Parent":
                return ["good_subfolder"]
            elif path == r"C:\Bad\Parent":
                raise FileNotFoundError("Simulated missing parent")
            return []

        def fake_isdir(path):
            return True

        with patch("app.backend.tools.folder_tools.INDEX_PARENTS", fake_parents), \
             patch("app.backend.tools.folder_tools.os.listdir", side_effect=fake_listdir), \
             patch("app.backend.tools.folder_tools.os.path.isdir", side_effect=fake_isdir):
            
            index = build_folder_index()
            
        # The good parent and its subfolder should be indexed
        assert "parent" in index
        assert r"C:\Good\Parent" in index["parent"]
        assert r"C:\Bad\Parent" in index["parent"] # Because parent name is added BEFORE os.listdir
        
        assert "good_subfolder" in index
        assert r"C:\Good\Parent\good_subfolder" in index["good_subfolder"]
