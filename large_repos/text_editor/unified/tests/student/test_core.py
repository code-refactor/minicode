"""
Tests for the core text editor functionality.
"""
import pytest
import time

from text_editor.core.buffer import TextBuffer
from text_editor.core.cursor import Cursor
from text_editor.core.editor import Editor
from text_editor.core.file_manager import FileManager
from text_editor.core.history import History, EditOperation


class TestTextBuffer:
    def test_initialization(self):
        """Test that the buffer is initialized correctly."""
        buffer = TextBuffer()
        assert buffer.lines == [""]
        
        buffer = TextBuffer("Hello\nWorld")
        assert buffer.lines == ["Hello", "World"]
    
    def test_get_content(self):
        """Test getting the entire content of the buffer."""
        buffer = TextBuffer("Hello\nWorld")
        assert buffer.get_content() == "Hello\nWorld"
        
        buffer = TextBuffer()
        assert buffer.get_content() == ""
    
    def test_get_line(self):
        """Test getting a specific line from the buffer."""
        buffer = TextBuffer("Hello\nWorld")
        assert buffer.get_line(0) == "Hello"
        assert buffer.get_line(1) == "World"
        
        with pytest.raises(IndexError):
            buffer.get_line(2)
    
    def test_get_line_count(self):
        """Test getting the number of lines in the buffer."""
        buffer = TextBuffer("Hello\nWorld")
        assert buffer.get_line_count() == 2
        
        buffer = TextBuffer()
        assert buffer.get_line_count() == 1
    
    def test_insert_text_single_line(self):
        """Test inserting text within a single line."""
        buffer = TextBuffer("Hello World")
        buffer.insert_text(0, 5, " Beautiful")
        assert buffer.get_content() == "Hello Beautiful World"
    
    def test_insert_text_multiline(self):
        """Test inserting text with multiple lines."""
        buffer = TextBuffer("Hello World")
        buffer.insert_text(0, 5, " Beautiful\nAmazing")
        assert buffer.get_content() == "Hello Beautiful\nAmazing World"
    
    def test_insert_text_at_end(self):
        """Test inserting text at the end of a line."""
        buffer = TextBuffer("Hello")
        buffer.insert_text(0, 5, " World")
        assert buffer.get_content() == "Hello World"
    
    def test_delete_text_single_line(self):
        """Test deleting text within a single line."""
        buffer = TextBuffer("Hello Beautiful World")
        deleted = buffer.delete_text(0, 5, 0, 15)
        assert deleted == " Beautiful"
        assert buffer.get_content() == "Hello World"
    
    def test_delete_text_multiline(self):
        """Test deleting text across multiple lines."""
        buffer = TextBuffer("Hello\nBeautiful\nWorld")
        deleted = buffer.delete_text(0, 5, 2, 0)
        assert deleted == "\nBeautiful\n"
        assert buffer.get_content() == "HelloWorld"
    
    def test_replace_text(self):
        """Test replacing text in the buffer."""
        buffer = TextBuffer("Hello World")
        replaced = buffer.replace_text(0, 0, 0, 5, "Hi")
        assert replaced == "Hello"
        assert buffer.get_content() == "Hi World"
    
    def test_clear(self):
        """Test clearing the buffer."""
        buffer = TextBuffer("Hello World")
        buffer.clear()
        assert buffer.get_content() == ""
        assert buffer.get_line_count() == 1


