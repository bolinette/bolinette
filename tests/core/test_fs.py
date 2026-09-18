"""In-memory file system nodes committed to disk in one go."""

from pathlib import Path

import pytest

from bolinette.core.fs import FSFile, FSFolder, FSNode


class TestFile:
    def test_new_file_is_empty_and_touched(self, tmp_path: Path) -> None:
        """A file that does not exist yet starts empty and is written on commit."""
        file = FSFile(tmp_path / "new.txt")

        assert file.lines == []
        assert file.touched
        assert not file.exists()

    def test_existing_file_is_read(self, tmp_path: Path) -> None:
        """An existing file loads its lines and is not rewritten unless modified."""
        (tmp_path / "old.txt").write_text("a\nb\n")

        file = FSFile(tmp_path / "old.txt")

        assert file.lines == ["a", "b"]
        assert not file.touched

    def test_append_and_prepend(self, tmp_path: Path) -> None:
        """`append` adds lines at the end and `prepend` at the start."""
        file = FSFile(tmp_path / "f.txt")
        file.append("b", "c")
        file.prepend("a")

        assert file.lines == ["a", "b", "c"]

    def test_commit_writes_lines(self, tmp_path: Path) -> None:
        """Committing writes the lines joined by newlines with a trailing newline."""
        file = FSFile(tmp_path / "f.txt")
        file.append("a", "b")
        file.commit()

        assert (tmp_path / "f.txt").read_text() == "a\nb\n"

    def test_commit_empty_file_touches_it(self, tmp_path: Path) -> None:
        """Committing a file without lines creates it empty."""
        FSFile(tmp_path / "empty").commit()

        assert (tmp_path / "empty").read_text() == ""

    def test_untouched_file_is_not_rewritten(self, tmp_path: Path) -> None:
        """An existing file that was not modified keeps its exact content on commit."""
        path = tmp_path / "old.txt"
        path.write_text("a\n\n\n")

        FSFile(path).commit()

        assert path.read_text() == "a\n\n\n"


class TestFolder:
    def test_new_folder_has_no_children(self, tmp_path: Path) -> None:
        """A folder that does not exist yet has no children."""
        folder = FSFolder(tmp_path / "new")

        assert folder.children == []

    def test_existing_folder_lists_children(self, tmp_path: Path) -> None:
        """An existing folder loads its files and sub-folders as nodes."""
        (tmp_path / "sub").mkdir()
        (tmp_path / "file.txt").write_text("")

        folder = FSFolder(tmp_path)

        assert isinstance(folder["sub"], FSFolder)
        assert isinstance(folder["file.txt"], FSFile)
        assert folder["sub"].parent is folder

    def test_contains_and_getitem(self, tmp_path: Path) -> None:
        """Children are looked up by name."""
        folder = FSFolder(tmp_path)
        folder.add_file("a.txt")

        assert "a.txt" in folder
        assert "b.txt" not in folder
        with pytest.raises(KeyError):
            folder["b.txt"]

    def test_add_file_returns_existing(self, tmp_path: Path) -> None:
        """Adding a file that already exists returns the existing node."""
        folder = FSFolder(tmp_path)
        first = folder.add_file("a.txt")

        assert folder.add_file("a.txt") is first

    def test_add_file_on_folder_name_raises(self, tmp_path: Path) -> None:
        """Adding a file under the name of an existing folder is an error."""
        folder = FSFolder(tmp_path)
        folder.add_folder("sub")

        with pytest.raises(TypeError):
            folder.add_file("sub")

    def test_add_folder_on_file_name_raises(self, tmp_path: Path) -> None:
        """Adding a folder under the name of an existing file is an error."""
        folder = FSFolder(tmp_path)
        folder.add_file("a")

        with pytest.raises(TypeError):
            folder.add_folder("a")

    def test_find_nested_path(self, tmp_path: Path) -> None:
        """`find` walks a relative path through sub-folders."""
        folder = FSFolder(tmp_path)
        file = folder.add_folder("a").add_folder("b").add_file("c.txt")

        assert folder.find(Path("a/b/c.txt")) is file
        assert folder.find(Path("a/b")) is folder["a"]["b"]  # pyright: ignore[reportIndexIssue]
        assert folder.find(Path("a/x")) is None
        assert folder.find(Path("a/b/c.txt/d")) is None

    def test_package_helpers(self, tmp_path: Path) -> None:
        """`init_package` creates `__init__.py` once and reports the folder as a package."""
        folder = FSFolder(tmp_path)

        assert not folder.is_package()
        dunder = folder.init_package()
        assert folder.is_package()
        assert folder.init_package() is dunder

    def test_commit_writes_tree(self, tmp_path: Path) -> None:
        """Committing a folder creates it and every node beneath it."""
        folder = FSFolder(tmp_path / "root")
        folder.add_folder("pkg").init_package().append("x = 1")
        folder.add_file("README.md").append("# Title")

        folder.commit()

        assert (tmp_path / "root" / "pkg" / "__init__.py").read_text() == "x = 1\n"
        assert (tmp_path / "root" / "README.md").read_text() == "# Title\n"

    def test_type_guards(self, tmp_path: Path) -> None:
        """`is_file` and `is_folder` discriminate node types."""
        folder = FSFolder(tmp_path)
        file = folder.add_file("a")

        assert FSNode.is_file(file)
        assert not FSNode.is_folder(file)
        assert FSNode.is_folder(folder)

    def test_add_folder_returns_existing(self, tmp_path: Path) -> None:
        """Adding a folder that already exists returns the existing node."""
        folder = FSFolder(tmp_path)
        first = folder.add_folder("sub")

        assert folder.add_folder("sub") is first

    def test_init_package_on_folder_raises(self, tmp_path: Path) -> None:
        """A folder named `__init__.py` cannot be turned into the package marker."""
        folder = FSFolder(tmp_path)
        folder.add_folder("__init__.py")

        with pytest.raises(TypeError):
            folder.init_package()
