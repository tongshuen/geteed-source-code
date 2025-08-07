#!/usr/bin/env python3
# geteed - A lightweight terminal text editor
# Copyright (C) 2024 Your Name <your@email>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import curses
import os
import sys
import re
import json
import time
import platform
from typing import List, Tuple, Dict, Optional, Callable, Any
from pathlib import Path

class SyntaxHighlighter:
    def __init__(self):
        self.rules: Dict[str, Dict[str, Any]] = {}
        self.load_default_rules()
        self.load_custom_rules()
        
    def load_default_rules(self):
        # 默认语法高亮规则
        self.rules = {
            'python': {
                'keywords': ['def', 'class', 'if', 'else', 'elif', 'for', 'while', 'try', 'except', 'finally', 'with', 'import', 'from', 'as', 'return', 'yield', 'break', 'continue', 'pass', 'raise', 'lambda', 'and', 'or', 'not', 'is', 'in', 'True', 'False', 'None'],
                'string_delimiters': ['"', "'", '"""', "'''"],
                'comment_delimiters': ['#'],
                'number_regex': r'\b\d+\b',
                'color_keywords': curses.COLOR_BLUE | curses.A_BOLD,
                'color_strings': curses.COLOR_GREEN,
                'color_comments': curses.COLOR_CYAN,
                'color_numbers': curses.COLOR_MAGENTA
            },
            'cpp': {
                'keywords': ['class', 'struct', 'if', 'else', 'for', 'while', 'try', 'catch', 'throw', 'namespace', 'using', 'return', 'break', 'continue', 'switch', 'case', 'default', 'auto', 'const', 'static', 'volatile', 'public', 'private', 'protected', 'template', 'typename', 'bool', 'int', 'float', 'double', 'char', 'void', 'true', 'false', 'nullptr'],
                'string_delimiters': ['"', "'"],
                'comment_delimiters': ['//', '/*', '*/'],
                'number_regex': r'\b\d+\b',
                'color_keywords': curses.COLOR_BLUE | curses.A_BOLD,
                'color_strings': curses.COLOR_GREEN,
                'color_comments': curses.COLOR_CYAN,
                'color_numbers': curses.COLOR_MAGENTA
            },
            'javascript': {
                'keywords': ['function', 'class', 'if', 'else', 'for', 'while', 'try', 'catch', 'finally', 'throw', 'return', 'break', 'continue', 'switch', 'case', 'default', 'var', 'let', 'const', 'true', 'false', 'null', 'undefined', 'this', 'new', 'delete', 'typeof', 'instanceof', 'await', 'async', 'yield'],
                'string_delimiters': ['"', "'", '`'],
                'comment_delimiters': ['//', '/*', '*/'],
                'number_regex': r'\b\d+\b',
                'color_keywords': curses.COLOR_BLUE | curses.A_BOLD,
                'color_strings': curses.COLOR_GREEN,
                'color_comments': curses.COLOR_CYAN,
                'color_numbers': curses.COLOR_MAGENTA
            }
        }
    
    def load_custom_rules(self):
        config_path = os.path.expanduser('./.geteed.cfg')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    custom_rules = json.load(f)
                    for lang, rules in custom_rules.items():
                        if lang in self.rules:
                            self.rules[lang].update(rules)
                        else:
                            self.rules[lang] = rules
            except Exception as e:
                pass
    
    def get_highlight_info(self, language: str) -> Optional[Dict[str, Any]]:
        return self.rules.get(language.lower(), None)