class TestCursor:
    def test_initialization(self):
        """Test that the cursor is initialized correctly."""
        buffer = TextBuffer("Hello World")
        cursor = Cursor(buffer=buffer)
        assert cursor.line == 0
        assert cursor.column == 0
    
    def test_move_to(self):
        """Test moving the cursor to a specific position."""
        buffer = TextBuffer("Hello\nWorld")
        cursor = Cursor(buffer=buffer)
        
        cursor.move_to(1, 3)
        assert cursor.line == 1
        assert cursor.column == 3
        
        with pytest.raises(IndexError):
            cursor.move_to(2, 0)  # Invalid line
        
        with pytest.raises(IndexError):
            cursor.move_to(1, 10)  # Invalid column
    
    def test_get_position(self):
        """Test getting the cursor position."""
        buffer = TextBuffer("Hello\nWorld")
        cursor = Cursor(buffer=buffer)
        
        cursor.move_to(1, 3)
        assert cursor.get_position() == (1, 3)
    
    def test_move_up(self):
        """Test moving the cursor up."""
        buffer = TextBuffer("Hello\nWorld")
        cursor = Cursor(buffer=buffer)
        
        cursor.move_to(1, 3)
        cursor.move_up()
        assert cursor.get_position() == (0, 3)
        
        cursor.move_up()  # Already at the top, should stay at line 0
        assert cursor.get_position() == (0, 3)
    
    def test_move_down(self):
        """Test moving the cursor down."""
        buffer = TextBuffer("Hello\nWorld")
        cursor = Cursor(buffer=buffer)
        
        cursor.move_down()
        assert cursor.get_position() == (1, 0)
        
        cursor.move_down()  # Already at the bottom, should stay at line 1
        assert cursor.get_position() == (1, 0)
    
    def test_move_left(self):
        """Test moving the cursor left."""
        buffer = TextBuffer("Hello\nWorld")
        cursor = Cursor(buffer=buffer)
        
        cursor.move_to(0, 3)
        cursor.move_left()
        assert cursor.get_position() == (0, 2)
        
        cursor.move_to(1, 0)
        cursor.move_left()  # Should move to the end of the previous line
        assert cursor.get_position() == (0, 5)
    
    def test_move_right(self):
        """Test moving the cursor right."""
        buffer = TextBuffer("Hello\nWorld")
        cursor = Cursor(buffer=buffer)
        
        cursor.move_right()
        assert cursor.get_position() == (0, 1)
        
        cursor.move_to(0, 5)
        cursor.move_right()  # Should move to the beginning of the next line
        assert cursor.get_position() == (1, 0)
    
    def test_move_to_line_start(self):
        """Test moving the cursor to the start of the line."""
        buffer = TextBuffer("Hello\nWorld")
        cursor = Cursor(buffer=buffer)
        
        cursor.move_to(0, 3)
        cursor.move_to_line_start()
        assert cursor.get_position() == (0, 0)
    
    def test_move_to_line_end(self):
        """Test moving the cursor to the end of the line."""
        buffer = TextBuffer("Hello\nWorld")
        cursor = Cursor(buffer=buffer)
        
        cursor.move_to_line_end()
        assert cursor.get_position() == (0, 5)
    
    def test_move_to_buffer_start(self):
        """Test moving the cursor to the start of the buffer."""
        buffer = TextBuffer("Hello\nWorld")
        cursor = Cursor(buffer=buffer)
        
        cursor.move_to(1, 3)
        cursor.move_to_buffer_start()
        assert cursor.get_position() == (0, 0)
    
    def test_move_to_buffer_end(self):
        """Test moving the cursor to the end of the buffer."""
        buffer = TextBuffer("Hello\nWorld")
        cursor = Cursor(buffer=buffer)
        
        cursor.move_to_buffer_end()
        assert cursor.get_position() == (1, 5)


class TestHistory:
    def test_record_operations(self):
        """Test recording different types of operations."""
        history = History()
        
        # Record an insert
        history.record_insert(0, 0, "Hello")
        assert len(history.undo_stack) == 1
        assert history.undo_stack[0].type == "insert"
        
        # Record a delete
        history.record_delete(0, 0, 0, 5, "Hello")
        assert len(history.undo_stack) == 2
        assert history.undo_stack[1].type == "delete"
        
        # Record a replace
        history.record_replace(0, 0, 0, 5, "Hi", "Hello")
        assert len(history.undo_stack) == 3
        assert history.undo_stack[2].type == "replace"
    
    def test_undo_redo(self):
        """Test the undo and redo functionality."""
        history = History()
        
        # Initial state: nothing to undo or redo
        assert not history.can_undo()
        assert not history.can_redo()
        
        # Record an operation
        history.record_insert(0, 0, "Hello")
        assert history.can_undo()
        assert not history.can_redo()
        
        # Undo the operation
        operation = history.undo()
        assert operation.type == "insert"
        assert not history.can_undo()
        assert history.can_redo()
        
        # Redo the operation
        operation = history.redo()
        assert operation.type == "insert"
        assert history.can_undo()
        assert not history.can_redo()
    
    def test_clear_history(self):
        """Test clearing the history."""
        history = History()
        
        history.record_insert(0, 0, "Hello")
        history.clear()
        
        assert not history.can_undo()
        assert not history.can_redo()