class TextEditor:
    def __init__(self, filename: str):
        self.filename = filename
        self.lines: List[str] = [""]
        self.cursor_x = 0
        self.cursor_y = 0
        self.screen_offset_y = 0
        self.screen_offset_x = 0
        self.show_line_numbers = True
        self.modified = False
        self.read_only = False
        self.status_msg = ""
        self.status_timeout = 0
        self.clipboard: List[str] = []
        self.search_term = ""
        self.replace_term = ""
        self.last_search_pos: Tuple[int, int] = (0, 0)
        self.syntax_highlighter = SyntaxHighlighter()
        self.current_language = self.detect_language()
        self.theme = self.load_theme()
        self.macro_recording = False
        self.macro_commands: List[int] = []
        self.bookmarks: Dict[int, Tuple[int, int]] = {}
        self.tab_size = 4
        self.auto_indent = True
        self.line_wrap = False
        self.show_whitespace = False
        self.encoding = 'utf-8'
        self.extensions = self.load_extensions()
        
        # 尝试加载文件
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding=self.encoding) as f:
                    self.lines = [line.rstrip('\n') for line in f.readlines()]
                    if not self.lines:  # 空文件
                        self.lines = [""]
            except Exception as e:
                self.show_message(f"Error loading file: {str(e)}", 3)
        elif not self.read_only:
            # 新文件
            self.lines = [""]
            self.modified = True
    
    def detect_language(self) -> str:
        ext_map = {
            '.py': 'python',
            '.cpp': 'cpp', '.hpp': 'cpp', '.c': 'cpp', '.h': 'cpp',
            '.js': 'javascript', '.ts': 'javascript',
            '.html': 'html', '.css': 'css',
            '.sh': 'bash', '.bash': 'bash',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.kt': 'kotlin',
            '.swift': 'swift',
            '.php': 'php',
            '.rb': 'ruby',
            '.lua': 'lua',
            '.pl': 'perl',
            '.r': 'r',
            '.sql': 'sql',
            '.json': 'json',
            '.xml': 'xml',
            '.yaml': 'yaml', '.yml': 'yaml',
            '.md': 'markdown',
            '.txt': 'text'
        }
        ext = os.path.splitext(self.filename)[1].lower()
        return ext_map.get(ext, 'text')
    
    def load_theme(self) -> Dict[str, int]:
        default_theme = {
            'line_number': curses.COLOR_CYAN,
            'current_line': curses.COLOR_BLACK | curses.A_REVERSE,
            'status_bar': curses.COLOR_WHITE | curses.A_REVERSE,
            'text': curses.COLOR_WHITE,
            'keyword': curses.COLOR_BLUE | curses.A_BOLD,
            'string': curses.COLOR_GREEN,
            'comment': curses.COLOR_CYAN,
            'number': curses.COLOR_MAGENTA,
            'selection': curses.COLOR_YELLOW | curses.A_REVERSE,
            'error': curses.COLOR_RED | curses.A_BOLD,
            'warning': curses.COLOR_YELLOW | curses.A_BOLD,
            'info': curses.COLOR_GREEN | curses.A_BOLD
        }
        
        config_path = os.path.expanduser('./.geteed.cfg')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    if 'theme' in config:
                        for key, value in config['theme'].items():
                            if key in default_theme:
                                default_theme[key] = value
            except Exception as e:
                pass
        return default_theme
    
    def load_extensions(self) -> Dict[str, Callable]:
        extensions = {}
        ext_path = os.path.expanduser('./.geteed.etf')
        if os.path.exists(ext_path):
            try:
                with open(ext_path, 'r') as f:
                    code = f.read()
                    namespace = {}
                    exec(code, namespace)
                    for name, func in namespace.items():
                        if callable(func) and not name.startswith('_'):
                            extensions[name] = func
            except Exception as e:
                self.show_message(f"Error loading extensions: {str(e)}", 3)
        return extensions
    
    def show_message(self, msg: str, timeout: int = 2):
        self.status_msg = msg
        self.status_timeout = timeout
    
    def save_file(self) -> bool:
        if self.read_only:
            self.show_message("Read-only mode - cannot save", 2)
            return False
        
        try:
            with open(self.filename, 'w', encoding=self.encoding) as f:
                f.write('\n'.join(self.lines))
            self.modified = False
            self.show_message(f"Saved {self.filename}", 2)
            return True
        except Exception as e:
            self.show_message(f"Error saving file: {str(e)}", 3)
            return False
    
    def insert_text(self, text: str):
        if self.read_only:
            return
        
        lines = text.split('\n')
        if len(lines) == 1:
            self.lines[self.cursor_y] = (
                self.lines[self.cursor_y][:self.cursor_x] + 
                text + 
                self.lines[self.cursor_y][self.cursor_x:]
            )
            self.cursor_x += len(text)
        else:
            first_line = self.lines[self.cursor_y][:self.cursor_x] + lines[0]
            last_line = lines[-1] + self.lines[self.cursor_y][self.cursor_x:]
            middle_lines = lines[1:-1] if len(lines) > 2 else []
            
            new_lines = (
                self.lines[:self.cursor_y] + 
                [first_line] + 
                middle_lines + 
                [last_line] + 
                self.lines[self.cursor_y + 1:]
            )
            
            self.lines = new_lines
            self.cursor_y += len(lines) - 1
            self.cursor_x = len(lines[-1])
        
        self.modified = True
    
    def delete_selection(self, start: Tuple[int, int], end: Tuple[int, int]) -> str:
        if start == end:
            return ""
        
        if start[0] == end[0]:
            # 单行选择
            deleted = self.lines[start[0]][start[1]:end[1]]
            self.lines[start[0]] = (
                self.lines[start[0]][:start[1]] + 
                self.lines[start[0]][end[1]:]
            )
        else:
            # 多行选择
            first_part = self.lines[start[0]][:start[1]]
            last_part = self.lines[end[0]][end[1]:]
            middle_parts = [self.lines[i] for i in range(start[0] + 1, end[0])]
            
            deleted = (
                self.lines[start[0]][start[1]:] + '\n' + 
                '\n'.join(middle_parts) + '\n' + 
                self.lines[end[0]][:end[1]]
            )
            
            self.lines = (
                self.lines[:start[0]] + 
                [first_part + last_part] + 
                self.lines[end[0] + 1:]
            )
        
        self.cursor_x, self.cursor_y = start
        self.modified = True
        return deleted
    
    def get_selection(self, start: Tuple[int, int], end: Tuple[int, int]) -> str:
        if start == end:
            return ""
        
        if start[0] == end[0]:
            return self.lines[start[0]][start[1]:end[1]]
        else:
            first_part = self.lines[start[0]][start[1]:]
            middle_parts = [self.lines[i] for i in range(start[0] + 1, end[0])]
            last_part = self.lines[end[0]][:end[1]]
            return first_part + '\n' + '\n'.join(middle_parts) + '\n' + last_part
    
    def find_next(self, term: str) -> Optional[Tuple[int, int]]:
        if not term:
            return None
        
        start_y = self.cursor_y
        start_x = self.cursor_x + 1
        
        for y in range(start_y, len(self.lines)):
            line = self.lines[y]
            x = line.find(term, start_x if y == start_y else 0)
            if x != -1:
                return (y, x)
            start_x = 0
        
        for y in range(0, start_y + 1):
            line = self.lines[y]
            x = line.find(term, 0)
            if x != -1:
                return (y, x)
        
        return None
    
    def find_prev(self, term: str) -> Optional[Tuple[int, int]]:
        if not term:
            return None
        
        start_y = self.cursor_y
        start_x = self.cursor_x - 1
        
        for y in range(start_y, -1, -1):
            line = self.lines[y]
            search_end = start_x + len(term) if y == start_y else len(line)
            x = line.rfind(term, 0, search_end)
            if x != -1:
                return (y, x)
            start_x = len(line)
        
        for y in range(len(self.lines) - 1, start_y - 1, -1):
            line = self.lines[y]
            x = line.rfind(term, 0, len(line))
            if x != -1:
                return (y, x)
        
        return None
    
    def replace_next(self, search: str, replace: str) -> bool:
        pos = self.find_next(search)
        if pos is None:
            return False
        
        y, x = pos
        self.lines[y] = self.lines[y][:x] + replace + self.lines[y][x + len(search):]
        self.cursor_y = y
        self.cursor_x = x + len(replace)
        self.modified = True
        return True
    
    def replace_all(self, search: str, replace: str) -> int:
        count = 0
        for y in range(len(self.lines)):
            line = self.lines[y]
            new_line = line.replace(search, replace)
            if new_line != line:
                count += line.count(search)
                self.lines[y] = new_line
        
        if count > 0:
            self.modified = True
        return count
    
    def indent_line(self, y: int, amount: int = 1):
        if self.read_only:
            return
        
        if amount > 0:
            self.lines[y] = ' ' * (self.tab_size * amount) + self.lines[y]
        elif amount < 0:
            spaces = 0
            line = self.lines[y]
            while spaces < len(line) and line[spaces] == ' ':
                spaces += 1
            remove_spaces = min(-amount * self.tab_size, spaces)
            self.lines[y] = line[remove_spaces:]
        
        self.modified = True
    
    def auto_format(self):
        if self.read_only:
            return
        
        if self.current_language == 'python':
            try:
                import autopep8
                code = '\n'.join(self.lines)
                formatted = autopep8.fix_code(code)
                self.lines = formatted.split('\n')
                self.modified = True
                self.show_message("Auto-formatted with autopep8", 2)
            except ImportError:
                self.show_message("autopep8 not installed - cannot auto-format", 2)
        else:
            self.show_message(f"Auto-format not supported for {self.current_language}", 2)
    
    def handle_input(self, stdscr):
        key = stdscr.getch()
        
        # 处理宏录制
        if self.macro_recording and key != 18:  # 不录制Ctrl+R
            self.macro_commands.append(key)
        
        # 处理特殊键
        if key == curses.KEY_UP:
            if self.cursor_y > 0:
                self.cursor_y -= 1
                self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))
        elif key == curses.KEY_DOWN:
            if self.cursor_y < len(self.lines) - 1:
                self.cursor_y += 1
                self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))
        elif key == curses.KEY_LEFT:
            if self.cursor_x > 0:
                self.cursor_x -= 1
            elif self.cursor_y > 0:
                self.cursor_y -= 1
                self.cursor_x = len(self.lines[self.cursor_y])
        elif key == curses.KEY_RIGHT:
            if self.cursor_x < len(self.lines[self.cursor_y]):
                self.cursor_x += 1
            elif self.cursor_y < len(self.lines) - 1:
                self.cursor_y += 1
                self.cursor_x = 0
        elif key == curses.KEY_HOME:
            self.cursor_x = 0
        elif key == curses.KEY_END:
            self.cursor_x = len(self.lines[self.cursor_y])
        elif key == curses.KEY_PPAGE:  # Page Up
            self.cursor_y = max(0, self.cursor_y - (self.screen_height - 2))
            self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))
        elif key == curses.KEY_NPAGE:  # Page Down
            self.cursor_y = min(len(self.lines) - 1, self.cursor_y + (self.screen_height - 2))
            self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))
        elif key == 10:  # Enter
            if not self.read_only:
                new_line = self.lines[self.cursor_y][self.cursor_x:]
                self.lines[self.cursor_y] = self.lines[self.cursor_y][:self.cursor_x]
                
                # 自动缩进
                if self.auto_indent:
                    indent = 0
                    line = self.lines[self.cursor_y]
                    while indent < len(line) and line[indent] == ' ':
                        indent += 1
                    
                    # 检查是否在括号内
                    open_braces = line.count('(') + line.count('[') + line.count('{')
                    close_braces = line.count(')') + line.count(']') + line.count('}')
                    if open_braces > close_braces:
                        indent += self.tab_size
                    
                    new_line = ' ' * indent + new_line.lstrip()
                
                self.lines.insert(self.cursor_y + 1, new_line)
                self.cursor_y += 1
                self.cursor_x = len(new_line) - len(new_line.lstrip())
                self.modified = True
        elif key == curses.KEY_BACKSPACE or key == 127:  # Backspace
            if not self.read_only:
                if self.cursor_x > 0:
                    # 智能退格：删除tab大小的空格
                    line = self.lines[self.cursor_y]
                    if self.cursor_x >= self.tab_size and line[self.cursor_x - self.tab_size:self.cursor_x] == ' ' * self.tab_size:
                        self.lines[self.cursor_y] = (
                            line[:self.cursor_x - self.tab_size] + 
                            line[self.cursor_x:]
                        )
                        self.cursor_x -= self.tab_size
                    else:
                        self.lines[self.cursor_y] = (
                            line[:self.cursor_x - 1] + 
                            line[self.cursor_x:]
                        )
                        self.cursor_x -= 1
                    self.modified = True
                elif self.cursor_y > 0:
                    old_x = len(self.lines[self.cursor_y - 1])
                    self.lines[self.cursor_y - 1] += self.lines[self.cursor_y]
                    del self.lines[self.cursor_y]
                    self.cursor_y -= 1
                    self.cursor_x = old_x
                    self.modified = True
        elif key == curses.KEY_DC:  # Delete
            if not self.read_only:
                if self.cursor_x < len(self.lines[self.cursor_y]):
                    self.lines[self.cursor_y] = (
                        self.lines[self.cursor_y][:self.cursor_x] + 
                        self.lines[self.cursor_y][self.cursor_x + 1:]
                    )
                    self.modified = True
                elif self.cursor_y < len(self.lines) - 1:
                    self.lines[self.cursor_y] += self.lines[self.cursor_y + 1]
                    del self.lines[self.cursor_y + 1]
                    self.modified = True
        elif key == 9:  # Tab
            if not self.read_only:
                spaces = ' ' * (self.tab_size - (self.cursor_x % self.tab_size))
                self.insert_text(spaces)
        elif key == 19:  # Ctrl+S - Save
            self.save_file()
        elif key == 17:  # Ctrl+Q - Quit
            if self.modified:
                self.show_message("Unsaved changes! Press Ctrl+S to save or Ctrl+Q again to quit", 2)
                key = stdscr.getch()
                if key == 19:  # Ctrl+S
                    if self.save_file():
                        return False
                elif key == 17:  # Ctrl+Q
                    return False
            else:
                return False
        elif key == 1:  # Ctrl+A - Go to start of line
            self.cursor_x = 0
        elif key == 5:  # Ctrl+E - Go to end of line
            self.cursor_x = len(self.lines[self.cursor_y])
        elif key == 24:  # Ctrl+X - Cut line
            if not self.read_only:
                self.clipboard = [self.lines[self.cursor_y]]
                del self.lines[self.cursor_y]
                if not self.lines:
                    self.lines = [""]
                self.cursor_x = 0
                if self.cursor_y >= len(self.lines):
                    self.cursor_y = len(self.lines) - 1
                self.modified = True
        elif key == 3:  # Ctrl+C - Copy line
            self.clipboard = [self.lines[self.cursor_y]]
            self.show_message("Line copied to clipboard", 1)
        elif key == 22:  # Ctrl+V - Paste
            if not self.read_only and self.clipboard:
                self.insert_text('\n'.join(self.clipboard))
        elif key == 11:  # Ctrl+K - Cut to end of line
            if not self.read_only:
                self.clipboard = [self.lines[self.cursor_y][self.cursor_x:]]
                self.lines[self.cursor_y] = self.lines[self.cursor_y][:self.cursor_x]
                self.modified = True
        elif key == 25:  # Ctrl+Y - Paste from clipboard
            if not self.read_only and self.clipboard:
                self.insert_text('\n'.join(self.clipboard))
        elif key == 8:  # Ctrl+H - Help
            self.show_help(stdscr)
        elif key == 6:  # Ctrl+F - Find
            self.show_find_dialog(stdscr)
        elif key == 18:  # Ctrl+R - Replace
            self.show_replace_dialog(stdscr)
        elif key == 4:  # Ctrl+D - Duplicate line
            if not self.read_only:
                self.lines.insert(self.cursor_y + 1, self.lines[self.cursor_y])
                self.cursor_y += 1
                self.modified = True
        elif key == 20:  # Ctrl+T - Toggle line numbers
            self.show_line_numbers = not self.show_line_numbers
        elif key == 14:  # Ctrl+N - New file
            self.show_message("New file - Not implemented", 2)
        elif key == 15:  # Ctrl+O - Open file
            self.show_message("Open file - Not implemented", 2)
        elif key == 16:  # Ctrl+P - Print
            self.show_message("Print - Not implemented", 2)
        elif key == 23:  # Ctrl+W - Word wrap toggle
            self.line_wrap = not self.line_wrap
            self.show_message(f"Line wrap {'enabled' if self.line_wrap else 'disabled'}", 2)
        elif key == 26:  # Ctrl+Z - Undo
            self.show_message("Undo - Not implemented", 2)
        elif key == 21:  # Ctrl+U - Redo
            self.show_message("Redo - Not implemented", 2)
        elif key == 12:  # Ctrl+L - Go to line
            self.show_goto_dialog(stdscr)
        elif key == 2:  # Ctrl+B - Toggle bookmark
            self.toggle_bookmark()
        elif key == 7:  # Ctrl+G - Go to bookmark
            self.goto_bookmark(stdscr)
        elif key == 13:  # Ctrl+M - Toggle macro recording
            self.toggle_macro_recording()
        elif key == 27:  # ESC - Cancel macro recording
            if self.macro_recording:
                self.macro_recording = False
                self.show_message("Macro recording cancelled", 2)
        elif key == 28:  # Ctrl+\ - Run macro
            self.run_macro()
        elif key == 29:  # Ctrl+] - Indent right
            if not self.read_only:
                self.indent_line(self.cursor_y, 1)
        elif key == 31:  # Ctrl+/ - Indent left
            if not self.read_only:
                self.indent_line(self.cursor_y, -1)
        elif key == 30:  # Ctrl+^ - Auto format
            self.auto_format()
        elif 32 <= key <= 126 or key >= 128:  # 可打印字符
            if not self.read_only:
                self.insert_text(chr(key))
        
        # 处理扩展功能
        for name, func in self.extensions.items():
            if key == func.__code__.co_consts[0]:  # 假设扩展函数第一个常量是快捷键
                func(self)
        
        # 调整屏幕偏移以确保光标可见
        if self.cursor_y < self.screen_offset_y:
            self.screen_offset_y = self.cursor_y
        elif self.cursor_y >= self.screen_offset_y + self.screen_height - 1:
            self.screen_offset_y = self.cursor_y - self.screen_height + 2
        
        if self.cursor_x < self.screen_offset_x:
            self.screen_offset_x = self.cursor_x
        elif self.cursor_x >= self.screen_offset_x + self.screen_width - 20:
            self.screen_offset_x = self.cursor_x - self.screen_width + 20
        
        return True
    
    def toggle_bookmark(self):
        if self.cursor_y in self.bookmarks:
            del self.bookmarks[self.cursor_y]
            self.show_message(f"Bookmark removed at line {self.cursor_y + 1}", 2)
        else:
            self.bookmarks[self.cursor_y] = (self.cursor_x, self.cursor_y)
            self.show_message(f"Bookmark added at line {self.cursor_y + 1}", 2)
    
    def goto_bookmark(self, stdscr):
        if not self.bookmarks:
            self.show_message("No bookmarks set", 2)
            return
        
        bookmarks = sorted(self.bookmarks.items())
        stdscr.clear()
        stdscr.addstr(0, 0, "Bookmarks:", curses.A_BOLD)
        
        for i, (line, (x, y)) in enumerate(bookmarks):
            preview = self.lines[line][:20].replace('\n', ' ')
            stdscr.addstr(i + 1, 0, f"{line + 1}: {preview}")
        
        stdscr.addstr(len(bookmarks) + 1, 0, "Select bookmark (1-9): ")
        stdscr.refresh()
        
        key = stdscr.getch()
        if 49 <= key <= 57:  # 1-9
            index = key - 49
            if index < len(bookmarks):
                line, (x, y) = bookmarks[index]
                self.cursor_y = line
                self.cursor_x = x
                self.screen_offset_y = max(0, line - self.screen_height // 2)
    
    def toggle_macro_recording(self):
        self.macro_recording = not self.macro_recording
        if self.macro_recording:
            self.macro_commands = []
            self.show_message("Macro recording started", 2)
        else:
            self.show_message(f"Macro recorded ({len(self.macro_commands)} commands)", 2)
    
    def run_macro(self):
        if not self.macro_commands:
            self.show_message("No macro recorded", 2)
            return
        
        for cmd in self.macro_commands:
            self.handle_input(curses.initscr())  # 简化处理
        
        self.show_message(f"Macro executed ({len(self.macro_commands)} commands)", 2)
    
    def show_find_dialog(self, stdscr):
        self.show_message("Find: " + self.search_term)
        stdscr.refresh()
        
        curses.echo()
        stdscr.addstr(self.screen_height - 1, 6, "")
        term = stdscr.getstr().decode('utf-8')
        curses.noecho()
        
        if term:
            self.search_term = term
            pos = self.find_next(self.search_term)
            if pos is not None:
                self.cursor_y, self.cursor_x = pos
                self.show_message(f"Found: {self.search_term}", 2)
            else:
                self.show_message(f"Not found: {self.search_term}", 2)
    
    def show_replace_dialog(self, stdscr):
        self.show_message(f"Replace '{self.search_term}' with: {self.replace_term}")
        stdscr.refresh()
        
        curses.echo()
        stdscr.addstr(self.screen_height - 1, 8 + len(self.search_term), "")
        replace = stdscr.getstr().decode('utf-8')
        curses.noecho()
        
        if replace is not None:
            self.replace_term = replace
            if self.replace_next(self.search_term, self.replace_term):
                self.show_message(f"Replaced: {self.search_term} -> {self.replace_term}", 2)
            else:
                self.show_message(f"Not found: {self.search_term}", 2)
    
    def show_goto_dialog(self, stdscr):
        self.show_message("Go to line: ")
        stdscr.refresh()
        
        curses.echo()
        stdscr.addstr(self.screen_height - 1, 10, "")
        line_str = stdscr.getstr().decode('utf-8')
        curses.noecho()
        
        if line_str:
            try:
                line_num = int(line_str) - 1
                if 0 <= line_num < len(self.lines):
                    self.cursor_y = line_num
                    self.cursor_x = 0
                    self.screen_offset_y = max(0, line_num - self.screen_height // 2)
                    self.show_message(f"Jumped to line {line_num + 1}", 2)
                else:
                    self.show_message(f"Invalid line number: {line_num + 1}", 2)
            except ValueError:
                self.show_message("Please enter a valid line number", 2)
    
    def show_help(self, stdscr):
        help_text = [
            "GETEED (General Text Editor) Help",
            "--------------------------------",
            "Navigation:",
            "  Arrow Keys    - Move cursor",
            "  Home/End      - Move to start/end of line",
            "  Ctrl+A/Ctrl+E - Move to start/end of line",
            "  Page Up/Dn    - Move up/down one screen",
            "  Ctrl+L        - Go to line number",
            "",
            "Editing:",
            "  Enter         - Insert new line",
            "  Backspace     - Delete previous character",
            "  Delete        - Delete next character",
            "  Tab           - Insert tab/spaces",
            "  Ctrl+D        - Duplicate line",
            "  Ctrl+]/Ctrl+/ - Indent right/left",
            "  Ctrl+^        - Auto format",
            "",
            "Clipboard:",
            "  Ctrl+X        - Cut line",
            "  Ctrl+C        - Copy line",
            "  Ctrl+V        - Paste",
            "  Ctrl+K        - Cut to end of line",
            "  Ctrl+Y        - Paste from clipboard",
            "",
            "Search & Replace:",
            "  Ctrl+F        - Find",
            "  Ctrl+R        - Replace",
            "",
            "Bookmarks:",
            "  Ctrl+B        - Toggle bookmark",
            "  Ctrl+G        - Go to bookmark",
            "",
            "Macros:",
            "  Ctrl+M        - Toggle macro recording",
            "  Ctrl+\        - Run macro",
            "  ESC           - Cancel recording",
            "",
            "File Operations:",
            "  Ctrl+S        - Save file",
            "  Ctrl+Q        - Quit",
            "  Ctrl+N        - New file",
            "  Ctrl+O        - Open file",
            "",
            "View Options:",
            "  Ctrl+T        - Toggle line numbers",
            "  Ctrl+W        - Toggle line wrap",
            "",
            "Press any key to continue..."
        ]

        stdscr.clear()
        for i, line in enumerate(help_text[:self.screen_height - 1]):
            try:
                stdscr.addstr(i, 0, line)
            except curses.error:
                pass
        
        stdscr.refresh()
        stdscr.getch()
    
    def highlight_line(self, stdscr, line: str, y: int, max_line_num_width: int):
        if not line:
            return
        
        display_x = max_line_num_width if self.show_line_numbers else 0
        max_len = self.screen_width - display_x - 1
        
        # 获取语法高亮规则
        highlight_info = self.syntax_highlighter.get_highlight_info(self.current_language)
        
        if not highlight_info:
            # 无语法高亮
            try:
                stdscr.addstr(y, display_x, line[:max_len])
            except curses.error:
                pass
            return
        
        # 高亮字符串
        string_delimiters = highlight_info.get('string_delimiters', [])
        in_string = False
        string_start = 0
        string_delim = None
        
        # 高亮注释
        comment_delimiters = highlight_info.get('comment_delimiters', [])
        in_comment = False
        comment_start = 0
        
        i = 0
        while i < len(line) and i < max_len:
            # 处理字符串
            if not in_comment:
                if not in_string:
                    for delim in string_delimiters:
                        if line.startswith(delim, i):
                            in_string = True
                            string_delim = delim
                            string_start = i
                            i += len(delim)
                            break
                else:
                    if line.startswith(string_delim, i):
                        in_string = False
                        try:
                            stdscr.addstr(y, display_x + string_start, line[string_start:i + len(string_delim)], 
                                         curses.color_pair(self.theme['string']))
                        except curses.error:
                            pass
                        i += len(string_delim)
                        continue
            
            # 处理注释
            if not in_string:
                if not in_comment:
                    for delim in comment_delimiters:
                        if line.startswith(delim, i):
                            in_comment = True
                            comment_start = i
                            i = len(line)
                            break
            
            # 处理关键字
            if not in_string and not in_comment:
                for keyword in highlight_info.get('keywords', []):
                    if line.startswith(keyword, i) and (i == 0 or not line[i-1].isalnum()) and \
                       (i + len(keyword) >= len(line) or not line[i + len(keyword)].isalnum()):
                        try:
                            stdscr.addstr(y, display_x + i, keyword, 
                                         curses.color_pair(self.theme['keyword']))
                        except curses.error:
                            pass
                        i += len(keyword)
                        break
            
            # 处理数字
            if not in_string and not in_comment:
                number_regex = highlight_info.get('number_regex', '')
                if number_regex:
                    match = re.match(number_regex, line[i:])
                    if match:
                        num = match.group()
                        try:
                            stdscr.addstr(y, display_x + i, num, 
                                         curses.color_pair(self.theme['number']))
                        except curses.error:
                            pass
                        i += len(num)
                        continue
            
            if not in_string and not in_comment:
                try:
                    stdscr.addch(y, display_x + i, line[i])
                except curses.error:
                    pass
            
            i += 1
        
        # 处理未闭合的字符串或注释
        if in_string:
            try:
                stdscr.addstr(y, display_x + string_start, line[string_start:min(len(line), max_len)], 
                             curses.color_pair(self.theme['string']))
            except curses.error:
                pass
        elif in_comment:
            try:
                stdscr.addstr(y, display_x + comment_start, line[comment_start:min(len(line), max_len)], 
                             curses.color_pair(self.theme['comment']))
            except curses.error:
                pass
    
    def render(self, stdscr):
        self.screen_height, self.screen_width = stdscr.getmaxyx()
        
        # 计算行号宽度
        max_line_num_width = len(str(len(self.lines))) + 2 if self.show_line_numbers else 0
        
        # 渲染文本内容
        for i in range(self.screen_height - 1):
            line_idx = self.screen_offset_y + i
            if line_idx < len(self.lines):
                # 显示行号
                if self.show_line_numbers:
                    line_num = f"{line_idx + 1}:".rjust(max_line_num_width - 1)
                    try:
                        stdscr.addstr(i, 0, line_num, curses.color_pair(self.theme['line_number']))
                    except curses.error:
                        pass
                
                # 高亮当前行背景
                if line_idx == self.cursor_y:
                    stdscr.attron(curses.color_pair(self.theme['current_line']))
                
                # 显示行内容
                line = self.lines[line_idx][self.screen_offset_x:]
                self.highlight_line(stdscr, line, i, max_line_num_width)
                
                if line_idx == self.cursor_y:
                    stdscr.attroff(curses.color_pair(self.theme['current_line']))
            else:
                # 空行
                pass
        
        # 显示状态栏
        status_line = self.screen_height - 1
        status = f"GETEED - {self.filename} - {self.cursor_y + 1}:{self.cursor_x + 1} - "
        status += "Modified" if self.modified else "Saved"
        status += " - " + ("READ ONLY" if self.read_only else "READ/WRITE")
        status += f" - {self.current_language.upper()}"
        
        if self.macro_recording:
            status += " - RECORDING"
        
        if self.status_msg and self.status_timeout > 0:
            status = self.status_msg
            self.status_timeout -= 1
        
        status = status[:self.screen_width - 1].ljust(self.screen_width - 1)
        try:
            stdscr.addstr(status_line, 0, status, curses.color_pair(self.theme['status_bar']))
        except curses.error:
            pass
        
        # 移动光标
        cursor_screen_y = self.cursor_y - self.screen_offset_y
        if 0 <= cursor_screen_y < self.screen_height - 1:
            cursor_x = self.cursor_x - self.screen_offset_x
            if self.show_line_numbers:
                cursor_x += max_line_num_width
            try:
                stdscr.move(cursor_screen_y, min(cursor_x, self.screen_width - 1))
            except curses.error:
                pass

def main(stdscr):
    # 初始化颜色
    curses.start_color()
    curses.use_default_colors()
    
    # 解析命令行参数
    if len(sys.argv) < 2:
        stdscr.addstr(0, 0, f"Usage: {sys.argv[0]} <filename> [--nl] [--ro] [--light] [--dark]")
        stdscr.refresh()
        stdscr.getch()
        return
    
    filename = sys.argv[1]
    show_line_numbers = "--nl" not in sys.argv
    read_only = "--ro" in sys.argv
    
    # 创建编辑器实例
    editor = TextEditor(filename)
    editor.show_line_numbers = show_line_numbers
    editor.read_only = read_only
    
    # 主循环
    curses.curs_set(1)  # 显示光标
    curses.noecho()     # 关闭回显
    curses.cbreak()     # 立即响应按键
    
    try:
        while True:
            editor.render(stdscr)
            if not editor.handle_input(stdscr):
                break
    finally:
        curses.endwin()  # 恢复终端状态

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <filename> [--nl] [--ro] [--light] [--dark]")
        print("Options:")
        print("  --nl      Disable line numbers")
        print("  --ro      Read-only mode")
        print("  --light   Light color theme")
        print("  --dark    Dark color theme (default)")
        sys.exit(1)
    
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