class TestEditor:
    def test_initialization(self):
        """Test that the editor is initialized correctly."""
        editor = Editor("Hello World")
        assert editor.get_content() == "Hello World"
        assert editor.get_cursor_position() == (0, 0)
    
    def test_insert_text(self):
        """Test inserting text at the cursor position."""
        editor = Editor("Hello")
        editor.set_cursor_position(0, 5)
        editor.insert_text(" World")
        assert editor.get_content() == "Hello World"
        assert editor.get_cursor_position() == (0, 11)
    
    def test_delete_char_before_cursor(self):
        """Test deleting the character before the cursor."""
        editor = Editor("Hello World")
        editor.set_cursor_position(0, 11)
        editor.delete_char_before_cursor()
        assert editor.get_content() == "Hello Worl"
        assert editor.get_cursor_position() == (0, 10)
    
    def test_delete_char_after_cursor(self):
        """Test deleting the character after the cursor."""
        editor = Editor("Hello World")
        editor.set_cursor_position(0, 5)
        editor.delete_char_after_cursor()
        assert editor.get_content() == "HelloWorld"
        assert editor.get_cursor_position() == (0, 5)
    
    def test_new_line(self):
        """Test inserting a new line at the cursor position."""
        editor = Editor("Hello World")
        editor.set_cursor_position(0, 5)
        editor.new_line()
        assert editor.get_content() == "Hello\n World"
        assert editor.get_cursor_position() == (1, 0)
    
    def test_move_cursor(self):
        """Test moving the cursor in different directions."""
        editor = Editor("Hello\nWorld")
        
        editor.move_cursor("right", 2)
        assert editor.get_cursor_position() == (0, 2)
        
        editor.move_cursor("down")
        assert editor.get_cursor_position() == (1, 2)
        
        editor.move_cursor("left")
        assert editor.get_cursor_position() == (1, 1)
        
        editor.move_cursor("up")
        assert editor.get_cursor_position() == (0, 1)
        
        editor.move_cursor("line_end")
        assert editor.get_cursor_position() == (0, 5)
        
        editor.move_cursor("line_start")
        assert editor.get_cursor_position() == (0, 0)
        
        editor.move_cursor("buffer_end")
        assert editor.get_cursor_position() == (1, 5)
        
        editor.move_cursor("buffer_start")
        assert editor.get_cursor_position() == (0, 0)
    
    def test_replace_text(self):
        """Test replacing text between specified positions."""
        editor = Editor("Hello World")
        editor.replace_text(0, 0, 0, 5, "Hi")
        assert editor.get_content() == "Hi World"
    
    def test_undo_redo(self):
        """Test undoing and redoing operations."""
        editor = Editor()
        
        # Insert some text
        editor.insert_text("Hello")
        assert editor.get_content() == "Hello"
        
        # Undo the insertion
        assert editor.undo()
        assert editor.get_content() == ""
        
        # Redo the insertion
        assert editor.redo()
        assert editor.get_content() == "Hello"
        
        # Delete some text
        editor.set_cursor_position(0, 5)
        editor.delete_char_before_cursor()
        assert editor.get_content() == "Hell"
        
        # Undo the deletion
        assert editor.undo()
        assert editor.get_content() == "Hello"
        
        # Redo the deletion
        assert editor.redo()
        assert editor.get_content() == "Hell"
    
    def test_clear(self):
        """Test clearing the editor."""
        editor = Editor("Hello World")
        editor.clear()
        assert editor.get_content() == ""
        assert editor.get_cursor_position() == (0, 0)


class TestFileManager:
    def test_file_operations(self, tmp_path):
        """Test file operations using a temporary file."""
        file_path = tmp_path / "test.txt"
        file_manager = FileManager()
        
        # Test saving a file
        file_manager.save_file("Hello World", str(file_path))
        assert file_path.read_text() == "Hello World"
        
        # Test loading a file
        content = file_manager.load_file(str(file_path))
        assert content == "Hello World"
        
        # Test file modification check
        assert not file_manager.is_file_modified()
        
        # Test getting the current path
        assert file_manager.get_current_path() == str(file_path)