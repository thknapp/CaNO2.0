"""--------Import Section---------"""

# Standard Library Imports
import base64
import ctypes
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import win32con
import win32gui
from datetime import datetime
from io import BytesIO
from uuid import uuid4

# Third-Party Package Imports
import pytesseract
from bs4 import BeautifulSoup
from PIL import Image
from spellchecker import SpellChecker

# PyQt6 Imports
from PyQt6.QtCore import (
    QByteArray, QBuffer, QDateTime, QEvent, QIODevice, QPoint, QRect, QTimer, QUrl, Qt, QSize, pyqtSignal
)
from PyQt6.QtGui import (
    QAction, QActionGroup, QColor, QFont, QGuiApplication, QIcon, QPainter, QPen, QPixmap,
    QBitmap, QTextCharFormat, QTextCursor, QTextDocument, QTextFormat, QTextImageFormat, QTextListFormat
)
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QCheckBox, QDialog, QDialogButtonBox, QFileDialog,
    QFontComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, 
    QInputDialog, QMainWindow, QMessageBox, QPushButton, QSizePolicy, QSplitter, 
    QSplitterHandle, QTabWidget, QTextEdit, QToolBar, QVBoxLayout, QWidget, 
    QWidgetAction, QMenu, QAbstractItemView  
)


"""--------Styling Constants--------"""

# Styling for Toggled Toolbar Buttons
TOGGLED_BUTTON_STYLE = """
    QToolButton:checked {
        background-color: #4CAF50;
        border: 2px solid #3E8E41;
        color: white;
    }
"""

# Styling for Toggle Buttons
TOGGLE_SWITCH_STYLE = """
    QPushButton {
        background-color: #ccc;
        border: 1px solid #888;
        border-radius: 15px;
        padding: 2px;
        min-width: 40px;
        min-height: 20px;
        color: transparent;  /* Hides any text */
    }
    QPushButton:checked {
        background-color: #4CAF50; /* Green background for "on" state */
        border: 1px solid #3E8E41;
    }
"""

"""--------Constants for Application Configuration--------"""

# Application Details
APP_NAME = "Case and Note Organizer 2.0"
SCRIPT_NAME = "CaNO2.0"

# Paths for Settings and Persistent Storage
SETTINGS_DIR = os.path.join(os.getenv('APPDATA'), SCRIPT_NAME)
os.makedirs(SETTINGS_DIR, exist_ok=True)
SETTINGS_FILE = os.path.join(SETTINGS_DIR, f"{SCRIPT_NAME}-settings.json")
CUSTOM_DICT_PATH = os.path.join(SETTINGS_DIR, "custom_dictionary.json")
PERSISTENT_FOLDER = os.path.join(SETTINGS_DIR, "saved_files")
os.makedirs(PERSISTENT_FOLDER, exist_ok=True)

# Paths for Logs and Images
LOG_FILE = os.path.join(os.path.dirname(__file__), f"{SCRIPT_NAME}.log")
IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'images')

# Checklist Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKLISTS_FOLDER = os.path.join(SCRIPT_DIR, "checklists")
os.makedirs(CHECKLISTS_FOLDER, exist_ok=True)

# Themes File Path
THEMES_FILE = os.path.join(os.path.dirname(__file__), 'themes.json')

# Default Application Settings
DEFAULT_FONT_FAMILY = "Cambria"
DEFAULT_FONT_SIZE = 14
DEFAULT_THEME = "Light Theme"
DEFAULT_WINDOW_SIZE = [800, 600]
DEFAULT_WINDOW_POSITION = [100, 100]
FONT_SIZES = [str(i) for i in range(8, 98, 2)]

# Metadata File Path
METADATA_FILE = os.path.join(PERSISTENT_FOLDER, "file_metadata.json")

"""--------Global Application Settings and Management--------"""

DEFAULT_SETTINGS = {
    "theme": DEFAULT_THEME,
    "font_family": DEFAULT_FONT_FAMILY,
    "font_size": DEFAULT_FONT_SIZE,
    "auto_save": False,
    "auto_space_images_enabled": False,
    "auto_space_image_lines": 1,
    "window_size": DEFAULT_WINDOW_SIZE,
    "window_position": DEFAULT_WINDOW_POSITION,
}

def load_app_settings():
    """Load settings from the JSON file or return defaults."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f) or {}
                return {**DEFAULT_SETTINGS, **settings}
        except json.JSONDecodeError:
            logger.warning("Settings file is invalid. Using default settings.")
    return DEFAULT_SETTINGS

def save_app_settings(settings):
    """Save settings to the JSON file."""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=4)
    logger.info("Application settings saved.")

# Load settings globally
app_settings = load_app_settings()

"""--------Theme Management--------"""

def load_themes():
    """Load available themes from the JSON file."""
    if os.path.exists(THEMES_FILE):
        try:
            with open(THEMES_FILE, 'r', encoding='utf-8') as f:
                themes = json.load(f)
                for theme_name, settings in themes.items():
                    settings['text_color'] = QColor(settings['text_color'])
                    settings['font_family'] = settings.get('font_family', DEFAULT_FONT_FAMILY)
                    settings['font_size'] = settings.get('font_size', DEFAULT_FONT_SIZE)
                return themes
        except json.JSONDecodeError:
            logger.error("Themes file is invalid. Falling back to default theme.")
    return {DEFAULT_THEME: {"text_color": QColor("black"), "font_family": DEFAULT_FONT_FAMILY, "font_size": DEFAULT_FONT_SIZE}}

# Load themes globally
THEMES = load_themes()

"""--------Highlight Colors--------"""

HIGHLIGHT_STYLES = {
    "Light Yellow / Dark Gray": {"highlight": QColor(255, 255, 204), "font": QColor(64, 64, 64)},
    "Light Blue / Dark Navy": {"highlight": QColor(204, 229, 255), "font": QColor(0, 0, 51)},
    "Light Green / Dark Green": {"highlight": QColor(204, 255, 204), "font": QColor(0, 51, 0)},
    "Light Pink / Dark Purple": {"highlight": QColor(255, 204, 229), "font": QColor(51, 0, 51)},
    "Light Orange / Dark Brown": {"highlight": QColor(255, 229, 204), "font": QColor(102, 51, 0)},
    "Light Gray / Black": {"highlight": QColor(224, 224, 224), "font": QColor(0, 0, 0)},
    "Light Purple / Dark Purple": {"highlight": QColor(229, 204, 255), "font": QColor(51, 0, 51)},
    "Light Peach / Dark Brown": {"highlight": QColor(255, 229, 204), "font": QColor(102, 51, 0)},
    "Light Teal / Dark Teal": {"highlight": QColor(204, 255, 255), "font": QColor(0, 51, 51)},
    "Pale Yellow / Dark Olive": {"highlight": QColor(255, 255, 153), "font": QColor(51, 51, 0)},
    "Mint Green / Dark Green": {"highlight": QColor(204, 255, 229), "font": QColor(0, 51, 0)}
}

"""--------Spell Checker Initialization--------"""

spell = SpellChecker()
if os.path.exists(CUSTOM_DICT_PATH):
    with open(CUSTOM_DICT_PATH, 'r', encoding='utf-8') as f:
        custom_words = json.load(f)
else:
    custom_words = []
spell.word_frequency.load_words(custom_words)

"""--------File Metadata Management--------"""

def load_file_metadata():
    """Load metadata for saved files."""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_file_metadata(metadata):
    """Save metadata for saved files."""
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=4)
    logger.info("File metadata saved.")

"""--------Minimize Console--------"""

# def minimize_console():
    # """Minimize the console window."""
    # hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    # if hwnd != 0:
        # win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

# def relaunch_minimized():
    # """Relaunch the script in minimized mode."""
    # if sys.platform == "win32" and "--minimized" not in sys.argv:
        # subprocess.Popen(["python", __file__, "--minimized"], creationflags=win32con.SW_HIDE)
        # sys.exit()

# # Minimize console on launch if applicable
# if "--minimized" not in sys.argv:
    # relaunch_minimized()
# else:
    # sys.argv.remove("--minimized")
    # minimize_console()

"""--------Logging Setup--------"""

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

"""--------Functions for Application Settings--------"""

def load_settings():
    """
    Load application settings from the settings file.

    - If the file exists and is valid, returns the settings as a dictionary.
    - Ensures the "auto_save" setting is present with a default value of False.
    - If the file does not exist or is invalid, returns default settings.

    Returns:
        dict: The settings dictionary with at least "auto_save".
    """
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f) or {}
                settings.setdefault("auto_save", False)  # Add default if missing
                return settings
        except json.JSONDecodeError:
            logger.warning("Settings file is empty or invalid. Using default settings.")
            return {"auto_save": False}  # Default settings
    return {"auto_save": False}  # Default if file doesn't exist

def save_settings(settings):
    """
    Save application settings to the settings file.

    Args:
        settings (dict): A dictionary containing application settings.

    - Writes the settings to the file specified by `SETTINGS_FILE` in JSON format.
    - Logs a message to indicate successful saving.
    """
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)
    logger.info("Settings saved.")

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Case and Note Organizer 2.0")

        """------------------------ Core Attributes and Configurations ------------------------"""
        # Path to image icons
        self.images_dir = os.path.join(os.path.dirname(__file__), 'images')
        if not os.path.exists(self.images_dir):
            logger.warning(f"Images directory not found at {self.images_dir}")

        # Initialize capture state attributes
        self.capture_area_set = False  # Tracks if the capture area has been set
        self.capture_in_progress = False  # Indicates if a screen capture is in progress

        # Initialize essential attributes
        self.paths = {} 
        self.thumbnail_image_map = {}
        self.full_image_map = {}

        # Editor widget and its image map
        self.editor = ClickableTextEdit(self)
        self.editor.full_image_map = self.full_image_map

        # Window icon
        icon_path = os.path.join(self.images_dir, "cano.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            logger.warning("Icon file not found. Application icon not set.")

        """------------------------ Load Settings ------------------------"""
        # Load theme, font, and auto-save settings
        self.current_theme = app_settings.get("theme", DEFAULT_THEME)
        self.current_theme_settings = THEMES.get(self.current_theme, THEMES["Light Theme"])
        self.current_font_family = app_settings.get("font_family", DEFAULT_FONT_FAMILY)
        self.current_font_size = app_settings.get("font_size", DEFAULT_FONT_SIZE)
        self.auto_save_enabled = app_settings.get("auto_save", False)
        self.auto_space_images_enabled = app_settings.get("auto_space_images_enabled", False)
        self.auto_space_image_lines = app_settings.get("auto_space_image_lines", 1)

        """------------------------ UI Initialization ------------------------"""
        self.setup_tab_widget()
        self.init_ui()  # Initialize UI components and toolbars
        self.init_settings_menu()

        # Apply global styles and settings
        self.setStyleSheet(TOGGLED_BUTTON_STYLE)
        self.apply_theme(self.current_theme)
        self.apply_default_font_settings()

        """------------------------ Layout Configuration ------------------------"""
        # Splitter for main layout
        self.splitter = CustomSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.splitter)

        # Saved files panel
        self.saved_files_panel = SavedFilesPanel(self)
        self.saved_files_panel.setMaximumWidth(200)
        self.splitter.addWidget(self.saved_files_panel)

        # Tab widget and layout
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.splitter.addWidget(self.tab_widget)

        """------------------------ Tab Management ------------------------"""
        self.add_new_tab()  # Add an initial tab

        """------------------------ Final Adjustments ------------------------"""
        self.repaint()
        self.update()

    """------------------------ Initialization and Setup ------------------------"""

    def load_themes():
        """
        Load theme settings from the themes file.

        - Reads the themes JSON file specified by `THEMES_FILE`.
        - Converts color and font settings to PyQt-compatible objects.
        - Returns a dictionary of themes.

        Returns:
            dict: A dictionary where keys are theme names and values are theme settings.
        """
        with open(THEMES_FILE, 'r', encoding='utf-8') as f:
            themes = json.load(f)
        # Convert color and font settings to PyQt objects
        for theme_name, settings in themes.items():
            settings['text_color'] = QColor(settings['text_color'])  # Convert to QColor
            settings['font_family'] = settings.get('font_family', 'Cambria')  # Default font
            settings['font_size'] = settings.get('font_size', 14)  # Default size
        return themes

    def apply_theme(self, theme_name):
        """
        Apply the specified theme to the application and save the setting.

        Args:
            theme_name (str): The name of the theme to apply.

        - Retrieves the theme from `THEMES`, falling back to "Light Theme" if unavailable.
        - Updates the application style sheet and internal theme settings.
        - Saves the selected theme to persistent settings.
        - Forces a repaint to ensure the changes are visible.
        """
        theme = THEMES.get(theme_name, THEMES["Light Theme"])
        self.setStyleSheet(theme["style"])  # Apply main theme style
        self.current_theme = theme_name
        self.current_theme_settings = theme  # Update current theme settings in memory

        # Apply to specific UI elements if needed
        self.tab_widget.setStyleSheet(theme["style"])
        app_settings["theme"] = theme_name  # Save theme to settings
        save_settings(app_settings)  # Persist change
        self.repaint()  # Force a repaint to apply changes
        logger.info(f"Applied and saved theme: {theme_name}")

    def init_ui(self):
        """
        Initialize the main UI elements including menus, toolbars, and theme settings.

        - Creates the main menu bar with standard menus (File, Edit, View, etc.).
        - Adds a toggle action for the "Saved Files Panel" in the View menu.
        - Initializes all toolbars in a logical order.
        """
        # Create the main menu bar and standard menus
        menubar = self.menuBar()
        self.file_menu = menubar.addMenu("File")
        self.edit_menu = menubar.addMenu("Edit")
        self.search_menu = menubar.addMenu("Search")
        self.view_menu = menubar.addMenu("View")
        self.format_menu = menubar.addMenu("Format")
        self.font_menu = menubar.addMenu("Font")

        # Add "Toggle Panel" action to the View menu
        self.toggle_panel_action = QAction("Saved Files Panel", self, checkable=True)
        self.toggle_panel_action.setChecked(True)  # Panel starts visible
        self.toggle_panel_action.triggered.connect(self.sync_toggle_buttons)
        self.view_menu.addAction(self.toggle_panel_action)

        # Initialize toolbars in the desired order
        self.init_auto_save_toolbar()
        self.init_edit_toolbar()
        self.init_font_toolbar()

        self.addToolBarBreak()  # Add a visual break between toolbar sections

        self.init_file_toolbar()
        self.init_format_toolbar()
        self.init_spell_check_toolbar()
        self.init_checklist_toolbar()
        self.init_align_toolbar()
        self.init_list_toolbar()
        self.init_capture_toolbar()

    def init_settings_menu(self):
        """
        Initialize the Settings menu with options for themes, custom dictionary, and image spacing.

        - Adds a Settings menu to the menu bar.
        - Includes a Theme submenu for selecting and applying themes.
        - Adds an action to edit the custom dictionary.
        - Includes an Options submenu with "Auto Space Images" toggle and line spacing settings.
        - Adds a Checklists menu for managing checklists.
        """
        # Ensure the menu bar is initialized
        self.menu_bar = self.menuBar()

        # Add Settings Menu
        self.settings_menu = self.menu_bar.addMenu("Settings")

        # Add Theme Selection submenu
        self.theme_menu = QMenu("Theme", self)
        self.settings_menu.addMenu(self.theme_menu)
        for theme_name in THEMES.keys():
            theme_action = QAction(theme_name, self, checkable=True)
            theme_action.setChecked(theme_name == self.current_theme)  # Check the current theme
            theme_action.triggered.connect(lambda _, t=theme_name: self.apply_theme(t))
            self.theme_menu.addAction(theme_action)

        # Add Dictionary Management action
        self.edit_dictionary_action = QAction("Edit Custom Dictionary", self)
        self.edit_dictionary_action.triggered.connect(self.edit_custom_dictionary)
        self.settings_menu.addAction(self.edit_dictionary_action)

        # Add Options submenu for "Auto Space Images"
        self.options_menu = QMenu("Options", self)
        self.settings_menu.addMenu(self.options_menu)

        # Add "Auto Space Images" toggle
        self.auto_space_images_action = QAction("Auto Space Images", self, checkable=True)
        self.auto_space_images_action.setChecked(self.auto_space_images_enabled)  # Reflect current state
        self.auto_space_images_action.toggled.connect(self.toggle_auto_space_images)
        self.options_menu.addAction(self.auto_space_images_action)

        # Add line count submenu for spacing after images
        self.line_count_menu = QMenu("Set Image Spacing", self)
        self.options_menu.addMenu(self.line_count_menu)
        for i in range(1, 6):
            line_action = QAction(f"{i} Line{'s' if i > 1 else ''}", self, checkable=True)
            line_action.setData(i)  # Store line count in the action
            line_action.setChecked(i == self.auto_space_image_lines)  # Reflect current setting
            line_action.triggered.connect(self.set_auto_space_image_lines)
            self.line_count_menu.addAction(line_action)

        # Add Checklist Management Menu
        checklist_menu = self.menu_bar.addMenu("Checklists")
        manage_checklists_action = QAction("Manage Checklists", self)
        manage_checklists_action.triggered.connect(self.open_checklist_manager)
        checklist_menu.addAction(manage_checklists_action)

    def init_auto_save_toolbar(self):
        """
        Initialize the Auto Save toolbar with a toggle switch and label.

        - Creates a toolbar for enabling/disabling auto-save.
        - Adds a vertically aligned label and toggle switch button.
        - Configures the toggle button state and appearance based on saved settings.
        """
        # Create the Auto Save toolbar
        toolbar = QToolBar("Auto Save")
        self.addToolBar(toolbar)

        # Create a layout to hold the label and button
        layout = QVBoxLayout()

        # Create and configure the label
        autosave_label = QLabel("Auto Save")
        autosave_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center-align text
        layout.addWidget(autosave_label)

        # Create and configure the toggle switch button
        self.autosave_toggle_button = QPushButton("OFF")
        self.autosave_toggle_button.setCheckable(True)  # Make the button toggleable
        self.autosave_toggle_button.setFixedSize(60, 30)
        self.autosave_toggle_button.clicked.connect(self.handle_autosave_toggle)

        # Set initial state and style based on saved settings
        self.autosave_toggle_button.setChecked(self.auto_save_enabled)
        self.update_toggle_style(self.auto_save_enabled)

        # Add the button to the layout and wrap it in a widget
        layout.addWidget(self.autosave_toggle_button)
        widget = QWidget()
        widget.setLayout(layout)

        # Add the widget to the toolbar
        toolbar.addWidget(widget)

    def init_align_toolbar(self):
        """
        Initialize the alignment toolbar with actions for text alignment.

        - Creates a toolbar for text alignment.
        - Adds actions for left, center, right, and justify alignments.
        - Associates each action with its respective alignment function.
        """
        # Create and configure the alignment toolbar
        align_toolbar = QToolBar("Align")
        align_toolbar.setIconSize(QSize(20, 20))  # Set icon size for toolbar buttons
        self.addToolBar(align_toolbar)

        # Left alignment action
        align_left_action = QAction(QIcon(os.path.join(self.images_dir, 'align-left.png')), "Align Left", self)
        align_left_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignLeft))
        align_toolbar.addAction(align_left_action)

        # Center alignment action
        align_center_action = QAction(QIcon(os.path.join(self.images_dir, 'align-center.png')), "Align Center", self)
        align_center_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignCenter))
        align_toolbar.addAction(align_center_action)

        # Right alignment action
        align_right_action = QAction(QIcon(os.path.join(self.images_dir, 'align-right.png')), "Align Right", self)
        align_right_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignRight))
        align_toolbar.addAction(align_right_action)

        # Justify alignment action
        align_justify_action = QAction(QIcon(os.path.join(self.images_dir, 'align-justify.png')), "Align Justify", self)
        align_justify_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignJustify))
        align_toolbar.addAction(align_justify_action)

    def init_capture_toolbar(self):
        """
        Initialize the Capture toolbar with actions for setting the capture area, screen grabs, OCR, and capturing.

        - Creates the toolbar and adds it to the top toolbar area.
        - Adds a button to set the capture area.
        - Includes buttons for screen grabbing, OCR, and general capturing.
        - Adds a spacer for better button alignment.
        """
        # Create and configure the Capture toolbar
        self.capture_toolbar = QToolBar("Capture")
        self.capture_toolbar.setIconSize(QSize(30, 30))  # Set icon size for toolbar buttons
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.capture_toolbar)

        # Set Capture Area button
        set_capture_area_action = QAction(QIcon(os.path.join(self.images_dir, 'set_capture.png')), "Set Capture Area",
                                          self)
        set_capture_area_action.triggered.connect(self.set_capture_area)
        self.capture_toolbar.addAction(set_capture_area_action)

        # Add a spacer widget for button alignment
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.capture_toolbar.addWidget(spacer)

        # Screen Grab button
        screen_grab_button = QPushButton(QIcon(os.path.join(self.images_dir, 'screen_grab.png')), "", self)
        screen_grab_button.setIconSize(QSize(45, 45))  # Larger button icon
        screen_grab_button.clicked.connect(self.screen_grab)
        self.capture_toolbar.addWidget(screen_grab_button)

        # OCR button
        ocr_button = QPushButton(QIcon(os.path.join(self.images_dir, 'ocr.png')), "", self)
        ocr_button.setIconSize(QSize(45, 45))  # Larger button icon
        ocr_button.clicked.connect(self.perform_ocr)
        self.capture_toolbar.addWidget(ocr_button)

        # General Capture button
        capture_button = QPushButton(QIcon(os.path.join(self.images_dir, 'capture.png')), "", self)
        capture_button.setIconSize(QSize(45, 45))  # Larger button icon
        capture_button.clicked.connect(self.capture)
        self.capture_toolbar.addWidget(capture_button)

    def init_edit_toolbar(self):
        """
        Initialize the Edit toolbar with actions for undo, redo, cut, copy, and paste.

        - Adds actions for basic text editing functions (Undo, Redo, Cut, Copy, Paste).
        - Associates each action with its corresponding functionality in the current editor.
        - Integrates actions into both the toolbar and the Edit menu.
        """
        # Create and configure the Edit toolbar
        edit_toolbar = QToolBar("Edit")
        edit_toolbar.setIconSize(QSize(20, 20))  # Set smaller icon size for compact toolbar
        self.addToolBar(edit_toolbar)

        # Undo action
        undo_action = QAction(QIcon(os.path.join(self.images_dir, 'arrow-curve_left.png')), "Undo", self)
        undo_action.setShortcut("Ctrl+Z")  # Set keyboard shortcut
        undo_action.triggered.connect(lambda: self.get_current_editor().undo())  # Link to editor's undo
        edit_toolbar.addAction(undo_action)
        self.edit_menu.addAction(undo_action)  # Add to Edit menu

        # Redo action
        redo_action = QAction(QIcon(os.path.join(self.images_dir, 'arrow-curve_right.png')), "Redo", self)
        redo_action.setShortcut("Ctrl+Y")  # Set keyboard shortcut
        redo_action.triggered.connect(lambda: self.get_current_editor().redo())  # Link to editor's redo
        edit_toolbar.addAction(redo_action)
        self.edit_menu.addAction(redo_action)  # Add to Edit menu

        # Cut action
        cut_action = QAction(QIcon(os.path.join(self.images_dir, 'scissors.png')), "Cut", self)
        cut_action.setShortcut("Ctrl+X")  # Set keyboard shortcut
        cut_action.triggered.connect(lambda: self.get_current_editor().cut())  # Link to editor's cut
        edit_toolbar.addAction(cut_action)
        self.edit_menu.addAction(cut_action)  # Add to Edit menu

        # Copy action
        copy_action = QAction(QIcon(os.path.join(self.images_dir, 'document-copy.png')), "Copy", self)
        copy_action.setShortcut("Ctrl+C")  # Set keyboard shortcut
        copy_action.triggered.connect(lambda: self.get_current_editor().copy())  # Link to editor's copy
        edit_toolbar.addAction(copy_action)
        self.edit_menu.addAction(copy_action)  # Add to Edit menu

        # Paste action
        paste_action = QAction(QIcon(os.path.join(self.images_dir, 'clipboard-paste-document-text.png')), "Paste", self)
        paste_action.setShortcut("Ctrl+V")  # Set keyboard shortcut
        paste_action.triggered.connect(lambda: self.get_current_editor().paste())  # Link to editor's paste
        edit_toolbar.addAction(paste_action)
        self.edit_menu.addAction(paste_action)  # Add to Edit menu

    def init_file_toolbar(self):
        """
        Initialize the File toolbar with actions for managing files and tabs.

        - Adds actions for creating a new instance, opening files, saving files, creating tabs, and closing tabs.
        - Integrates these actions into both the toolbar and the File menu.
        """
        # Create and configure the File toolbar
        toolbar = QToolBar("File")
        toolbar.setIconSize(QSize(20, 20))  # Set icon size
        self.addToolBar(toolbar)

        # New Instance action
        new_window_action = QAction(QIcon(os.path.join(self.images_dir, 'new-instance.png')), "New Instance", self)
        new_window_action.setShortcut("Ctrl+N")  # Shortcut for new instance
        new_window_action.triggered.connect(self.open_new_instance)
        toolbar.addAction(new_window_action)
        self.file_menu.addAction(new_window_action)

        # Open File action
        open_action = QAction(QIcon(os.path.join(self.images_dir, 'open_file.png')), "Open", self)
        open_action.setShortcut("Ctrl+O")  # Shortcut for opening a file
        open_action.triggered.connect(self.file_open)
        toolbar.addAction(open_action)
        self.file_menu.addAction(open_action)

        # Save File action
        save_action = QAction(QIcon(os.path.join(self.images_dir, 'save.png')), "Save", self)
        save_action.setShortcut("Ctrl+S")  # Shortcut for saving a file
        save_action.triggered.connect(lambda: self.file_save(self.tab_widget.currentIndex()))
        toolbar.addAction(save_action)
        self.file_menu.addAction(save_action)

        # Save As action
        saveas_action = QAction(QIcon(os.path.join(self.images_dir, 'save_as.png')), "Save As...", self)
        saveas_action.setShortcut("Ctrl+Alt+S")  # Shortcut for "Save As"
        saveas_action.triggered.connect(lambda: self.file_save_as(self.tab_widget.currentIndex()))
        toolbar.addAction(saveas_action)
        self.file_menu.addAction(saveas_action)

        # Save All action
        save_all_action = QAction(QIcon(os.path.join(self.images_dir, 'save_all.png')), "Save All", self)
        save_all_action.setShortcut("Ctrl+Shift+S")
        save_all_action.triggered.connect(self.file_save_all)
        self.file_menu.addAction(save_all_action)

        # New Tab action
        new_tab_action = QAction(QIcon(os.path.join(self.images_dir, 'new-tab.png')), "New Tab", self)
        new_tab_action.setShortcut("Ctrl+T")  # Shortcut for creating a new tab
        new_tab_action.triggered.connect(self.add_new_tab)
        toolbar.addAction(new_tab_action)
        self.file_menu.addAction(new_tab_action)

        # Close All Tabs action
        close_all_action = QAction(QIcon(os.path.join(self.images_dir, 'close-tab.png')), "Close All Tabs", self)
        close_all_action.setShortcut("Ctrl+Shift+W")  # Shortcut for closing all tabs
        close_all_action.triggered.connect(self.close_all_tabs)
        toolbar.addAction(close_all_action)
        self.file_menu.addAction(close_all_action)

    def init_font_toolbar(self):
        """
        Initialize the Font toolbar with font family and size selectors.

        - Adds a font combo box for selecting the font family.
        - Adds a size combo box for selecting the font size.
        - Connects these selectors to their respective handlers for applying changes.
        """
        # Create and configure the Font toolbar
        toolbar = QToolBar("Font")
        toolbar.setIconSize(QSize(20, 20))  # Set smaller icon size for toolbar
        self.addToolBar(toolbar)

        # Font ComboBox for selecting font family
        font_box = QFontComboBox()
        font_box.setCurrentFont(QFont(self.current_font_family))  # Set default font
        font_box.currentFontChanged.connect(self.on_font_change)  # Connect to font change handler
        toolbar.addWidget(font_box)

        # Font Size ComboBox for selecting font size
        size_box = QComboBox()
        size_box.addItems(FONT_SIZES)  # Populate with predefined font sizes
        size_box.setCurrentText(str(self.current_font_size))  # Set default size
        size_box.currentTextChanged.connect(self.on_fontsize_change)  # Connect to size change handler
        size_box.setMinimumWidth(50)  # Set a minimum width for better visibility
        toolbar.addWidget(size_box)

    def init_format_toolbar(self):
        """
        Initialize the Format toolbar with actions for text formatting.

        - Adds buttons for bold, italic, underline, strikethrough, and highlight formatting.
        - Includes a dropdown menu for selecting highlight colors.
        - Adds a button to clear all text formatting.
        - Applies a custom toggled style for buttons with on/off states.
        """
        # Create and configure the Format toolbar
        self.format_toolbar = QToolBar("Format")
        self.format_toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(self.format_toolbar)

        # Bold action
        self.bold_action = QAction(QIcon(os.path.join(self.images_dir, 'bold.png')), "Bold", self)
        self.bold_action.setCheckable(True)
        self.bold_action.setShortcut("Ctrl+B")
        self.bold_action.toggled.connect(lambda checked: self.toggle_text_format("bold", checked))
        self.format_toolbar.addAction(self.bold_action)
        # Apply toggled style
        self.format_toolbar.widgetForAction(self.bold_action).setStyleSheet(TOGGLED_BUTTON_STYLE)

        # Italic action
        self.italic_action = QAction(QIcon(os.path.join(self.images_dir, 'italic.png')), "Italic", self)
        self.italic_action.setCheckable(True)
        self.italic_action.setShortcut("Ctrl+I")
        self.italic_action.toggled.connect(lambda checked: self.toggle_text_format("italic", checked))
        self.format_toolbar.addAction(self.italic_action)
        self.format_toolbar.widgetForAction(self.italic_action).setStyleSheet(TOGGLED_BUTTON_STYLE)

        # Underline action
        self.underline_action = QAction(QIcon(os.path.join(self.images_dir, 'underline.png')), "Underline", self)
        self.underline_action.setCheckable(True)
        self.underline_action.setShortcut("Ctrl+U")
        self.underline_action.toggled.connect(lambda checked: self.toggle_text_format("underline", checked))
        self.format_toolbar.addAction(self.underline_action)
        self.format_toolbar.widgetForAction(self.underline_action).setStyleSheet(TOGGLED_BUTTON_STYLE)

        # Strikethrough action
        self.strikethrough_action = QAction(QIcon(os.path.join(self.images_dir, 'strikethrough.png')), "Strikethrough",
                                            self)
        self.strikethrough_action.setCheckable(True)
        self.strikethrough_action.toggled.connect(lambda checked: self.toggle_text_format("strikethrough", checked))
        self.format_toolbar.addAction(self.strikethrough_action)
        self.format_toolbar.widgetForAction(self.strikethrough_action).setStyleSheet(TOGGLED_BUTTON_STYLE)

        # Highlight action
        self.highlight_action = QAction(QIcon(os.path.join(self.images_dir, 'highlighter.png')), "Highlight", self)
        self.highlight_action.setCheckable(True)
        self.highlight_action.toggled.connect(lambda checked: self.toggle_highlighting(checked))
        self.format_toolbar.addAction(self.highlight_action)
        self.format_toolbar.widgetForAction(self.highlight_action).setStyleSheet(TOGGLED_BUTTON_STYLE)

        # Highlight color dropdown menu
        highlight_menu = QMenu("Highlight Colors", self)
        highlight_group = QActionGroup(self)
        highlight_group.setExclusive(True)  # Only one highlight color can be selected
        for name, colors in HIGHLIGHT_STYLES.items():
            action = self.create_highlight_action(name, colors)
            action.setCheckable(True)
            action.setData(colors)
            action.triggered.connect(self.on_highlight_color_selected)
            highlight_group.addAction(action)
            highlight_menu.addAction(action)
        self.highlight_action.setMenu(highlight_menu)  # Attach menu to the highlight action
        self.current_highlight_color = list(HIGHLIGHT_STYLES.values())[0]  # Set default highlight color

        # Clear formatting action
        clear_format_action = QAction(QIcon(os.path.join(self.images_dir, 'clear_format.png')), "Clear Formatting",
                                      self)
        clear_format_action.setShortcut("Ctrl+Space")
        clear_format_action.triggered.connect(self.clear_formatting)
        self.format_toolbar.addAction(clear_format_action)

    def init_list_toolbar(self):
        """
        Initialize the List toolbar with actions for creating and managing lists.

        - Adds actions for bullet lists, numbered lists, and adjusting indentation.
        - Integrates actions into both the toolbar and the Format menu.
        """
        # Create and configure the List toolbar
        list_toolbar = QToolBar("Lists")
        list_toolbar.setIconSize(QSize(20, 20))  # Set icon size
        self.addToolBar(list_toolbar)

        # Bullet List action
        bullet_list_action = QAction(QIcon(os.path.join(self.images_dir, 'bullet.png')), "Bullet List", self)
        bullet_list_action.setShortcut("Ctrl+Shift+L")  # Shortcut for bullet list
        bullet_list_action.triggered.connect(self.add_bullet_list)  # Connect to handler
        list_toolbar.addAction(bullet_list_action)
        self.format_menu.addAction(bullet_list_action)  # Add to Format menu

        # Numbered List action
        numbered_list_action = QAction(QIcon(os.path.join(self.images_dir, 'numbered-list.png')), "Numbered List", self)
        numbered_list_action.setShortcut("Ctrl+Shift+N")  # Shortcut for numbered list
        numbered_list_action.triggered.connect(self.add_numbered_list)  # Connect to handler
        list_toolbar.addAction(numbered_list_action)
        self.format_menu.addAction(numbered_list_action)  # Add to Format menu

        # Increase Indent action
        increase_indent_action = QAction(QIcon(os.path.join(self.images_dir, 'indent.png')), "Increase Indent", self)
        increase_indent_action.setShortcut("Ctrl+Tab")  # Shortcut for increasing indent
        increase_indent_action.triggered.connect(self.increase_indent)  # Connect to handler
        list_toolbar.addAction(increase_indent_action)

        # Decrease Indent action
        decrease_indent_action = QAction(QIcon(os.path.join(self.images_dir, 'outdent.png')), "Decrease Indent", self)
        decrease_indent_action.setShortcut("Ctrl+Shift+Tab")  # Shortcut for decreasing indent
        decrease_indent_action.triggered.connect(self.decrease_indent)  # Connect to handler
        list_toolbar.addAction(decrease_indent_action)

    def init_spell_check_toolbar(self):
        """
        Initialize the Spell Check toolbar with a toggle button.

        - Adds a toggle button to enable or disable real-time spell checking.
        - Applies a custom toggled style for the button.
        - Populates checklists using `load_checklists_to_dropdown` if required.
        """
        # Create and configure the Spell Check toolbar
        toolbar = QToolBar("Spell Check")
        self.addToolBar(toolbar)

        # Spell Check toggle button
        self.spell_check_action = QAction(QIcon(os.path.join(self.images_dir, 'spellcheck.png')), "Spell Check", self)
        self.spell_check_action.setCheckable(True)  # Make the action toggleable
        self.spell_check_action.toggled.connect(self.toggle_real_time_spell_check)  # Connect to spell check handler
        toolbar.addAction(self.spell_check_action)

        # Apply toggled style to the Spell Check button
        spell_check_button = toolbar.widgetForAction(self.spell_check_action)
        if spell_check_button:
            spell_check_button.setStyleSheet(TOGGLED_BUTTON_STYLE)

        # Store the toolbar as an attribute for future reference
        self.spell_check_toolbar = toolbar

    def init_checklist_toolbar(self):
        """
        Initialize the Checklist toolbar with a dropdown for checklist selection.

        - Creates a toolbar for managing checklists.
        - Adds a dropdown menu for displaying available checklists.
        - Populates the dropdown menu with checklist options.
        """
        # Create and configure the Checklist toolbar
        checklist_toolbar = QToolBar("Checklist Toolbar")
        checklist_toolbar.setIconSize(QSize(20, 20))  # Set icon size for toolbar buttons
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, checklist_toolbar)  # Add to the top toolbar area

        # Create a dropdown for selecting checklists
        self.checklist_dropdown = QComboBox(self)
        self.checklist_dropdown.addItem("Loading...")  # Placeholder text
        self.checklist_dropdown.currentIndexChanged.connect(self.open_selected_checklist)  # Connect to handler
        checklist_toolbar.addWidget(self.checklist_dropdown)

        # Add a spacer to align elements properly
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        checklist_toolbar.addWidget(spacer)

        # Load available checklists into the dropdown menu
        self.load_checklists_to_dropdown()

    def setup_tab_widget(self):
        """
        Set up the main tab widget for managing multiple tabs.

        - Enables tab closing with close buttons.
        - Adds a context menu for additional tab options.
        - Sets the tab widget as the central widget in the main window.
        """
        # Create and configure the tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)  # Enable close buttons on tabs
        self.tab_widget.tabCloseRequested.connect(self.close_tab)  # Connect close event to handler

        # Enable and configure a custom context menu for the tab widget
        self.tab_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self.show_tab_context_menu)

        # Set the tab widget as the central widget of the main window
        self.setCentralWidget(self.tab_widget)

    """------------------------ Main Window and UI Management ------------------------"""

    def closeEvent(self, event):
        """
        Override the close event to handle auto-saving, file cleanup, and application settings persistence.

        - Auto-saves modified documents if auto-save is enabled.
        - Removes empty auto-saved files from the persistent folder.
        - Saves file metadata and updates saved files panel.
        - Saves window size and position to application settings.
        """
        for index in reversed(range(self.tab_widget.count())):
            editor = self.tab_widget.widget(index)
            file_path = self.paths.get(index)

            # Auto-save modified documents if auto-save is enabled
            if self.autosave_toggle_button.isChecked() and editor.document().isModified():
                if file_path:
                    # Save to existing file
                    self.auto_save_current_tab(index=index)
                else:
                    # Save to a default file name in the persistent folder if no file name is set
                    file_name = f"Untitled_{index + 1}.txt"
                    persistent_path = os.path.join(PERSISTENT_FOLDER, file_name)
                    with open(persistent_path, 'w', encoding='utf-8') as f:
                        f.write(editor.toPlainText())
                    self.file_metadata_manager.update_file_metadata(file_name, persistent_path, persistent_path)
                    self.saved_files_panel.add_saved_file(file_name)

            # Remove empty auto-saved files
            if file_path and file_path.startswith(PERSISTENT_FOLDER) and self.is_tab_empty(editor):
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.file_metadata_manager.remove_metadata_entry(os.path.basename(file_path))
                    logger.info(f"Empty auto-saved file removed on exit: {file_path}")
                    self.saved_files_panel.refresh_files_list()

            # Save the file metadata for open tabs
            if file_path:
                content = self.get_tab_content(index)
                self.file_metadata_manager.update_file_metadata(
                    os.path.basename(file_path), file_path, file_path
                )
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            # Close the tab
            self.close_tab(index)

        # Save application settings (e.g., window size and position) before exit
        app_settings["window_size"] = [self.size().width(), self.size().height()]
        app_settings["window_position"] = [self.pos().x(), self.pos().y()]
        save_settings(app_settings)

        # Log application close and persist settings
        logger.info("Application closed. Settings and metadata saved.")

        # Call the parent class's closeEvent to finalize
        super().closeEvent(event)

    def setup_custom_context_menu(self):
        """
        Set up a custom context menu for the main window.

        - Configures the context menu policy to allow a custom menu.
        - Connects the right-click event to the method for displaying the menu.
        """
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)  # Enable custom context menu
        self.customContextMenuRequested.connect(self.show_custom_context_menu)  # Connect to handler

    def show_tab_context_menu(self, position):
        """
        Display a context menu for tabs with options to rename or close the selected tab.

        Args:
            position (QPoint): The position where the context menu should appear.
        """
        # Create the context menu
        menu = QMenu(self)

        # Close Tab action
        close_action = QAction("Close Tab", self)
        close_action.triggered.connect(
            lambda: self.close_tab(self.tab_widget.tabBar().tabAt(position)))  # Close the selected tab
        menu.addAction(close_action)

        # Rename Tab action
        rename_action = QAction("Rename Tab", self)
        rename_action.triggered.connect(
            lambda: self.rename_tab(self.tab_widget.tabBar().tabAt(position)))  # Rename the selected tab
        menu.addAction(rename_action)

        # Show the menu at the specified position
        menu.exec(self.tab_widget.mapToGlobal(position))

    def add_new_tab(self, text=None):
        """
        Add a new tab with a unique untitled name.

        Args:
            text (str, optional): The initial text content for the new tab. Defaults to an empty string.

        - Ensures the new tab has a unique untitled name.
        - Creates a text editor for the tab and sets the font and initial content.
        - Sets up a custom context menu for the new tab.
        - Auto-saves the new tab if auto-save is enabled.
        """
        # Ensure 'text' is a string and default to an empty string if None or invalid
        if not isinstance(text, str):
            text = ""

        # Determine the next available untitled file name
        untitled_count = 1
        existing_titles = [self.tab_widget.tabText(i) for i in range(self.tab_widget.count())]
        existing_files = os.listdir(PERSISTENT_FOLDER)
        while f"Untitled_{untitled_count}.txt" in existing_titles or f"Untitled_{untitled_count}.txt" in existing_files:
            untitled_count += 1
        untitled_name = f"Untitled_{untitled_count}.txt"

        # Create the new tab editor
        new_tab = ClickableTextEdit()
        new_tab.full_image_map = self.full_image_map
        new_tab.setFont(QFont(self.current_font_family, self.current_font_size))
        new_tab.setPlainText(text)

        # Add the new tab to the tab widget
        index = self.tab_widget.addTab(new_tab, untitled_name)
        self.tab_widget.setCurrentIndex(index)

        # Set up a custom context menu for the new tab
        self.setup_custom_context_menu()

        # Auto-save the tab's initial content if auto-save is enabled
        if self.autosave_toggle_button.isChecked():
            persistent_path = os.path.join(PERSISTENT_FOLDER, untitled_name)
            with open(persistent_path, 'w', encoding='utf-8') as f:
                f.write(text)
            self.file_metadata_manager.update_file_metadata(untitled_name, persistent_path, persistent_path)
            self.paths[index] = persistent_path
            self.saved_files_panel.refresh_files_list()
            logger.info(f"Auto-saved initial content to persistent path: {persistent_path}")

    def close_tab(self, index):
        """
        Close a tab and handle unsaved changes or cleanup.

        Args:
            index (int): The index of the tab to be closed.

        - Prompts the user to save changes if the document is modified and auto-save is disabled.
        - Removes empty auto-saved files if applicable.
        - Closes the tab and updates paths and metadata.
        """
        editor = self.tab_widget.widget(index)
        file_path = self.paths.get(index)

        # Check for unsaved changes if auto-save is disabled
        if editor.document().isModified() and not self.autosave_toggle_button.isChecked():
            response = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"The document '{self.tab_widget.tabText(index)}' has unsaved changes. Would you like to save them?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            )
            if response == QMessageBox.StandardButton.Save:
                self.file_save(index)  # Save the file
            elif response == QMessageBox.StandardButton.Cancel:
                return  # Do not close the tab if canceled

        # Remove empty auto-saved files if applicable
        if file_path and file_path.startswith(PERSISTENT_FOLDER) and self.is_tab_empty(editor):
            if os.path.exists(file_path):
                os.remove(file_path)  # Delete the file
                self.file_metadata_manager.remove_metadata_entry(os.path.basename(file_path))
                logger.info(f"Empty auto-saved file removed: {file_path}")
                self.saved_files_panel.refresh_files_list()

        # Close the tab and clean up
        self.tab_widget.removeTab(index)
        if index in self.paths:
            del self.paths[index]  # Remove the path from tracking
        logger.info(f"Tab at index {index} closed.")

    def close_all_tabs(self):
        """
        Close all tabs in the tab widget.

        - Iterates through all tabs in reverse order.
        - Prompts for unsaved changes if necessary while closing each tab.
        """
        for index in reversed(range(self.tab_widget.count())):
            self.tab_widget.setCurrentIndex(index)  # Set the current tab
            self.close_tab(index)  # Close the current tab

    def ensure_tab_open(self):
        """
        Ensure that at least one tab is open.

        - Creates a new tab if no tabs are currently open.
        - Logs the creation of a new tab when necessary.
        """
        if self.tab_widget.count() == 0:
            self.add_new_tab()  # Add a new tab if none exist
            logger.info("No open tabs found. A new tab has been created.")

    def rename_tab(self, index):
        """
        Prompt the user to rename the specified tab.

        Args:
            index (int): The index of the tab to rename.

        - Displays a dialog for the user to input a new tab name.
        - Updates the tab's name if the user confirms the change.
        """
        current_name = self.tab_widget.tabText(index)  # Get the current tab name
        new_name, ok = QInputDialog.getText(self, "Rename Tab", "Enter new name:", text=current_name)

        if ok and new_name:  # If the user confirms and the new name is not empty
            self.tab_widget.setTabText(index, new_name)  # Set the new tab name
            logger.info(f"Tab at index {index} renamed to '{new_name}'.")

    def add_editor_to_tab(self, editor, path):
        """
        Add a text editor to a new tab and configure its settings.

        Args:
            editor (QTextEdit): The editor widget to add to the tab.
            path (str): The file path associated with the tab.

        Returns:
            int: The index of the newly created tab.
        """
        # Add the editor to a new tab and set the tab's label to the file name
        index = self.tab_widget.addTab(editor, os.path.basename(path))
        self.paths[index] = path  # Store the file path for the tab
        self.tab_widget.setCurrentIndex(index)  # Set the newly created tab as the current one
        self.tab_widget.setTabToolTip(index, path)  # Set the file path as the tab's tooltip
        return index  # Return the index of the newly created tab

    def get_current_editor(self):
        """
        Retrieve the currently active editor widget.

        Returns:
            QWidget: The editor widget in the currently selected tab.
        """
        return self.tab_widget.currentWidget()

    def get_current_tab_index(self):
        """
        Get the current index of the active tab.

        Returns:
            int: The index of the active tab, or -1 if no tabs are open.
        """
        return self.tab_widget.currentIndex() if self.tab_widget.count() > 0 else -1

    def sync_toggle_buttons(self):
        """
        Sync the visibility of the saved files panel with the state of the View menu toggle action.

        - Shows or hides the saved files panel based on the toggle action state.
        - Updates the text and icon of the panel's collapse button accordingly.
        """
        if self.toggle_panel_action.isChecked():
            self.saved_files_panel.show()
            self.saved_files_panel.collapse_button.setText("◀")  # Icon to collapse
        else:
            self.saved_files_panel.hide()

    def toggle_panel_visibility(self):
        """
        Toggle the visibility of the saved files panel and update the toggle action text.

        - Shows or hides the saved files panel based on the toggle action state.
        - Updates the text of the toggle action to reflect the current state.
        """
        if self.toggle_panel_action.isChecked():
            self.saved_files_panel.show()
            self.toggle_panel_action.setText("Hide Panel")
        else:
            self.saved_files_panel.hide()
            # self.toggle_panel_action.setText("Show Panel")  # Uncomment if text update is needed

        logger.info("User interface initialized with tab support.")

    """------------------------ File Management ------------------------"""
    
    def file_open(self):
        """
        Open a file and load its content into a tab.

        - Prompts the user to select a file (TXT or HTML).
        - Loads the file content into an existing or new tab based on the current tab's state.
        - Updates paths and tab settings for the loaded file.
        """
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open file",
            "",
            "Text and HTML documents (*.txt *.html);;All files (*.*)"
        )
        if path:
            try:
                # Get the current tab and editor
                index = self.get_current_tab_index()
                current_editor = self.tab_widget.widget(index) if index >= 0 else None

                # Reuse current tab if it's empty and unmodified
                if current_editor and self.is_tab_empty(current_editor) and not current_editor.document().isModified():
                    editor = current_editor
                    self.paths[index] = path
                    self.tab_widget.setTabText(index, os.path.basename(path))
                    self.tab_widget.setTabToolTip(index, path)
                else:
                    # Create a new tab and set up paths
                    editor = ClickableTextEdit()
                    index = self.tab_widget.addTab(editor, os.path.basename(path))
                    self.paths[index] = path
                    self.tab_widget.setCurrentIndex(index)
                    self.tab_widget.setTabToolTip(index, path)

                # Load file content into the editor
                self.load_file_content(path, editor)
                logger.info(f"File opened: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")
                logger.error(f"Failed to open file: {str(e)}")

    def load_file_content(self, path, editor):
        """
        Load the content of a file into the specified editor.

        Args:
            path (str): The file path to load.
            editor (QTextEdit): The editor where the content will be loaded.

        - Determines the file format based on its extension.
        - Loads HTML files using `load_html_file`.
        - Loads plain text files directly into the editor.
        """
        if path.endswith(".html"):
            self.load_html_file(path, editor)  # Use HTML-specific loader for HTML files
        else:
            with open(path, 'r', encoding='utf-8') as f:
                text_content = f.read()  # Read plain text content
            editor.setPlainText(text_content)  # Load content into the editor

    def load_html_file(self, path, editor):
        """
        Load an HTML file with images and text into the specified editor.

        Args:
            path (str): Path to the HTML file.
            editor (QTextEdit): The editor where the content will be loaded.

        - Parses the HTML file and removes unnecessary elements (scripts, overlays, buttons).
        - Extracts and reconstructs images (thumbnails and full-size) into the editor.
        - Updates image mappings with unique IDs for resource management.
        - Sets the modified HTML content into the editor.
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Parse HTML content with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove unwanted elements
            for script in soup.find_all('script'):
                script.decompose()
            for overlay_div in soup.find_all('div', id='overlay'):
                overlay_div.decompose()
            for button in soup.find_all('button'):
                if button.get_text(strip=True) == 'Close':
                    button.decompose()

            # Initialize image maps for the editor
            editor.full_image_map = {}
            editor.thumbnail_image_map = {}

            # Process all <img> tags
            for img_tag in soup.find_all('img'):
                img_src = img_tag.get('src')
                if img_src and img_src.startswith("data:image/png;base64,"):
                    # Decode thumbnail image data
                    base64_thumbnail = img_src.split("base64,")[1]
                    thumbnail_data = base64.b64decode(base64_thumbnail)
                    thumbnail_pixmap = QPixmap()
                    thumbnail_pixmap.loadFromData(thumbnail_data)

                    # Extract full image data from 'onclick' attribute
                    onclick_attr = img_tag.get('onclick')
                    if onclick_attr and "showFullImage" in onclick_attr:
                        base64_full_image = onclick_attr.split("base64,")[1].rstrip("')")

                        # Generate a unique ID for the image
                        unique_id = str(uuid4())

                        # Store images in editor's and main window's image maps
                        editor.full_image_map[unique_id] = base64_full_image
                        editor.thumbnail_image_map[unique_id] = thumbnail_pixmap
                        self.full_image_map[unique_id] = base64_full_image
                        self.thumbnail_image_map[unique_id] = thumbnail_pixmap

                        # Replace 'src' with the unique ID
                        img_tag['src'] = unique_id
                        img_tag['onclick'] = ""  # Clear the 'onclick' attribute

                        # Remove the 'href' attribute from parent <a> tag if present
                        if img_tag.parent and img_tag.parent.name == 'a':
                            img_tag.parent['href'] = unique_id

                        # Add the thumbnail image to the editor's document resources
                        editor.document().addResource(
                            QTextDocument.ResourceType.ImageResource,
                            QUrl(unique_id),
                            thumbnail_pixmap,
                        )
                    else:
                        logger.warning("Full-size image data not found for an image.")
                else:
                    logger.warning("Image source is missing or not in expected format.")

            # Convert the modified soup back to HTML and set it in the editor
            modified_html = str(soup)
            editor.setHtml(modified_html)

            logger.info(f"HTML file '{path}' loaded into editor with images reconstructed.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load HTML file: {str(e)}")
            logger.error(f"Failed to load HTML file: {str(e)}")

    def load_html_content(self, path, editor):
        """
        Load HTML content into the editor and reconstruct images.

        Args:
            path (str): The file path to the HTML content.
            editor (QTextEdit): The editor where the HTML content will be loaded.

        - Reads and sets the HTML content into the editor.
        - Reconstructs images from base64 data and updates the document's resources.
        """
        with open(path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Set the HTML content directly into the editor
        editor.setHtml(html_content)

        # Reconstruct images from the document's resources
        document = editor.document()
        resource_iterator = document.allResources()
        for resource_name in resource_iterator:
            if resource_name.type() == QTextDocument.ResourceType.ImageResource:
                image = document.resource(QTextDocument.ResourceType.ImageResource, resource_name)
                if isinstance(image, QPixmap):
                    # Generate a unique ID for the image
                    image_id = str(uuid4())
                    self.full_image_map[image_id] = image

                    # Update the image format with the new ID
                    image_format = QTextImageFormat()
                    image_format.setName(image_id)

                    # Add the image to the document's resources
                    document.addResource(QTextDocument.ResourceType.ImageResource, QUrl(image_id), image)

    def open_file_in_new_tab(self, file_path):
        """
        Open a specified file in a new tab and display its content.

        Args:
            file_path (str): The path to the file to be opened.

        - Reads the file content and sets it in a new tab's editor.
        - Adds the new tab to the tab widget and updates the file path mapping.
        - Logs the action for debugging purposes.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Create a new editor and set the file content
        editor = ClickableTextEdit()
        editor.setPlainText(content)

        # Add a new tab for the editor and set its properties
        tab_index = self.tab_widget.addTab(editor, os.path.basename(file_path))
        self.tab_widget.setCurrentIndex(tab_index)
        self.paths[tab_index] = file_path

        # Log the file opening
        logger.info(f"Opened file in new tab: {file_path}")

    def file_save(self, index=None):
        """
        Save the current document. If the file is unsaved, perform 'Save As'.

        Args:
            index (int, optional): The index of the tab to save. Defaults to the current tab.

        - Checks if the file already has an associated save path.
        - Performs a 'Save As' operation if no path exists.
        - Saves the file as HTML or plain text based on the file extension.
        - Marks the document as unmodified after saving.
        """
        if index is None:
            index = self.get_current_tab_index()  # Default to the current tab

        # Get the file path associated with the tab
        path = self.paths.get(index)

        if not path:
            # If no path exists, perform 'Save As'
            logger.info("No existing save path. Calling 'Save As'.")
            self.file_save_as(index)
        else:
            # Save as HTML or plain text based on file extension
            editor = self.tab_widget.widget(index)
            if path.endswith(".html"):
                # Save as HTML with JavaScript and images
                self.save_as_html_with_js(path, index)
                logger.info(f"File re-saved as HTML with embedded images: {path}")
            else:
                # Save as plain text
                content = editor.toPlainText()
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(content)
                editor.document().setModified(False)  # Mark document as saved
                logger.info(f"File re-saved as plain text: {path}")

    def file_save_as(self, index=None):
        """
        Save the current document to a user-specified location.

        Args:
            index (int, optional): The index of the tab to save. Defaults to the current tab.

        - Prompts the user to select a save location.
        - Saves the file as an HTML document with embedded images and JavaScript.
        """
        if index is None:
            index = self.get_current_tab_index()  # Default to the current tab

        # Open a Save File dialog for the user to specify the file path
        user_path, _ = QFileDialog.getSaveFileName(
            self, "Save As", "", "HTML documents (*.html)"
        )

        if user_path:
            # Save the file with JavaScript and embedded images
            self.save_as_html_with_js(user_path, index)

    def file_save_all(self):
        """
        Save all open documents.

        - Iterates through all open tabs.
        - Saves each tab's content to its associated path or prompts 'Save As' if no path exists.
        - Logs the results of each save operation.
        """
        for index in range(self.tab_widget.count()):
            path = self.paths.get(index)

            if path:
                # Save the file as HTML or plain text based on its extension
                editor = self.tab_widget.widget(index)
                if path.endswith(".html"):
                    self.save_as_html_with_js(path, index)  # Save as HTML with JavaScript
                    logger.info(f"File saved as HTML: {path}")
                else:
                    content = editor.toPlainText()
                    with open(path, 'w', encoding='utf-8') as file:
                        file.write(content)
                    editor.document().setModified(False)  # Mark document as saved
                    logger.info(f"File saved as plain text: {path}")
            else:
                # If no path exists, prompt 'Save As' for this tab
                logger.info(f"No existing save path for tab {index}. Calling 'Save As'.")
                self.file_save_as(index)

        logger.info("All open documents have been saved.")

    def save_as_html_with_js(self, path, index):
        """
        Save the document content as an HTML file with embedded images and JavaScript.

        Args:
            path (str): The file path to save the HTML content.
            index (int): The index of the tab containing the document to save.

        - Retrieves the current HTML content from the editor.
        - Embeds images into the HTML content using the editor's image maps.
        - Saves the final HTML with JavaScript to the specified path.
        - Updates the document's modified status and associated UI elements.
        """
        logger.info(f"Starting save_as_html_with_js for path: {path} and index: {index}")

        editor = self.tab_widget.widget(index)
        if editor:
            # Step 1: Get HTML content from the editor
            html_content = editor.document().toHtml()
            logger.debug("Original HTML content retrieved from editor.")

            # Step 2: Embed images into the HTML content
            embedded_html_content = self.embed_images_in_html_with_js(html_content, editor.document(), editor)
            logger.debug("HTML content after embedding images.")

            # Step 3: Save the HTML content with JavaScript
            with open(path, 'w', encoding='utf-8') as file:
                file.write(embedded_html_content)
                logger.info(f"Embedded HTML content with JavaScript saved to {path}")

            # Update paths and UI elements
            self.paths[index] = path  # Update file path for the tab
            self.tab_widget.setTabText(index, os.path.basename(path))  # Update tab text
            self.tab_widget.setTabToolTip(index, path)  # Update tab tooltip
            editor.document().setModified(False)  # Mark the document as saved
            logger.info(f"Document saved and UI updated for path: {path}")

    def embed_images_in_html_with_js(self, html_content, document, editor):
        """
        Embed both thumbnail and full-size images as Base64 in HTML with JavaScript for overlay viewing.

        Args:
            html_content (str): The original HTML content to process.
            document (QTextDocument): The document associated with the editor.
            editor (ClickableTextEdit): The editor containing the image maps.

        Returns:
            str: Modified HTML content with embedded images and interactive overlay functionality.
        """
        logger.info("Starting embed_images_in_html_with_js")
        soup = BeautifulSoup(html_content, 'html.parser')

        for img_tag in soup.find_all('img'):
            unique_id = img_tag.get('src')
            logger.debug(f"Found <img> tag with src (unique_id): {unique_id}")

            if unique_id:
                # Retrieve images from the editor's image maps
                base64_full_image = editor.full_image_map.get(unique_id)
                thumbnail_pixmap = editor.thumbnail_image_map.get(unique_id)
                if not base64_full_image or not thumbnail_pixmap:
                    logger.warning(f"No images found in editor's image maps for ID {unique_id}")
                    continue

                # Encode thumbnail image to Base64
                buffer = QBuffer()
                buffer.open(QBuffer.OpenModeFlag.ReadWrite)
                thumbnail_pixmap.save(buffer, "PNG")
                base64_thumbnail_image = base64.b64encode(buffer.data()).decode('utf-8')
                buffer.close()

                logger.info(f"Embedding Base64 images directly for ID {unique_id}")

                # Embed the Base64 string in the `src` attribute
                img_tag['src'] = f"data:image/png;base64,{base64_thumbnail_image}"
                # Update the `onclick` attribute for full-size image display
                img_tag['onclick'] = f"showFullImage('data:image/png;base64,{base64_full_image}')"
                img_tag['style'] = "cursor: pointer;"
                if img_tag.parent and img_tag.parent.name == 'a':
                    img_tag.parent['href'] = "javascript:void(0);"

        # Add overlay and script for full-size viewing if not already present
        if not soup.find(id="overlay"):
            logger.info("Adding JavaScript and overlay HTML for full-size image viewing.")
            overlay_script = """
            <script type="text/javascript">
                function showFullImage(fullImageData) {
                    var overlay = document.getElementById('overlay');
                    var fullImage = document.getElementById('fullImage');
                    fullImage.src = fullImageData;
                    overlay.style.display = 'flex';
                }

                function hideFullImage() {
                    document.getElementById('overlay').style.display = 'none';
                }
            </script>
            <div id="overlay" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%;
                 background-color:rgba(0,0,0,0.8); justify-content:center; align-items:center;">
                <img id="fullImage" src="" style="max-width:90%; max-height:90%;" alt="Full Size"/>
                <button onclick="hideFullImage()" style="position:absolute; top:20px; right:20px;
                        background-color:white; border:none; font-size:18px;">Close</button>
            </div>
            """
            soup.body.append(BeautifulSoup(overlay_script, 'html.parser'))

        logger.info("Completed embed_images_in_html_with_js")
        return str(soup)

    def convert_document_to_html(self, document):
        """
        Convert a QTextDocument to an HTML representation with embedded images as clickable thumbnails.

        Args:
            document (QTextDocument): The document to convert to HTML.

        Returns:
            str: The HTML content as a string.
        """
        cursor = QTextCursor(document)
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        # Initialize HTML structure
        html_output = "<html><body>"

        while not cursor.atEnd():
            block = cursor.block()
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                format = fragment.charFormat()

                if format.isImageFormat():
                    # Handle image formats
                    image_format = format.toImageFormat()
                    image_id = image_format.name()

                    if image_id in self.full_image_map:
                        pixmap = self.full_image_map[image_id]

                        # Convert full-size image to Base64
                        buffer_full = QBuffer()
                        buffer_full.open(QBuffer.OpenModeFlag.ReadWrite)
                        pixmap.save(buffer_full, "PNG")
                        base64_full = base64.b64encode(buffer_full.data()).decode('utf-8')
                        buffer_full.close()

                        # Retrieve thumbnail image from document resources
                        thumbnail_image = document.resource(QTextDocument.ResourceType.ImageResource, QUrl(image_id))
                        
                        if thumbnail_image:
                            # Convert thumbnail to Base64
                            buffer_thumb = QBuffer()
                            buffer_thumb.open(QBuffer.OpenModeFlag.ReadWrite)
                            thumbnail_image.save(buffer_thumb, "PNG")
                            base64_thumb = base64.b64encode(buffer_thumb.data()).decode('utf-8')
                            buffer_thumb.close()

                            # Embed as clickable thumbnail
                            width = image_format.width() if image_format.width() else pixmap.width()
                            height = image_format.height() if image_format.height() else pixmap.height()
                            thumbnail_html = (
                                f'<a href="data:image/png;base64,{base64_full}" target="_blank">'
                                f'<img src="data:image/png;base64,{base64_thumb}" '
                                f'width="{width}" height="{height}"/></a>'
                            )
                            html_output += thumbnail_html
                        else:
                            # Log a warning if thumbnail is missing
                            logger.warning(f"Thumbnail image for ID {image_id} not found in document resources.")
                    else:
                        # Log a warning if full-size image is missing
                        logger.warning(f"Image with ID {image_id} not found in full_image_map.")
                else:
                    # Handle text fragments
                    text = fragment.text().replace('\n', '<br>')
                    html_output += text

                it += 1  # Move to the next fragment

            # Add a line break after each block
            cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
            html_output += "<br>"

        html_output += "</body></html>"
        return html_output

    def get_tab_filename(self, index):
        """
        Get the filename associated with the tab at the given index.

        Args:
            index (int): The index of the tab.

        Returns:
            str or None: The filename (window title) of the tab, or None if no widget exists.
        """
        widget = self.tab_widget.widget(index)
        return widget.windowTitle() if widget else None

    def open_new_instance(self):
        """
        Open a new instance of the application with a cascaded window position.

        - Retrieves the current window position and offsets it for a cascading effect.
        - Launches a new instance of the application in a separate console window.
        - Logs the new instance position or displays an error if the operation fails.

        Raises:
            Exception: If an error occurs during the subprocess call, it is logged and displayed to the user.
        """
        try:
            # Get the current window position
            current_x = self.x()  # X-coordinate of the current window
            current_y = self.y()  # Y-coordinate of the current window

            # Offset for the cascade effect (e.g., 30 pixels down and right)
            offset = 30
            new_x = current_x + offset  # New X-coordinate for the cascaded window
            new_y = current_y + offset  # New Y-coordinate for the cascaded window

            # Start a new instance of the script with position arguments
            subprocess.Popen(
                ["python", __file__, str(new_x), str(new_y)],  # Pass new coordinates to the new instance
                creationflags=subprocess.CREATE_NEW_CONSOLE  # Ensure a new console is used for the instance
            )

            # Log the new instance creation with its position
            logger.info(f"Opened new instance at position ({new_x}, {new_y}).")

        except Exception as e:
            # Log the critical error with the exception details
            logger.critical("Failed to open a new instance.", exc_info=True)

            # Show a critical error message box to the user
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open a new instance:\n\n{str(e)}"
            )

    """------------------------ Editing and Formatting ------------------------"""
    
    def undo(self):
        """
        Undo the last action in the current editor.

        - Retrieves the current editor and performs an undo operation.
        - Logs the action for debugging purposes.
        """
        editor = self.get_current_editor()
        if editor:
            editor.undo()  # Perform undo operation
            logger.info("Undo action performed.")

    def redo(self):
        """
        Redo the last undone action in the current editor.

        - Retrieves the current editor and performs a redo operation.
        - Logs the action for debugging purposes.
        """
        editor = self.get_current_editor()
        if editor:
            editor.redo()  # Perform redo operation
            logger.info("Redo action performed.")

    def cut(self):
        """
        Cut the selected text in the current editor.

        - Retrieves the current editor and performs the cut operation.
        - Logs the action for debugging purposes.
        """
        editor = self.get_current_editor()
        if editor:
            editor.cut()  # Perform cut operation
            logger.info("Cut action performed.")

    def copy(self):
        """
        Copy the selected text in the current editor.

        - Retrieves the current editor and performs the copy operation.
        - Logs the action for debugging purposes.
        """
        editor = self.get_current_editor()
        if editor:
            editor.copy()  # Perform copy operation
            logger.info("Copy action performed.")

    def paste(self):
        """
        Paste text from the clipboard into the current editor.

        - Retrieves the current editor and performs the paste operation.
        - Logs the action for debugging purposes.
        """
        editor = self.get_current_editor()
        if editor:
            editor.paste()  # Perform paste operation
            logger.info("Paste action performed.")

    def set_alignment(self, alignment):
        """
        Set the alignment for the current text in the editor.

        Args:
            alignment (Qt.AlignmentFlag): The alignment type (e.g., AlignLeft, AlignCenter).

        - Retrieves the current editor and applies the specified alignment.
        - Logs the action for debugging purposes.
        """
        editor = self.get_current_editor()
        if editor:
            editor.setAlignment(alignment)  # Apply the specified alignment
            logger.info(f"Text alignment set to {alignment}.")

    def toggle_text_format(self, format_type, checked):
        """
        Toggle text formatting in the current editor.

        Args:
            format_type (str): The type of text formatting (e.g., "bold", "italic", "underline", "strikethrough").
            checked (bool): Whether the formatting should be enabled or disabled.

        - Retrieves the current editor and text cursor.
        - Applies the specified text formatting based on the format type and checked state.
        """
        editor = self.get_current_editor()
        cursor = editor.textCursor()
        format = QTextCharFormat()

        # Apply the specified text format
        if format_type == "bold":
            format.setFontWeight(QFont.Weight.Bold if checked else QFont.Weight.Normal)
        elif format_type == "italic":
            format.setFontItalic(checked)
        elif format_type == "underline":
            format.setFontUnderline(checked)
        elif format_type == "strikethrough":
            format.setFontStrikeOut(checked)

        # Merge the format with the current text selection
        cursor.mergeCharFormat(format)
        editor.setTextCursor(cursor)

    def clear_formatting(self):
        """
        Clear all text formatting in the current editor and reset to theme defaults.

        - Resets font, foreground color, and background to the current theme settings.
        - Applies formatting to the selected text if a selection exists, otherwise to the cursor position.
        """
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            format = QTextCharFormat()

            # Set theme default font and colors
            format.setFont(QFont(self.current_theme_settings["font_family"], self.current_theme_settings["font_size"]))
            format.setForeground(self.current_theme_settings["text_color"])
            format.setBackground(Qt.GlobalColor.transparent)  # Clear background color

            # Apply formatting to the selection or current cursor position
            if cursor.hasSelection():
                cursor.mergeCharFormat(format)  # Apply to selection
            else:
                editor.setCurrentFont(
                    QFont(self.current_theme_settings["font_family"], self.current_theme_settings["font_size"]))
                editor.mergeCurrentCharFormat(format)  # Apply to cursor position

            logger.info("Cleared formatting to current theme defaults.")

    def clear_formatting_near_thumbnail(self):
        """
        Clear text formatting if the cursor is within one space of a thumbnail image.

        - Checks for zero-width space characters (`\u200b`) near the cursor position.
        - Clears formatting if the cursor is adjacent to a thumbnail image.
        """
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()

            # Check the character to the left of the cursor
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor)
            left_buffer = cursor.selectedText() == '\u200b'
            cursor.clearSelection()  # Reset selection

            # Check the character to the right of the cursor
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
            right_buffer = cursor.selectedText() == '\u200b'
            cursor.clearSelection()  # Reset selection

            # Clear formatting if near a zero-width space
            if left_buffer or right_buffer:
                neutral_format = QTextCharFormat()  # Reset formatting
                cursor.setCharFormat(neutral_format)
                editor.setTextCursor(cursor)

    def add_spacing_after_image(self, editor):
        """
        Add spacing after an image in the editor based on the auto-space setting.

        Args:
            editor (QTextEdit): The editor where spacing will be added.

        - Checks if the auto-space feature is enabled.
        - Moves the cursor to the end of the last image.
        - Inserts a specified number of newlines based on the auto-space setting.
        """
        if self.auto_space_images_enabled:
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)  # Move cursor to the end of the last image
            cursor.insertText('\n' * self.auto_space_image_lines)  # Insert newlines
            editor.setTextCursor(cursor)  # Update the editor's cursor

    def toggle_auto_space_images(self, enabled):
        """Enable or disable automatic spacing after inserting images.
        
        Args:
            enabled (bool): True to enable auto-spacing, False to disable it.
        """
        self.auto_space_images_enabled = enabled
        app_settings["auto_space_images_enabled"] = enabled  # Update global settings
        save_settings(app_settings)  # Persist the change immediately
        logger.info(f"Auto Space Images set to {'enabled' if enabled else 'disabled'}.")

    def set_auto_space_image_lines(self):
        """Set the number of blank lines to insert after an image.
        
        This method updates the application's setting for auto-spacing after images 
        and ensures the UI reflects the selected number of lines.
        """
        action = self.sender()  # Identify which menu action triggered this method
        if action:
            self.auto_space_image_lines = action.data()  # Retrieve the selected line count
            app_settings["auto_space_image_lines"] = self.auto_space_image_lines  # Update global settings
            save_settings(app_settings)  # Persist the change immediately

            # Update menu actions to reflect the currently selected line count
            for action in self.line_count_menu.actions():
                action.setChecked(action.data() == self.auto_space_image_lines)
            logger.info(f"Auto Space Image Lines set to {self.auto_space_image_lines}.")

    """---------- Highlighter Methods ----------""" 
    
    def toggle_highlighting(self, checked):
        """
        Toggle highlighting on/off using the current highlight color.

        If `checked` is True, apply the highlight color to the selected text 
        or cursor position. If `checked` is False, remove the highlighting.
        """
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            format = cursor.charFormat()

            if checked:
                # Apply the current highlight and font color
                format.setBackground(self.current_highlight_color["highlight"])
                format.setForeground(self.current_highlight_color["font"])
            else:
                # Revert to the default background and text color
                format.setBackground(Qt.GlobalColor.transparent)
                format.setForeground(self.current_theme_settings["text_color"])

            cursor.mergeCharFormat(format)
            editor.setTextCursor(cursor)

    def on_highlight_color_selected(self):
        """
        Update the current highlight color based on user selection.

        If highlighting is active, apply the new color immediately to the current
        selection or cursor position.
        """
        action = self.sender()
        color = action.data()  # Retrieve the selected color data from QAction
        self.current_highlight_color = color  # Update the active highlight color

        if self.highlight_action.isChecked():
            self.apply_highlight_style(color)

    def create_highlight_action(self, name, colors):
        """
        Create a QAction with a preview label for the highlight color dropdown menu.

        The label visually represents the highlight color and font color for the 
        corresponding action.
        """
        action = QWidgetAction(self)
        label = QLabel(name)
        label.setFont(QFont(DEFAULT_FONT_FAMILY, 12))
        label.setStyleSheet(
            f"background-color: rgb({colors['highlight'].red()}, {colors['highlight'].green()}, {colors['highlight'].blue()}); "
            f"color: rgb({colors['font'].red()}, {colors['font'].green()}, {colors['font'].blue()}); "
            "padding: 5px; margin: 1px;"
        )
        action.setDefaultWidget(label)
        return action

    def apply_highlight_style(self, color):
        """
        Apply the selected highlight color to the current text cursor or selection.

        Merges the highlight color with the existing text styles, applying it only
        to the current selection if one exists, or to the cursor position otherwise.
        """
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            format = cursor.charFormat()

            # Apply the selected highlight and font color
            format.setBackground(color["highlight"])
            format.setForeground(color["font"])

            if cursor.hasSelection():
                cursor.setCharFormat(format)
            else:
                cursor.mergeCharFormat(format)

            editor.setTextCursor(cursor)
            editor.setFocus()

    """---------- List Methods ----------""" 
    
    def add_bullet_list(self):
        """
        Apply or toggle a bullet list format to the selected text or current line.
        
        - If the current block is already a bullet list, toggle the list format.
        - Otherwise, apply a bullet list style.
        - Allows indentation and bullet type changes via a helper method.
        """
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.beginEditBlock()
            
            # Check for existing list format
            current_list = cursor.currentList()
            if current_list:
                # Toggle bullet list: Remove existing list format
                block_format = cursor.blockFormat()
                block_format.setIndent(0)
                cursor.setBlockFormat(block_format)
            else:
                # Apply bullet list
                list_format = QTextListFormat()
                list_format.setStyle(QTextListFormat.Style.ListDisc)  # Default to disc bullets
                cursor.createList(list_format)
            
            cursor.endEditBlock()
            logger.info("Bullet list applied or toggled.")

    def change_numbered_list_indentation(self, increase_indent=True):
        """
        Adjust bullet indentation and cycle through bullet styles.
        
        - Increase or decrease indentation based on the `increase_indent` flag.
        - Cycle through bullet styles when the indentation level changes.
        
        Args:
            increase_indent (bool): If True, increase indentation; if False, decrease it.
        """
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.beginEditBlock()
            
            current_list = cursor.currentList()
            if current_list:
                # Get current list and block formats
                block_format = cursor.blockFormat()
                list_format = current_list.format()
                
                # Adjust indentation
                indent = block_format.indent()
                new_indent = indent + 1 if increase_indent else max(indent - 1, 0)
                block_format.setIndent(new_indent)
                cursor.setBlockFormat(block_format)
                
                # Cycle through bullet styles based on indentation level
                bullet_styles = [
                    QTextListFormat.Style.ListDisc,
                    QTextListFormat.Style.ListCircle,
                    QTextListFormat.Style.ListSquare
                ]
                new_style = bullet_styles[new_indent % len(bullet_styles)]
                list_format.setStyle(new_style)
                current_list.setFormat(list_format)
                
                logger.info(f"Bullet list style changed to {new_style}. Indentation level: {new_indent}.")
            else:
                logger.warning("No bullet list found to change indentation or style.")
            
            cursor.endEditBlock()

    def add_numbered_list(self):
        """
        Apply or remove a numbered list format to the selected text or current line.

        - If the current block is already a numbered list, remove the list format.
        - Otherwise, apply a numbered list style to the selected text or current line.
        """
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.beginEditBlock()
            
            # Check for existing numbered list
            current_list = cursor.currentList()
            if current_list and current_list.format().style() == QTextListFormat.Style.ListDecimal:
                # Remove numbered list by resetting block indentation
                block_format = cursor.blockFormat()
                block_format.setIndent(0)
                cursor.setBlockFormat(block_format)
            else:
                # Apply numbered list
                list_format = QTextListFormat()
                list_format.setStyle(QTextListFormat.Style.ListDecimal)
                cursor.createList(list_format)
            
            cursor.endEditBlock()
            logger.info("Numbered list applied.")

    def increase_indent(self):
        """
        Increase the indent level of the selected text or current line.

        - Adjusts the block indentation by incrementing the indent level by 1.
        """
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.beginEditBlock()

            # Increase the block indentation
            block_format = cursor.blockFormat()
            block_format.setIndent(block_format.indent() + 1)
            cursor.setBlockFormat(block_format)
            
            cursor.endEditBlock()
            logger.info("Increased indent level.")

    def decrease_indent(self):
        """
        Decrease the indent level of the selected text or current line.

        - Reduces the block indentation by decrementing the indent level, with a minimum of 0.
        """
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.beginEditBlock()

            # Decrease the block indentation
            block_format = cursor.blockFormat()
            block_format.setIndent(max(block_format.indent() - 1, 0))
            cursor.setBlockFormat(block_format)
            
            cursor.endEditBlock()
            logger.info("Decreased indent level.")

    """---------- Font Methods ----------""" 

    def apply_current_font_settings(self):
        """
        Apply the current font settings (family and size) to the text at the cursor 
        or selected text and save them to settings.

        This method ensures the selected or active text reflects the current font 
        family and size settings, and updates the app settings for persistence.
        """
        editor = self.get_current_editor()
        if editor:
            # Get the text cursor and define the desired font format
            cursor = editor.textCursor()
            format = QTextCharFormat()
            format.setFontFamily(self.current_font_family)
            format.setFontPointSize(self.current_font_size)

            # Apply the font settings to the selected text or cursor position
            if cursor.hasSelection():
                cursor.setCharFormat(format)
            else:
                editor.setCurrentFont(QFont(self.current_font_family, self.current_font_size))
                cursor.mergeCharFormat(format)

            # Persist changes to app settings
            app_settings["font_family"] = self.current_font_family
            app_settings["font_size"] = self.current_font_size
            save_settings(app_settings)  # Save settings to JSON

            logger.info(
                f"Applied and saved font family '{self.current_font_family}' "
                f"and size '{self.current_font_size}' at cursor or selection."
            )

    def apply_default_font_settings(self):
        """
        Apply the default font settings to the active editor.

        This method ensures the editor's font matches the global application settings, 
        reflecting the default font family and size.
        """
        editor = self.get_current_editor()
        if editor:
            # Set the editor's font to the current application defaults
            editor.setFont(QFont(self.current_font_family, self.current_font_size))

            # Ensure the text cursor format aligns with the font settings
            cursor = editor.textCursor()
            format = QTextCharFormat()
            format.setFontFamily(self.current_font_family)
            format.setFontPointSize(self.current_font_size)
            cursor.mergeCharFormat(format)
            editor.setTextCursor(cursor)

            logger.info(
                f"Applied default font settings: {self.current_font_family}, "
                f"{self.current_font_size}pt to the editor."
            )
    
    def on_font_change(self, font):
        """
        Update the current font family based on the user's selection and save the setting.

        Args:
            font (QFont): The new font selected by the user.
        """
        self.current_font_family = font.family()
        app_settings["font_family"] = self.current_font_family  # Update settings with new font family
        save_settings(app_settings)  # Persist change to settings
        self.apply_current_font_settings()
        logger.info(f"Font family changed to {self.current_font_family} and saved to settings.")

    def on_fontsize_change(self, size):
        """
        Update the current font size based on the user's selection and save the setting.

        Args:
            size (str): The new font size selected by the user.
        """
        try:
            self.current_font_size = int(size)
            app_settings["font_size"] = self.current_font_size  # Update settings with new font size
            save_settings(app_settings)  # Persist change to settings
            self.apply_current_font_settings()
            logger.info(f"Font size changed to {self.current_font_size} and saved to settings.")
        except ValueError:
            logger.error(f"Invalid font size: {size}")
        
    """------------------------ Auto Save ------------------------"""
    
    def handle_autosave_toggle(self):
        """
        Handle the state of the auto-save toggle button and save open tabs as needed.

        - Updates the toggle button style based on the current state.
        - Enables or disables the auto-save timer.
        - When auto-save is enabled for the first time, processes all open tabs to ensure they are tracked.
        - Updates and saves the "auto_save" setting.
        """
        is_checked = self.autosave_toggle_button.isChecked()
        self.update_toggle_style(is_checked)  # Update toggle button appearance

        if is_checked:
            self.enable_auto_save_timer()  # Enable auto-save timer

            # Initialize auto-save for open tabs if not already done
            if not hasattr(self, "auto_save_initialized") or not self.auto_save_initialized:
                self.auto_save_initialized = True
                for index in range(self.tab_widget.count()):
                    editor = self.tab_widget.widget(index)
                    if editor:
                        filename = self.get_tab_filename(index) or f"Untitled-{index}"
                        if not self.saved_files_panel.contains(filename):
                            self.add_to_saved_files_panel(index, editor.toPlainText())  # Add to saved files panel
                            logger.info(f"Tab '{filename}' added to saved files panel during initial auto-save setup.")
        else:
            self.disable_auto_save_timer()  # Disable auto-save timer

        # Update and save the "auto_save" setting
        app_settings["auto_save"] = is_checked
        save_settings(app_settings)  # Save the updated setting
        logger.info(f"Auto Save setting updated to: {'enabled' if is_checked else 'disabled'}")

    def update_toggle_style(self, is_checked):
        """
        Update the style of the auto-save toggle button based on its state.

        Args:
            is_checked (bool): True if the toggle is ON, False if OFF.

        - Applies green styling and sets the text to "ON" for the enabled state.
        - Applies gray styling and sets the text to "OFF" for the disabled state.
        """
        if is_checked:
            # Style for "ON" state
            self.autosave_toggle_button.setStyleSheet(
                """
                QPushButton {
                    background-color: #4CAF50;  /* Green for ON */
                    color: white;
                    border-radius: 10px;
                    min-width: 40px;
                    min-height: 20px;
                    font-weight: bold;
                }
                """
            )
            self.autosave_toggle_button.setText("ON")  # Set button text to "ON"
        else:
            # Style for "OFF" state
            self.autosave_toggle_button.setStyleSheet(
                """
                QPushButton {
                    background-color: #ccc;  /* Gray for OFF */
                    color: black;
                    border-radius: 10px;
                    min-width: 40px;
                    min-height: 20px;
                    font-weight: bold;
                }
                """
            )
            self.autosave_toggle_button.setText("OFF")  # Set button text to "OFF"

    def enable_auto_save_timer(self):
        """
        Enable the auto-save timer to periodically save content.

        - Creates a QTimer instance for auto-saving.
        - Sets the timeout interval (default: 5000ms = 5 seconds).
        - Connects the timer to the auto-save handler for the current tab.
        """
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save_current_tab)  # Connect timer to auto-save handler
        self.auto_save_timer.start(5000)  # Start timer with a 5-second interval
        logger.info("Auto-save timer started.")

    def disable_auto_save_timer(self):
        """
        Disable the auto-save timer.

        - Stops the timer if it exists and removes the reference.
        - Logs the action for debugging purposes.
        """
        if hasattr(self, 'auto_save_timer'):
            self.auto_save_timer.stop()  # Stop the timer
            del self.auto_save_timer  # Remove timer reference
        logger.info("Auto-save timer stopped.")

    def auto_save_current_tab(self, index=None):
        """
        Automatically save the content of the current tab.

        Args:
            index (int, optional): The index of the tab to auto-save. Defaults to the current tab.

        - Checks if the tab's content is modified.
        - Saves the content to the associated file path if available.
        - Logs warnings if no editor or file path is found, or skips unmodified tabs.
        """
        if index is None:
            index = self.tab_widget.currentIndex()  # Default to the current tab

        editor = self.tab_widget.widget(index)

        if editor is None:
            logger.warning(f"No editor found for tab {index}; auto-save skipped.")
            return

        if editor.document().isModified():
            content = editor.toPlainText()  # Get tab content
            file_path = self.paths.get(index)

            if file_path:
                # Save content to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                editor.document().setModified(False)  # Mark document as saved
                logger.info(f"Tab {index} auto-saved to {file_path}.")
            else:
                logger.warning(f"No file path set for tab {index}; auto-save skipped.")
        else:
            logger.info(f"Tab {index} not modified; auto-save skipped.")

    """------------------------ Checklists ------------------------"""

    def load_checklists_to_dropdown(self):
        """
        Load checklists into the dropdown menu.

        - Ensures the dropdown is initialized before performing operations.
        - Clears existing items and adds a placeholder ("Select Checklist") as the first item.
        - Searches for `.json` files in the checklists folder and populates the dropdown.
        - Disables the dropdown and provides user feedback if no checklists are found.
        """
        # Check if the dropdown is initialized
        if not hasattr(self, 'checklist_dropdown') or not self.checklist_dropdown:
            logger.error("Checklist dropdown is not initialized. Operation skipped.")
            return

        # Clear the dropdown and add a placeholder item
        self.checklist_dropdown.clear()
        self.checklist_dropdown.addItem("Select Checklist")  # Placeholder for unselected state

        # Ensure the checklists folder exists
        os.makedirs(CHECKLISTS_FOLDER, exist_ok=True)

        # Find all checklist files in the folder
        checklists = [f[:-5] for f in os.listdir(CHECKLISTS_FOLDER) if f.endswith(".json")]

        if not checklists:
            # No checklists found, disable the dropdown and notify the user
            logger.warning("No checklists found. Disabling dropdown.")
            self.checklist_dropdown.setEnabled(False)
            QMessageBox.information(self, "No Checklists", "No checklists found. Create a new checklist to begin.")
        else:
            # Enable the dropdown and populate it with checklist names
            self.checklist_dropdown.setEnabled(True)
            for checklist_name in checklists:
                logger.info(f"Adding checklist to dropdown: {checklist_name}")
                self.checklist_dropdown.addItem(checklist_name)

    def open_selected_checklist(self, index):
        """
        Dynamically render and display the selected checklist based on the JSON structure.

        - Supports Main Title, Title, Description, Task, Checklist Items, and Notes.
        - Handles an arbitrary order of elements as defined in the JSON file.
        - Validates the JSON file and ensures proper formatting.

        Args:
            index (int): The index of the selected item in the dropdown menu.
        """
        # Skip operation if the placeholder is selected
        if index == 0:
            logger.warning("No checklist selected. Skipping operation.")
            QMessageBox.warning(self, "No Checklist Selected", "Please select a valid checklist from the dropdown.")
            return

        # Get the selected checklist name
        checklist_name = self.checklist_dropdown.itemText(index).strip()

        # Validate the checklist name
        if not checklist_name:
            logger.error("Invalid checklist name: null or empty.")
            QMessageBox.critical(self, "Error", "Invalid checklist name. Please select a valid checklist.")
            return

        # Construct the file path for the selected checklist
        checklist_path = os.path.join(CHECKLISTS_FOLDER, f"{checklist_name}.json")

        # Ensure the checklist file exists
        if not os.path.exists(checklist_path):
            logger.error(f"Checklist file '{checklist_path}' does not exist.")
            QMessageBox.critical(self, "Error", f"Checklist '{checklist_name}' not found.")
            return

        try:
            # Load the JSON file
            with open(checklist_path, "r", encoding="utf-8") as f:
                checklist_data = json.load(f)

            if "checklists" not in checklist_data or not isinstance(checklist_data["checklists"], list):
                raise ValueError("Checklist JSON structure is invalid or missing 'checklists' key.")

            for checklist in checklist_data["checklists"]:
                dialog = QDialog(self)
                dialog.setWindowTitle(checklist.get("main_title", "Checklist"))
                dialog.setGeometry(300, 300, 600, 800)

                layout = QVBoxLayout(dialog)

                # Add Main Title
                if "main_title" in checklist:
                    main_title_label = QLabel(f"<b style='font-size:20px'>{checklist['main_title']}</b>")
                    main_title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    layout.addWidget(main_title_label)

                # Process each item dynamically
                for item in checklist.get("items", []):
                    item_type = item.get("type")
                    content = item.get("content", "")

                    if item_type == "title":
                        title_label = QLabel(f"<b style='font-size:18px'>{content}</b>")
                        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                        layout.addWidget(title_label)

                    elif item_type == "description":
                        description_label = QLabel(f"<div style='font-size:14px; margin-left:20px'>{content}</div>")
                        description_label.setWordWrap(True)
                        layout.addWidget(description_label)

                    elif item_type == "task":
                        task_label = QLabel(f"<div style='font-size:16px; margin-left:20px;'><li>{content}</li></div>")
                        task_label.setWordWrap(True)
                        layout.addWidget(task_label)

                        # Add task details if available
                        if "details" in item:
                            details_label = QLabel(f"<div style='font-size:14px; margin-left:40px'>{item['details']}</div>")
                            details_label.setWordWrap(True)
                            layout.addWidget(details_label)

                        # Add checklist items if available
                        if "checklist" in item and isinstance(item["checklist"], list):
                            for checklist_item in item["checklist"]:
                                checklist_checkbox = QCheckBox(f"{checklist_item}")
                                checklist_checkbox.setStyleSheet("margin-left: 60px;")
                                layout.addWidget(checklist_checkbox)

                    elif item_type == "note":
                        note_label = QLabel(f"<i style='font-size:14px; margin-left:20px'>{content}</i>")
                        note_label.setWordWrap(True)
                        layout.addWidget(note_label)

                # Add Close Button
                close_button = QPushButton("Close", dialog)
                close_button.clicked.connect(dialog.close)
                layout.addWidget(close_button)

                dialog.setLayout(layout)
                dialog.exec()

        except Exception as e:
            logger.error(f"Failed to open checklist '{checklist_name}': {e}")
            QMessageBox.critical(self, "Error", f"Could not open checklist '{checklist_name}'.\n\nError: {str(e)}")

    def display_checklist(self, checklist_name, items):
        """
        Display the checklist in a dialog.

        - Validates if the checklist has items before displaying.
        - Constructs a dialog with checkboxes for each item in the checklist.
        - Provides a "Close" button for user interaction.

        Args:
            checklist_name (str): The name of the checklist being displayed.
            items (list): A list of items in the checklist.
        """
        # Check if the checklist is empty
        if not items:
            logger.warning(f"Checklist '{checklist_name}' is empty.")
            QMessageBox.information(self, "Empty Checklist", f"The checklist '{checklist_name}' is empty.")
            return

        # Create a dialog to display the checklist
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Checklist: {checklist_name}")
        dialog.setGeometry(300, 300, 400, 500)

        # Layout to hold the checklist items
        layout = QVBoxLayout(dialog)

        # List widget to display items with checkboxes
        list_widget = QListWidget(dialog)
        layout.addWidget(list_widget)

        # Add each checklist item as a checkbox
        for item in items:
            list_item = QListWidgetItem(list_widget)
            checkbox = QCheckBox(item)
            checkbox.stateChanged.connect(lambda state, text=item: self.log_checked_item(text, state))
            list_widget.setItemWidget(list_item, checkbox)

        # Add a "Close" button to the dialog
        close_button = QPushButton("Close", dialog)
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)

        # Set layout and display the dialog
        dialog.setLayout(layout)
        dialog.exec()

    def log_checked_item(self, item, state):
        """
        Log the state of a checklist item when it is checked or unchecked.

        - Captures the state change of each item.
        - Logs the action in the main editor.

        Args:
            item (str): The text of the checklist item.
            state (int): The state of the checkbox (Checked or Unchecked).
        """
        if state == Qt.CheckState.Checked:
            logger.info(f"Checklist item checked: {item}")
            self.add_text_to_current_tab(f"Checked off: {item}")
        elif state == Qt.CheckState.Unchecked:
            logger.info(f"Checklist item unchecked: {item}")

    def open_checklist_manager(self):
        """
        Open the Checklist Manager dialog.

        - Creates an instance of the ChecklistManager.
        - Displays the dialog for managing checklists.
        """
        self.checklist_manager = ChecklistManager(self)  # Initialize the Checklist Manager
        self.checklist_manager.exec()  # Open the dialog

    """------------------------ Capture and OCR ------------------------"""

    def set_capture_area(self):
        """
        Launch an overlay to set the capture area and trigger the capture process if an area is set.

        - Creates and displays snipping overlays on all available screens.
        - Defines a callback to handle overlay closure and process the selected capture area.
        """
        screens = QGuiApplication.screens()
        self.overlays = []  # Store overlay instances

        def close_all_overlays(rect):
            """
            Close all overlays and process the selected capture area.

            Args:
                rect (QRect): The rectangle defining the selected capture area.
            """
            for overlay in self.overlays:
                overlay.close()
            self.on_capture_area_set(rect)  # Trigger capture area handling

        # Create and show an overlay on each screen
        for screen in screens:
            screen_rect = screen.geometry()
            overlay = SnippingOverlay(screen_rect, close_all_callback=close_all_overlays)
            overlay.showFullScreen()
            overlay.activateWindow()
            overlay.raise_()
            self.overlays.append(overlay)  # Keep track of overlays

        logger.info("Snipping tool initialized on all screens.")

    def capture(self):
        """
        Override the capture method to insert an image and add spacing after it.

        - Checks if the capture area is set; if not, launches the capture area tool.
        - Captures the pixmap of the pre-set area and inserts it into the editor.
        - Adds spacing after the inserted image based on auto-spacing settings.
        """
        if not self.capture_area_set:
            self.capture_in_progress = True
            self.set_capture_area()  # Launch the capture area tool
            return

        pixmap = self.capture_pixmap(self.capture_area)  # Capture the pre-set area
        if pixmap:
            self.insert_image_with_thumbnail(pixmap)  # Insert the captured image
            self.add_spacing_after_image(self.get_current_editor())  # Add spacing below the image
        else:
            # Notify the user if the capture fails
            QMessageBox.warning(self, "Capture Failed", "Failed to capture the pre-set area.")

    def perform_ocr(self):
        """
        Launch an OCR overlay for selecting a screen area and extracting text from the selected region.

        - Creates and displays snipping overlays on all available screens.
        - Defines a callback to handle overlay closure and process the selected OCR area.
        """
        screens = QGuiApplication.screens()
        self.overlays = []  # Store overlay instances

        def close_all_overlays(rect):
            """
            Close all overlays and perform OCR on the selected area.

            Args:
                rect (QRect): The rectangle defining the selected area for OCR.
            """
            for overlay in self.overlays:
                overlay.close()
            self.ocr_from_selected_area(rect)  # Trigger OCR processing for the selected area

        # Create and show an overlay on each screen
        for screen in screens:
            screen_rect = screen.geometry()
            overlay = SnippingOverlay(screen_rect, close_all_callback=close_all_overlays)
            overlay.showFullScreen()
            overlay.activateWindow()
            overlay.raise_()
            self.overlays.append(overlay)  # Keep track of overlays

        logger.info("OCR overlay initialized.")

    def screen_grab(self):
        """
        Launch a screen grab overlay and add spacing after inserting the captured image.

        - Displays snipping overlays on all screens for selecting a capture area.
        - Captures the selected screen area as an image (pixmap).
        - Inserts the captured image into the editor and adds spacing below it.
        """
        screens = QGuiApplication.screens()
        self.overlays = []  # Store overlay instances

        def close_all_overlays(rect):
            """
            Close all overlays and handle the captured screen area.

            Args:
                rect (QRect): The rectangle defining the selected screen area.
            """
            for overlay in self.overlays:
                overlay.close()
            pixmap = self.capture_pixmap(rect)  # Capture the selected area
            if pixmap:
                self.insert_image_with_thumbnail(pixmap)  # Insert the image into the editor
                self.add_spacing_after_image(self.get_current_editor())  # Add spacing below the image

        # Create and show an overlay on each screen
        for screen in screens:
            screen_rect = screen.geometry()
            overlay = SnippingOverlay(screen_rect, close_all_callback=close_all_overlays)
            overlay.showFullScreen()
            overlay.activateWindow()
            overlay.raise_()
            self.overlays.append(overlay)  # Keep track of overlays

        logger.info("Screen grab overlay initialized.")

    def capture_pixmap(self, snip_rect):
        """
        Capture a pixmap of the specified area within the given screen rectangle.

        Args:
            snip_rect (QRect): The rectangle defining the area to capture.

        Returns:
            QPixmap or None: The captured pixmap if successful, otherwise None.
        
        - Identifies the screen containing the capture area or falls back to the primary screen.
        - Adjusts the capture area coordinates relative to the screen.
        - Captures the screenshot of the specified area and returns it.
        """
        screens = QGuiApplication.screens()
        selected_screen = None

        # Determine which screen contains the snip_rect's center
        for screen in screens:
            if screen.geometry().contains(snip_rect.center()):
                selected_screen = screen
                break
        if not selected_screen:
            selected_screen = QGuiApplication.primaryScreen()  # Default to primary screen

        # Adjust capture coordinates relative to the selected screen
        screen_rect = selected_screen.geometry()
        adjusted_x = snip_rect.x() - screen_rect.x()
        adjusted_y = snip_rect.y() - screen_rect.y()

        # Capture the specified area within the screen
        pixmap = selected_screen.grabWindow(0, adjusted_x, adjusted_y, snip_rect.width(), snip_rect.height())
        return pixmap if not pixmap.isNull() else None

    def insert_image_with_thumbnail(self, pixmap):
        """
        Insert an image into the editor as a thumbnail with a link to the full-size image.

        Args:
            pixmap (QPixmap): The full-size image to be inserted.

        - Generates a unique ID for the image and creates a thumbnail.
        - Encodes the full-size image in base64 for embedding.
        - Inserts the thumbnail into the editor with a link to display the full image.
        - Stores the image and thumbnail in mapping dictionaries for future access.
        """
        unique_id = str(uuid4())
        logger.debug(f"Generated unique_id for image: {unique_id}")

        # Generate a scaled thumbnail
        thumbnail_pixmap = pixmap.scaled(
            200,
            150,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        logger.debug(f"Thumbnail generated for image ID {unique_id}")

        # Base64 encode the full-size image
        buffer_full = QBuffer()
        buffer_full.open(QBuffer.OpenModeFlag.ReadWrite)
        pixmap.save(buffer_full, "PNG")
        base64_full_image = base64.b64encode(buffer_full.data()).decode('utf-8')
        buffer_full.close()
        logger.debug(f"Base64 encoding complete for full image with ID {unique_id}, length: {len(base64_full_image)}")

        # Insert the thumbnail with a link to the full-size image
        editor = self.get_current_editor()
        if editor:
            # Add the thumbnail to document resources
            editor.document().addResource(
                QTextDocument.ResourceType.ImageResource,
                QUrl(unique_id),
                thumbnail_pixmap,
            )
            logger.debug(f"Thumbnail image resource added to document for ID {unique_id}")

            # Insert the image as HTML with formatting isolation
            cursor = editor.textCursor()
            cursor.beginEditBlock()
            cursor.insertText('\u200b')  # Zero-width space
            html = f'<a href="{unique_id}" onclick="showFullImage(\'data:image/png;base64,{base64_full_image}\')"><img src="{unique_id}" width="200" height="150" style="cursor:pointer;"/></a>'
            cursor.insertHtml(html)
            cursor.movePosition(QTextCursor.MoveOperation.Right)
            cursor.insertText('\u200b')  # Zero-width space
            cursor.setCharFormat(QTextCharFormat())
            cursor.endEditBlock()
            editor.setTextCursor(cursor)

            # Store the full image and thumbnail in the image maps
            self.full_image_map[unique_id] = base64_full_image
            self.thumbnail_image_map[unique_id] = thumbnail_pixmap
            logger.info(f"Full-size image and thumbnail stored for ID {unique_id}")

            # Assign image maps to the editor
            editor.full_image_map = self.full_image_map
            editor.thumbnail_image_map = self.thumbnail_image_map

    def ocr_from_selected_area(self, snip_rect):
        """
        Perform OCR on the selected screen area and insert the extracted text into the editor.

        Args:
            snip_rect (QRect): The rectangle defining the area to capture and process.

        - Captures the specified area as an image.
        - Converts the image to text using Tesseract OCR.
        - Inserts the extracted text into the current editor at the cursor position.
        """
        pixmap = self.capture_pixmap(snip_rect)  # Capture the selected screen area
        if pixmap:
            # Save the captured image to a buffer
            buffer = QBuffer()
            buffer.open(QBuffer.OpenModeFlag.ReadWrite)
            pixmap.save(buffer, "PNG")
            buffer.seek(0)

            # Perform OCR using Tesseract
            image_data = BytesIO(buffer.data())  # Convert buffer data to BytesIO
            pil_image = Image.open(image_data)  # Open image with PIL
            ocr_text = pytesseract.image_to_string(pil_image)  # Extract text

            # Insert the extracted text into the current editor
            editor = self.get_current_editor()
            if editor and isinstance(editor, QTextEdit):
                cursor = editor.textCursor()
                cursor.insertText(ocr_text)  # Insert OCR text
                logger.info("OCR text inserted into document.")

    """------------------------ Spell Check ------------------------"""

    def toggle_real_time_spell_check(self, checked):
        """
        Enable or disable real-time spell checking based on the toggle state.

        Args:
            checked (bool): True to enable real-time spell checking, False to disable.

        - When enabled:
            - Sets up a timer to delay spell checking after text changes.
            - Connects the timer to the `perform_real_time_spell_check` method.
        - When disabled:
            - Disconnects the spell check from text change signals to prevent interference.
        """
        editor = self.get_current_editor()
        if checked:
            # Initialize the spell check timer
            self.spell_check_timer = QTimer()
            self.spell_check_timer.setSingleShot(True)
            self.spell_check_timer.timeout.connect(self.perform_real_time_spell_check)

            # Connect to text changes if an editor is active
            if editor:
                editor.textChanged.connect(lambda: self.spell_check_timer.start(500))  # Start timer on text change
            logger.info("Real-time spell check enabled.")
        else:
            # Disconnect textChanged signal to disable real-time spell checking
            if editor:
                try:
                    editor.textChanged.disconnect()  # Safely disconnect if connected
                except TypeError:
                    pass  # Ignore if already disconnected
            logger.info("Real-time spell check disabled.")

    def edit_custom_dictionary(self):
        """
        Open the Custom Dictionary dialog for managing user-defined words.

        - Creates an instance of the CustomDictionaryDialog.
        - Displays the dialog in a modal fashion using `exec()`.
        """
        dialog = CustomDictionaryDialog(self)  # Initialize the dialog
        dialog.exec()  # Open the dialog modally

    def perform_real_time_spell_check(self):
        """
        Underline misspelled words in real-time without affecting images or other formatting.

        - Iterates over each text fragment in the document.
        - Skips fragments representing images.
        - Removes existing spell check underlines before applying new ones.
        - Delegates word spell-checking to `check_text_fragment`.
        """
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.beginEditBlock()  # Group changes for efficiency

            # Start from the first block of the document
            block = editor.document().firstBlock()
            while block.isValid():
                it = block.begin()
                while not it.atEnd():
                    fragment = it.fragment()
                    if fragment.isValid():
                        # Skip image fragments
                        if fragment.charFormat().isImageFormat():
                            pass
                        else:
                            # Get fragment positions
                            start_pos = fragment.position()
                            end_pos = start_pos + fragment.length()

                            # Create a cursor for the fragment
                            fragment_cursor = QTextCursor(editor.document())
                            fragment_cursor.setPosition(start_pos)
                            fragment_cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)

                            # Remove existing underlines
                            format = QTextCharFormat()
                            format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.NoUnderline)
                            fragment_cursor.mergeCharFormat(format)

                            # Extract and check text from the fragment
                            text = fragment.text()
                            if text:
                                self.check_text_fragment(fragment_cursor, text)
                    it += 1
                block = block.next()  # Move to the next block
            cursor.endEditBlock()

    def check_text_fragment(self, cursor, text):
        """
        Check a text fragment for spelling errors and apply underlines.

        - Tokenizes the text using word boundaries.
        - For each word, checks if it is misspelled.
        - Applies a red spell-check underline to misspelled words.
        """
        # Tokenize text into words using regex
        words = re.finditer(r'\b\w+\b', text)
        for word_match in words:
            word = word_match.group()
            start_offset = word_match.start()
            end_offset = word_match.end()

            # Calculate absolute positions in the document
            start = cursor.selectionStart() + start_offset
            end = cursor.selectionStart() + end_offset

            # Create a cursor for the specific word
            word_cursor = QTextCursor(cursor.document())
            word_cursor.setPosition(start)
            word_cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

            # Check if the word is misspelled
            if word not in spell:  # `spell` should be an instance of a spell-checking library
                # Apply red underline for misspelled words
                misspelled_format = QTextCharFormat()
                misspelled_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
                misspelled_format.setUnderlineColor(Qt.GlobalColor.red)
                word_cursor.mergeCharFormat(misspelled_format)

    """---------- Custom Context/Spellchek Methods ----------""" 

    def populate_spell_check_menu(self, word, cursor, spell_check_menu):
        """
        Populate the spell-check menu with suggestions and options.

        - **Suggestions**: Add a list of possible replacements for the misspelled word.
        - **Add to Dictionary**: Option to add the misspelled word to the custom dictionary.
        
        Args:
            word (str): The misspelled word to provide suggestions for.
            cursor (QTextCursor): The cursor pointing to the misspelled word in the document.
            spell_check_menu (QMenu): The menu to populate with suggestions.
        """
        suggestions = spell.candidates(word)
        for suggestion in suggestions:
            action = QAction(suggestion, self)
            action.triggered.connect(lambda _, sug=suggestion: self.replace_word(cursor, sug))
            spell_check_menu.addAction(action)

        # Option to add the word to the dictionary
        add_to_dict_action = QAction("Add to Dictionary", self)
        add_to_dict_action.triggered.connect(lambda _, w=word: self.add_word_to_dictionary(w))
        spell_check_menu.addAction(add_to_dict_action)

    def replace_word(self, editor, start_pos, end_pos, replacement):
        """
        Replace a misspelled word with the provided replacement.

        - Highlights the misspelled word using the start and end positions.
        - Replaces the word and updates the document content.
        - Re-runs spell check to refresh underlines.

        Args:
            editor (QTextEdit): The editor instance where the word exists.
            start_pos (int): Start position of the word in the document.
            end_pos (int): End position of the word in the document.
            replacement (str): The replacement word to insert.
        """
        cursor = QTextCursor(editor.document())
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(replacement)
        cursor.endEditBlock()

        # Re-run spell check to update underlines
        self.perform_real_time_spell_check()

    def add_word_to_dictionary(self, word):
        """
        Add a new word to the custom dictionary.

        - Updates the spell checker with the new word.
        - Saves the updated dictionary to disk.
        - Refreshes the document to remove underlines from the added word.

        Args:
            word (str): The word to add to the custom dictionary.
        """
        spell.word_frequency.add(word)
        self.save_custom_dictionary()
        QMessageBox.information(self, "Word Added", f"'{word}' has been added to the dictionary.")
        
        # Re-run spell check to update underlines
        self.perform_real_time_spell_check()

    def save_custom_dictionary(self):
        """
        Save the current state of the custom dictionary to a file.

        - Persists the dictionary in JSON format for future use.
        """
        with open(CUSTOM_DICT_PATH, 'w') as f:
            json.dump(list(spell.word_frequency.dictionary.keys()), f, indent=4)
        logger.info("Custom dictionary saved.")

    """---------- Context Window Methods ----------""" 
    
    def setup_custom_context_menu(self):
        """
        Set up the context menu policy for the current editor.

        - Configures the editor to show a custom context menu on right-click.
        - Connects the context menu event to the `show_custom_context_menu` method.
        """
        editor = self.get_current_editor()
        if editor:
            editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            editor.customContextMenuRequested.connect(self.show_custom_context_menu)

    def show_custom_context_menu(self, pos):
        """
        Create and display a custom context menu with various options.

        - **Editing Options**: Cut, Copy, Paste, and Delete.
        - **Spell-Checking**: Suggestions for misspelled words and an option to add words to the dictionary.
        - **Formatting**: Bold, Italic, Underline, Strikethrough, and Highlight with color options.
        - Uses a consistent dark gray theme for styling.
        """
        editor = self.get_current_editor()
        if not editor:
            return  # Exit if there's no active editor

        # Initialize the context menu with custom styling
        context_menu = QMenu(editor)
        context_menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;  /* Dark gray background */
                color: #f0f0f0;             /* Light gray text */
                border: 1px solid #5a5a5a;  /* Border color */
            }
            QMenu::item {
                background-color: transparent;
                padding: 4px 24px;
            }
            QMenu::item:selected {
                background-color: #3a3a3a;  /* Slightly lighter gray on selection */
                color: #ffffff;             /* White text on selection */
            }
            QMenu::separator {
                height: 1px;
                background: #5a5a5a;        /* Gray separator line */
                margin-left: 10px;
                margin-right: 10px;
            }
        """)

        # Add basic editing actions
        cut_action = QAction("Cut", editor)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(editor.cut)
        context_menu.addAction(cut_action)

        copy_action = QAction("Copy", editor)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(editor.copy)
        context_menu.addAction(copy_action)

        paste_action = QAction("Paste", editor)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(editor.paste)
        context_menu.addAction(paste_action)

        delete_action = QAction("Delete", editor)
        delete_action.triggered.connect(lambda: editor.textCursor().removeSelectedText())
        context_menu.addAction(delete_action)

        context_menu.addSeparator()

        # Get the cursor at the position where the context menu was requested
        cursor = editor.cursorForPosition(pos)
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        word = cursor.selectedText()
        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()

        # Spell-check options
        if word and word not in spell:
            spell_menu = QMenu("Spelling Suggestions", editor)
            spell_menu.setStyleSheet(context_menu.styleSheet())  # Apply the same style

            # Add suggestions from the spell checker
            suggestions = spell.candidates(word)
            if suggestions:
                for suggestion in suggestions:
                    action = QAction(suggestion, editor)
                    action.triggered.connect(lambda _, sug=suggestion, s=start_pos, e=end_pos: self.replace_word(editor, s, e, sug))
                    spell_menu.addAction(action)

            # Add an option to add the word to the custom dictionary
            add_to_dict_action = QAction("Add to Dictionary", editor)
            add_to_dict_action.triggered.connect(lambda _, w=word: self.add_word_to_dictionary(w))
            spell_menu.addAction(add_to_dict_action)

            context_menu.addMenu(spell_menu)

        context_menu.addSeparator()

        # Text formatting options
        bold_action = QAction("Bold", editor)
        bold_action.setCheckable(True)
        bold_action.setChecked(editor.fontWeight() == QFont.Weight.Bold)
        bold_action.triggered.connect(lambda: self.toggle_text_format("bold", bold_action.isChecked()))
        context_menu.addAction(bold_action)

        italic_action = QAction("Italic", editor)
        italic_action.setCheckable(True)
        italic_action.setChecked(editor.fontItalic())
        italic_action.triggered.connect(lambda: self.toggle_text_format("italic", italic_action.isChecked()))
        context_menu.addAction(italic_action)

        underline_action = QAction("Underline", editor)
        underline_action.setCheckable(True)
        underline_action.setChecked(editor.fontUnderline())
        underline_action.triggered.connect(lambda: self.toggle_text_format("underline", underline_action.isChecked()))
        context_menu.addAction(underline_action)

        strikethrough_action = QAction("Strikethrough", editor)
        strikethrough_action.setCheckable(True)
        strikethrough_action.triggered.connect(lambda: self.toggle_text_format("strikethrough", strikethrough_action.isChecked()))
        context_menu.addAction(strikethrough_action)

        # Highlight submenu for selecting colors
        highlight_menu = QMenu("Highlight", editor)
        highlight_menu.setStyleSheet(context_menu.styleSheet())  # Apply the same style
        for name, colors in HIGHLIGHT_STYLES.items():
            color_action = QAction(name, editor)
            color_action.triggered.connect(lambda _, col=colors: self.apply_highlight_style(col))
            highlight_menu.addAction(color_action)
        context_menu.addMenu(highlight_menu)

        # Show the context menu at the requested position
        context_menu.exec(editor.viewport().mapToGlobal(pos))

    """------------------------ Helper Methods ------------------------"""
    
    def add_to_saved_files_panel(self, index, content):
        """
        Add the content of the specified tab to the saved files panel.

        Args:
            index (int): The index of the tab to add.
            content (str): The content of the tab to save.

        - Retrieves the filename of the tab or generates a default name if unavailable.
        - Adds the file to the saved files panel if it doesn't already exist.
        - Logs the addition for debugging purposes.
        """
        filename = self.get_tab_filename(index) or f"Untitled-{index}"  # Retrieve or generate filename
        if not self.saved_files_panel.contains(filename):  # Check for duplicates
            self.saved_files_panel.add_item(filename, content)  # Add the file to the panel
            logging.info(f"Added '{filename}' to saved files panel.")

    def is_tab_empty(self, editor):
        """
        Check if the editor tab is empty (contains no text or images).

        Args:
            editor (QTextEdit): The editor to check.

        Returns:
            bool: True if the tab is empty, False otherwise.

        - Returns True if the editor is None.
        - Checks for the absence of text and images in the editor.
        """
        if editor is None:
            return True  # Consider the tab empty if no editor is present
        return not editor.toPlainText().strip() and not self.has_images(editor)  # Check for text and images

    def has_images(self, editor):
        """
        Check if the editor contains any images.

        Args:
            editor (QTextEdit): The editor to check.

        Returns:
            bool: True if the editor contains images, False otherwise.

        - Iterates through the content of the editor using the cursor.
        - Checks if any character format in the document is an image format.
        """
        if editor is None:
            return False  # No editor implies no images
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)  # Start from the beginning
        while not cursor.atEnd():
            if cursor.charFormat().isImageFormat():  # Check if the format is an image
                return True
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)  # Move to the next character
        return False  # No images found

    def on_capture_area_set(self, snip_rect):
        """
        Set the capture area and update the capture_area_set flag.

        Args:
            snip_rect (QRect): The rectangle defining the selected capture area.

        - Updates the `capture_area` attribute with the selected area.
        - Sets the `capture_area_set` flag to True.
        - If a capture is in progress, calls the `capture` method and resets the progress flag.
        """
        self.capture_area = snip_rect  # Store the selected capture area
        self.capture_area_set = True  # Mark the capture area as set
        logger.info(f"Capture area set to: {self.capture_area}")

        # Trigger capture if it was waiting for the area to be set
        if self.capture_in_progress:
            self.capture()
            self.capture_in_progress = False  # Reset the progress flag

class ClickableTextEdit(QTextEdit):
    def __init__(self, parent=None):
        """
        Initialize the ClickableTextEdit instance.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.

        - Initializes the `full_image_map` to store mappings for full-size images.
        """
        super().__init__(parent)
        self.full_image_map = {}  # To store full images

    """---------- List Methods ----------"""     
    
    def change_bullet_list_indentation(self, increase_indent=True):
        """
        Adjust the bullet indentation and style for the current block and subsequent blocks only.

        - Tab (increase_indent=True): Increase indentation and cycle forward through bullet styles.
        - Backspace (increase_indent=False): Decrease indentation and cycle backward through bullet styles.
        - Removes the bullet when reducing indentation below the first level.
        """
        cursor = self.textCursor()
        cursor.beginEditBlock()

        block = cursor.block()
        current_list = block.textList()

        if current_list:
            # Get current list format and indentation level before removing the block
            list_format = current_list.format()
            current_indent = list_format.indent()
            logger.debug(f"Current indent level: {current_indent}")

            # Remove the block from the current list
            current_list.remove(block)

            # After removing the block, current_list may be invalid
            new_indent = current_indent + (1 if increase_indent else -1)
            logger.debug(f"New indent level: {new_indent}")

            if new_indent < 1:
                # Remove bullet entirely
                block_format = block.blockFormat()
                block_format.setIndent(0)
                block_format.setLeftMargin(0)
                cursor.setBlockFormat(block_format)
                logger.info("Removed bullet as indentation is below level 1.")
            else:
                # Set up new list format with updated indent
                new_list_format = QTextListFormat()
                bullet_styles = [
                    QTextListFormat.Style.ListDisc,    # Level 1: Disc
                    QTextListFormat.Style.ListCircle,  # Level 2: Circle
                    QTextListFormat.Style.ListSquare,  # Level 3: Square
                ]
                new_style = bullet_styles[(new_indent - 1) % len(bullet_styles)]
                new_list_format.setStyle(new_style)
                new_list_format.setIndent(new_indent)

                # Apply consistent left margin based on indentation level
                indent_increment = 20  # Adjust as needed for your desired indentation width
                block_format = block.blockFormat()
                block_format.setIndent(0)  # Reset block indent to 0 to avoid compounding
                block_format.setLeftMargin(indent_increment * (new_indent - 1))
                cursor.setBlockFormat(block_format)

                # Create a new list starting from the current block
                cursor.setPosition(block.position())
                cursor.createList(new_list_format)

                logger.info(f"Bullet updated to style {new_style} at indent level {new_indent}.")
        else:
            if increase_indent:
                # Start a new list since there isn't one
                new_indent = 1
                new_list_format = QTextListFormat()
                new_list_format.setStyle(QTextListFormat.Style.ListDisc)
                new_list_format.setIndent(new_indent)

                # Apply left margin
                block_format = block.blockFormat()
                block_format.setIndent(0)  # Reset block indent to 0
                block_format.setLeftMargin(0)
                cursor.setBlockFormat(block_format)

                # Create a new list starting from the current block
                cursor.setPosition(block.position())
                cursor.createList(new_list_format)
                logger.info("Created new bullet list.")
            else:
                # Cannot decrease indentation if there is no list
                logger.warning("Cannot decrease indentation, no bullet list found.")

        cursor.endEditBlock()

    def change_numbered_list_indentation(self, increase_indent=True):
        """
        Adjust the numbered list indentation and style for the current block and subsequent blocks only.
        """
        cursor = self.textCursor()
        cursor.beginEditBlock()

        block = cursor.block()
        current_list = block.textList()

        if current_list and current_list.format().style() in [
            QTextListFormat.Style.ListDecimal,
            QTextListFormat.Style.ListUpperAlpha,
            QTextListFormat.Style.ListLowerAlpha,
            QTextListFormat.Style.ListUpperRoman,
            QTextListFormat.Style.ListLowerRoman,
        ]:
            # Get current list format and indentation level before removing the block
            list_format = current_list.format()
            current_indent = list_format.indent()

            # Remove the block from the current list
            current_list.remove(block)

            # Calculate new indentation level
            new_indent = current_indent + (1 if increase_indent else -1)

            if new_indent < 1:
                # Remove numbering entirely
                block_format = block.blockFormat()
                block_format.setIndent(0)
                block_format.setLeftMargin(0)
                cursor.setBlockFormat(block_format)
                logger.info("Removed numbering as indentation is below level 1.")
            else:
                # Set up new list format with updated indent
                new_list_format = QTextListFormat()
                number_styles = [
                    QTextListFormat.Style.ListDecimal,     # Level 1: 1, 2, 3
                    QTextListFormat.Style.ListUpperAlpha,  # Level 2: A, B, C
                    QTextListFormat.Style.ListLowerAlpha,  # Level 3: a, b, c
                    QTextListFormat.Style.ListUpperRoman,  # Level 4: I, II, III
                    QTextListFormat.Style.ListLowerRoman,  # Level 5: i, ii, iii
                ]
                new_style = number_styles[(new_indent - 1) % len(number_styles)]
                new_list_format.setStyle(new_style)
                new_list_format.setIndent(new_indent)

                # Apply consistent left margin based on indentation level
                indent_increment = 20  # Adjust as needed
                block_format = block.blockFormat()
                block_format.setIndent(0)  # Reset block indent to avoid compounding
                block_format.setLeftMargin(indent_increment * (new_indent - 1))
                cursor.setBlockFormat(block_format)

                # Create a new list starting from the current block
                cursor.setPosition(block.position())
                cursor.createList(new_list_format)

                logger.info(f"Numbering updated to style {new_style} at indent level {new_indent}.")
        else:
            if increase_indent:
                # Start a new numbered list
                new_indent = 1
                new_list_format = QTextListFormat()
                new_list_format.setStyle(QTextListFormat.Style.ListDecimal)
                new_list_format.setIndent(new_indent)

                # Apply left margin
                block_format = block.blockFormat()
                block_format.setIndent(0)
                block_format.setLeftMargin(0)
                cursor.setBlockFormat(block_format)

                # Create a new list starting from the current block
                cursor.setPosition(block.position())
                cursor.createList(new_list_format)
                logger.info("Created new numbered list.")
            else:
                # Cannot decrease indentation if there is no list
                logger.warning("Cannot decrease indentation, no numbered list found.")

        cursor.endEditBlock()
    
    """------------------------ Mouse and Event Handling ------------------------"""

    def keyPressEvent(self, event):
        """
        Handle Tab and Backspace for adjusting bullet and numbered list indentation and style,
        when the cursor is in a list item.
        """
        cursor = self.textCursor()
        block = cursor.block()
        current_list = block.textList()

        if event.key() == Qt.Key.Key_Tab:
            if current_list:
                list_style = current_list.format().style()
                if list_style in [
                    QTextListFormat.Style.ListDisc,
                    QTextListFormat.Style.ListCircle,
                    QTextListFormat.Style.ListSquare,
                ]:
                    logger.info("Tab detected in bullet list item. Increasing indentation.")
                    self.change_bullet_list_indentation(increase_indent=True)
                elif list_style in [
                    QTextListFormat.Style.ListDecimal,
                    QTextListFormat.Style.ListLowerAlpha,
                    QTextListFormat.Style.ListUpperAlpha,
                    QTextListFormat.Style.ListLowerRoman,
                    QTextListFormat.Style.ListUpperRoman,
                ]:
                    logger.info("Tab detected in numbered list item. Increasing indentation.")
                    self.change_numbered_list_indentation(increase_indent=True)
                else:
                    super().keyPressEvent(event)
            else:
                super().keyPressEvent(event)  # Normal Tab behavior
        elif event.key() == Qt.Key.Key_Backspace:
            if current_list and self.is_cursor_at_list_start():
                list_style = current_list.format().style()
                if list_style in [
                    QTextListFormat.Style.ListDisc,
                    QTextListFormat.Style.ListCircle,
                    QTextListFormat.Style.ListSquare,
                ]:
                    logger.info("Backspace at start of bullet list item. Decreasing indentation.")
                    self.change_bullet_list_indentation(increase_indent=False)
                elif list_style in [
                    QTextListFormat.Style.ListDecimal,
                    QTextListFormat.Style.ListLowerAlpha,
                    QTextListFormat.Style.ListUpperAlpha,
                    QTextListFormat.Style.ListLowerRoman,
                    QTextListFormat.Style.ListUpperRoman,
                ]:
                    logger.info("Backspace at start of numbered list item. Decreasing indentation.")
                    self.change_numbered_list_indentation(increase_indent=False)
                else:
                    super().keyPressEvent(event)
            else:
                super().keyPressEvent(event)  # Normal Backspace behavior
        else:
            super().keyPressEvent(event)  # Default behavior for other keys

    def mousePressEvent(self, event):
        """
        Handle mouse press events for interacting with images or clearing formatting.

        Args:
            event (QMouseEvent): The mouse press event.

        - Detects if the click is on an anchor (image link) and displays the full image.
        - Clears formatting if the click is adjacent to a zero-width space.
        - Otherwise, processes the event as a normal mouse press.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            click_pos = event.position().toPoint()
            anchor = self.anchorAt(click_pos)  # Check if the click is on an anchor

            if anchor:
                image_id = anchor
                if image_id in self.full_image_map:  # If the anchor corresponds to an image
                    self.show_full_image(self.full_image_map[image_id])  # Display the image
                    return  # Consume the event
            else:
                # Check for adjacent zero-width space and reset formatting
                cursor = self.cursorForPosition(click_pos)
                cursor.select(QTextCursor.SelectionType.WordUnderCursor)

                if cursor.selectedText() == '\u200b':  # Detect zero-width space
                    neutral_format = QTextCharFormat()
                    cursor.setCharFormat(neutral_format)  # Reset formatting
                    self.setTextCursor(cursor)

        super().mousePressEvent(event)  # Pass the event to the parent class
        
    """------------------------ Image and Interaction Support ------------------------"""        
    def show_full_image(self, base64_image_data):
        """
        Display the full-size image in a modal dialog.

        Args:
            base64_image_data (str): Base64-encoded image data.

        - Decodes the base64 image and loads it into a QPixmap.
        - Displays the full-size image in a QLabel within a modal QDialog.
        """
        # Decode the base64 image data
        image_data = base64.b64decode(base64_image_data)
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(image_data))  # Load image data into QPixmap

        # Create a QLabel to display the image
        full_image_label = QLabel()
        full_image_label.setPixmap(pixmap)
        full_image_label.setWindowTitle("Full-Size Image")
        full_image_label.setScaledContents(True)  # Scale contents to fit the QLabel
        full_image_label.setFixedSize(pixmap.size())  # Match the label size to the image size

        # Display the image in a modal QDialog
        full_image_dialog = QDialog(self)
        layout = QVBoxLayout()
        layout.addWidget(full_image_label)
        full_image_dialog.setLayout(layout)
        full_image_dialog.exec()  # Open the dialog modally 
  
    """---------- Clickable Text Helper Methods ----------""" 
    
    def is_cursor_at_list_start(self):
        """
        Check if the cursor is at the start of the list item text.

        Returns:
            bool: True if the cursor is at the start of the list item text.
        """
        cursor = self.textCursor()
        block = cursor.block()
        cursor_position_in_block = cursor.position() - block.position()
        return cursor_position_in_block == 0

class FileMetadataManager:
    """
    Handles file metadata management, including loading, saving, updating, and removing file paths.

    - Manages metadata stored in a JSON file.
    - Provides methods to update, save, and delete metadata entries.
    """
    
    def __init__(self, metadata_file=METADATA_FILE):
        """
        Initialize the FileMetadataManager.

        Args:
            metadata_file (str): The path to the metadata file. Defaults to METADATA_FILE.

        - Loads existing metadata from the specified file or initializes an empty dictionary.
        """
        self.metadata_file = metadata_file
        self.metadata = self.load_metadata()  # Load metadata from file

    def load_metadata(self):
        """
        Load file metadata from a JSON file.

        Returns:
            dict: The loaded metadata, or an empty dictionary if the file doesn't exist.

        - Reads and parses the JSON metadata file.
        - Returns an empty dictionary if the file is missing.
        """
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r') as f:
                return json.load(f)  # Load JSON data
        return {}  # Return empty if file is missing

    def save_metadata(self):
        """
        Save the metadata dictionary to a JSON file.

        - Writes the current metadata dictionary to the specified JSON file.
        - Overwrites the file if it already exists.
        """
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=4)  # Save with indentation

    def update_file_metadata(self, file_name, user_path, persistent_path):
        """
        Update or add metadata for a file.

        Args:
            file_name (str): The name of the file.
            user_path (str): The user-selected path for the file.
            persistent_path (str): The app's persistent storage path for the file.

        - Adds or updates metadata for the file, including paths and timestamps.
        - Automatically sets a "created_at" timestamp if not already present.
        - Saves the updated metadata to the JSON file.
        """
        self.metadata[file_name] = {
            "user_path": user_path,  # User-selected path
            "persistent_path": persistent_path,  # Persistent app path
            "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Current timestamp
            "created_at": self.metadata.get(file_name, {}).get(
                "created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Preserve or set creation timestamp
            ),
        }
        self.save_metadata()  # Save changes

    def remove_metadata_entry(self, file_name):
        """
        Remove metadata for a file.

        Args:
            file_name (str): The name of the file to remove.

        - Deletes the metadata entry for the specified file if it exists.
        - Saves the updated metadata to the JSON file.
        """
        if file_name in self.metadata:
            del self.metadata[file_name]  # Remove the entry
            self.save_metadata()  # Save changes

class SavedFilesPanel(QWidget):
    """A panel to display saved files on the left side of the main window, with toggle and collapse functionality."""

    def __init__(self, main_window):
        super(SavedFilesPanel, self).__init__(main_window)
        self.files = []     
        self.main_window = main_window
        self.setWindowTitle("Saved Files")
        self.setFixedWidth(200)

        # Initialize layout and widgets
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Header layout for collapse and toggle button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 5)

        # Collapse button for hiding the panel
        self.collapse_button = QPushButton("◀", self)
        font = self.collapse_button.font()
        font.setPointSize(16)  
        self.collapse_button.setFont(font) 
        self.collapse_button.setFixedSize(20, 20)

        self.collapse_button.clicked.connect(self.collapse_panel)
        header_layout.addWidget(self.collapse_button, alignment=Qt.AlignmentFlag.AlignLeft)

        # Toggle button for showing/hiding the panel content
        self.toggle_button = QPushButton(self)
        self.toggle_button.setIcon(QIcon.fromTheme("window-close"))  # Uses a standard "X" close icon
        self.toggle_button.setFixedSize(8, 8)
        self.toggle_button.clicked.connect(self.toggle_panel)
        header_layout.addWidget(self.toggle_button, alignment=Qt.AlignmentFlag.AlignRight)

        # Add the header layout to the main layout
        self.layout.addLayout(header_layout)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search files...")
        self.search_bar.textChanged.connect(self.refresh_files_list)
        self.layout.addWidget(self.search_bar)

        # Horizontal layout for sort options and order toggle
        sort_layout = QHBoxLayout()

        # Sort criteria combo box
        self.sort_by_combo = QComboBox()
        self.sort_by_combo.setFixedWidth(150) 
        self.sort_by_combo.addItems(["Name", "Modification Date", "Creation Date"])
        self.sort_by_combo.currentIndexChanged.connect(self.refresh_files_list)
        sort_layout.addWidget(self.sort_by_combo)

        # Sorting direction button (arrow up/down)
        self.sort_order_button = QPushButton("▲")
        self.sort_order_button.setFixedSize(25, 25)
        self.sort_order_button.setCheckable(True)
        self.sort_order_button.clicked.connect(self.toggle_sort_order)
        sort_layout.addWidget(self.sort_order_button)
        self.sort_ascending = True  # Default sort order

        # Add the sort layout to the main layout
        self.layout.addLayout(sort_layout)

        # Saved files list
        self.saved_files_list = QListWidget(self)
        self.layout.addWidget(self.saved_files_list)

        # Context menu for file actions
        self.saved_files_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.saved_files_list.customContextMenuRequested.connect(self.show_context_menu)

        # Manual refresh button
        self.refresh_button = QPushButton("Refresh 🔄")
        self.refresh_button.clicked.connect(self.refresh_files_list)
        self.layout.addWidget(self.refresh_button)

        # Initial load of saved files
        self.refresh_files_list()

    """---------- File Management Methods ----------""" 
    def add_item(self, filename, content):
        """Add a file to the internal saved files list."""
        self.files.append(filename)

    def add_saved_file(self, file_name):
        """Add a new file to the saved files folder and refresh the list."""
        if not os.path.exists(os.path.join(PERSISTENT_FOLDER, file_name)):
            self.saved_files_list.addItem(file_name)
            self.refresh_files_list()

    def contains(self, filename):
        """Check if a file is already in the saved files panel."""
        return filename in self.files

    def get_item_content(self, filename):
        """
        Retrieve the content of a saved file by its filename.

        Args:
            filename (str): The name of the file to retrieve content for.

        Returns:
            str: The content of the file as a string, or None if the file does not exist.

        Raises:
            FileNotFoundError: If the specified file is not found in the persistent folder.
        """
        file_path = os.path.join(PERSISTENT_FOLDER, filename)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            logger.warning(f"File '{filename}' not found in persistent folder.")
            raise FileNotFoundError(f"File '{filename}' does not exist.")

    def refresh_files_list(self):
        """Refresh the saved files list based on search, sort options, and sorting preferences."""
        self.saved_files_list.clear()  # Clear the current list

        # Retrieve and filter files
        search_text = self.search_bar.text().lower()
        all_files = [
            f for f in os.listdir(PERSISTENT_FOLDER)
            if os.path.isfile(os.path.join(PERSISTENT_FOLDER, f)) and f != "file_metadata.json"
        ]
        
        # Filter files by search text
        filtered_files = [f for f in all_files if search_text in f.lower()]

        # Sort files based on selected criteria
        sort_criteria = self.sort_by_combo.currentText()
        reverse_order = not self.sort_ascending

        if sort_criteria == "Name":
            sorted_files = sorted(filtered_files, reverse=reverse_order)
        else:
            sorted_files = sorted(
                filtered_files,
                key=lambda f: os.path.getmtime(os.path.join(PERSISTENT_FOLDER, f)) if sort_criteria == "Modification Date"
                else os.path.getctime(os.path.join(PERSISTENT_FOLDER, f)),
                reverse=reverse_order
            )

        # Add sorted and filtered files to the list
        self.saved_files_list.addItems(sorted_files)

    """---------- UI Interation Methods ----------""" 
    def toggle_panel(self):
        """Toggle visibility of the saved files panel content."""
        is_visible = self.isVisible()
        self.setVisible(not is_visible)
        self.main_window.toggle_panel_action.setChecked(not is_visible)

    def collapse_panel(self):
        """Collapse the splitter panel containing this widget."""
        splitter = self.main_window.splitter  # Access the main splitter
        splitter.setSizes([0, 1])  # Collapse the left panel (self)

    def toggle_sort_order(self):
        """Toggle the sort order between ascending and descending with an arrow button."""
        self.sort_ascending = not self.sort_ascending
        self.sort_order_button.setText("▲" if self.sort_ascending else "▼")
        self.refresh_files_list()  # Refresh the list to apply the new sort order

    """---------- Context Menu and File Actions ----------""" 
    def show_context_menu(self, pos):
        """Show context menu for file actions in the saved files list with a gray color scheme."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;  /* Dark gray background */
                color: #f0f0f0;             /* Light gray text */
                border: 1px solid #5a5a5a;  /* Border color */
            }
            QMenu::item {
                background-color: transparent;
                padding: 4px 24px;
            }
            QMenu::item:selected {
                background-color: #3a3a3a;  /* Slightly lighter gray on selection */
                color: #ffffff;             /* White text on selection */
            }
            QMenu::separator {
                height: 1px;
                background: #5a5a5a;        /* Gray separator line */
                margin-left: 10px;
                margin-right: 10px;
            }
        """)

        open_action = QAction("Open", self)
        open_action.triggered.connect(lambda: self.open_selected_file(self.saved_files_list.currentItem()))
        menu.addAction(open_action)

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_selected_file())
        menu.addAction(delete_action)

        properties_action = QAction("Properties", self)
        properties_action.triggered.connect(lambda: self.show_file_properties(self.saved_files_list.currentItem()))
        menu.addAction(properties_action)

        menu.exec(self.saved_files_list.mapToGlobal(pos))

    def open_selected_file(self, item):
        """Open the selected file in a new tab."""
        if item:
            file_name = item.text()
            file_path = os.path.join(PERSISTENT_FOLDER, file_name)
            if os.path.exists(file_path):
                # Check if the file is already open in a tab
                for index in range(self.main_window.tab_widget.count()):
                    tab_path = self.main_window.paths.get(index)
                    if tab_path == file_path:
                        self.main_window.tab_widget.setCurrentIndex(index)
                        return
                # Open the file in a new tab if not already open
                self.main_window.open_file_in_new_tab(file_path)
            else:
                QMessageBox.warning(self, "File Not Found", f"The file '{file_name}' could not be found.")
                self.refresh_files_list()  # Refresh the list if the file is missing

    def delete_selected_file(self):
        """Delete the selected file and close the corresponding tab if it is open."""
        item = self.saved_files_list.currentItem()
        if item:
            file_name = item.text()
            file_path = os.path.join(PERSISTENT_FOLDER, file_name)

            # Confirm deletion
            confirm = QMessageBox.question(
                self, 
                "Delete File", 
                f"Are you sure you want to delete '{file_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if confirm == QMessageBox.StandardButton.Yes:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.saved_files_list.takeItem(self.saved_files_list.row(item))
                    self.main_window.file_metadata_manager.remove_metadata_entry(file_name)

                    # Close the corresponding tab if open
                    for index in range(self.main_window.tab_widget.count()):
                        tab_path = self.main_window.paths.get(index)
                        if tab_path == file_path:
                            self.main_window.tab_widget.removeTab(index)
                            del self.main_window.paths[index]
                            break
                    self.refresh_files_list()
                    logging.info(f"File '{file_name}' deleted from saved files and any open tab closed.")

    def show_file_properties(self, item):
        """Show the properties of the selected file, including location, created/modified times, and size."""
        if item:
            file_name = item.text()
            file_path = os.path.join(PERSISTENT_FOLDER, file_name)

            if os.path.exists(file_path):
                file_info = os.stat(file_path)
                created_time = datetime.fromtimestamp(file_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                modified_time = datetime.fromtimestamp(file_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                file_size = file_info.st_size

                # Display file properties in a message box
                QMessageBox.information(
                    self, 
                    "File Properties", 
                    f"File: {file_name}\n\n"
                    f"Location: {file_path}\n"
                    f"Created: {created_time}\n"
                    f"Modified: {modified_time}\n"
                    f"Size: {file_size} bytes"
                )
            else:
                QMessageBox.warning(self, "File Not Found", f"The file '{file_name}' could not be found.")
                self.refresh_files_list()

class ChecklistManager(QDialog):
    """Manage multiple checklists."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Checklist Manager")
        self.setGeometry(300, 300, 500, 400)

        # Layout setup
        self.layout = QVBoxLayout(self)
        self.checklist_dir = CHECKLISTS_FOLDER
        os.makedirs(self.checklist_dir, exist_ok=True)

        # List widget to display checklists
        self.checklist_widget = QListWidget(self)
        self.load_checklists()
        self.layout.addWidget(self.checklist_widget)

        # Buttons for managing checklists
        self.new_button = QPushButton("New Checklist", self)
        self.new_button.clicked.connect(self.create_new_checklist)
        self.layout.addWidget(self.new_button)

        self.edit_button = QPushButton("Edit Selected Checklist", self)
        self.edit_button.clicked.connect(self.edit_selected_checklist)
        self.layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete Selected Checklist", self)
        self.delete_button.clicked.connect(self.delete_selected_checklist)
        self.layout.addWidget(self.delete_button)

    def load_checklists(self):
        """Load all available checklists into the list widget."""
        self.checklist_widget.clear()
        for filename in os.listdir(self.checklist_dir):
            if filename.endswith(".json"):
                self.checklist_widget.addItem(filename[:-5])  # Remove the ".json" extension

    def create_new_checklist(self):
        """Create a new checklist by prompting the user for a name."""
        name, ok = QInputDialog.getText(self, "New Checklist", "Enter checklist name:")
        if ok and name:
            path = os.path.join(self.checklist_dir, f"{name}.json")
            if os.path.exists(path):
                QMessageBox.warning(self, "Error", "A checklist with this name already exists.")
            else:
                # Save an empty checklist structure
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"checklists": []}, f, indent=4)
                self.load_checklists()

    def edit_selected_checklist(self):
        """Edit the currently selected checklist."""
        selected_item = self.checklist_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Error", "No checklist selected.")
            return

        checklist_name = selected_item.text()
        editor = UnifiedChecklistEditor(checklist_name, self)
        editor.exec()
        self.load_checklists()

    def delete_selected_checklist(self):
        """Delete the currently selected checklist after user confirmation."""
        selected_item = self.checklist_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Error", "No checklist selected.")
            return

        checklist_name = selected_item.text()
        path = os.path.join(self.checklist_dir, f"{checklist_name}.json")
        confirm = QMessageBox.question(
            self,
            "Delete Checklist",
            f"Are you sure you want to delete '{checklist_name}'?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            os.remove(path)
            self.load_checklists()

class UnifiedChecklistEditor(QDialog):
    """Unified editor for managing checklists with structured sections and items."""
    
    def __init__(self, checklist_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Checklist: {checklist_name}")
        self.setGeometry(400, 400, 800, 600)

        self.checklist_name = checklist_name
        self.checklist_path = os.path.join(CHECKLISTS_FOLDER, f"{checklist_name}.json")
        
        # Load existing checklist data
        self.data = self.load_checklist_data()

        # Main layout
        self.layout = QVBoxLayout(self)

        # Checklist display area with drag-and-drop enabled
        self.editor_area = QListWidget(self)
        self.editor_area.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.editor_area.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor_area.setDragEnabled(True)
        self.editor_area.setAcceptDrops(True)
        self.editor_area.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.editor_area.setDropIndicatorShown(True)
        self.editor_area.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.editor_area.customContextMenuRequested.connect(self.show_context_menu)
        self.populate_editor_area()
        self.layout.addWidget(self.editor_area)

        # Toolbar for adding/removing items
        self.toolbar_layout = QHBoxLayout()

        self.add_title_button = self.create_toolbar_button("🅰️", "Add Main Title", lambda: self.add_item("MainTitle"))
        self.toolbar_layout.addWidget(self.add_title_button)

        self.add_subtitle_button = self.create_toolbar_button("🔠", "Add Sub Title", lambda: self.add_item("SubTitle"))
        self.toolbar_layout.addWidget(self.add_subtitle_button)

        self.add_description_button = self.create_toolbar_button("✍️", "Add Description", lambda: self.add_item("Description"))
        self.toolbar_layout.addWidget(self.add_description_button)

        self.add_task_button = self.create_toolbar_button("📝", "Add Task", lambda: self.add_item("Task"))
        self.toolbar_layout.addWidget(self.add_task_button)

        self.add_checklist_item_button = self.create_toolbar_button("✅", "Add Checklist Item", lambda: self.add_item("ChecklistItem"))
        self.toolbar_layout.addWidget(self.add_checklist_item_button)

        self.add_note_button = self.create_toolbar_button("🗒️", "Add Checklist Note", lambda: self.add_item("ChecklistNote"))
        self.toolbar_layout.addWidget(self.add_note_button)

        self.remove_button = self.create_toolbar_button("❌", "Remove Selected", self.remove_selected)
        self.toolbar_layout.addWidget(self.remove_button)

        self.layout.addLayout(self.toolbar_layout)

        # Save button at the bottom
        self.save_button = QPushButton("💾 Save Checklist", self)
        self.save_button.clicked.connect(self.save_checklist)
        self.layout.addWidget(self.save_button)

        # Connect drag-and-drop signal
        self.editor_area.model().rowsMoved.connect(self.update_data_order)

    def create_toolbar_button(self, icon_text, tooltip, callback):
        """Create a compact button for the toolbar."""
        button = QPushButton(icon_text, self)
        button.setToolTip(tooltip)
        button.setFixedSize(40, 40)
        button.clicked.connect(callback)
        button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: #f0f0f0;
                font-size: 16px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-radius: 5px;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        return button

    def load_checklist_data(self):
        """Load checklist data from the file."""
        if os.path.exists(self.checklist_path):
            with open(self.checklist_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"checklists": []}

    def populate_editor_area(self):
        """Populate the editor area with formatted checklist items."""
        self.editor_area.clear()
        for item in self.data.get("checklists", []):
            self.add_item_to_display(item)

    def add_item(self, item_type):
        """Add a new item of the specified type."""
        text, ok = QInputDialog.getText(self, f"Add {item_type}", f"Enter the text for {item_type}:")
        if ok and text:
            new_item = {"type": item_type, "text": text}
            self.data["checklists"].append(new_item)
            self.add_item_to_display(new_item)

    def add_item_to_display(self, item):
        """Add an item to the display with formatting."""
        formatted_item = QListWidgetItem(item["text"])
        font = QFont(DEFAULT_FONT_FAMILY)

        # Set formatting based on type
        if item["type"] == "MainTitle":
            font.setPointSize(18)
            font.setBold(True)
        elif item["type"] == "SubTitle":
            font.setPointSize(16)
            font.setBold(True)
        elif item["type"] == "Description":
            font.setPointSize(12)
            formatted_item.setText(f"    {item['text']}")
        elif item["type"] == "Task":
            font.setPointSize(14)
            formatted_item.setText(f"    • {item['text']}")
        elif item["type"] == "ChecklistItem":
            font.setPointSize(12)
            formatted_item.setText(f"        ☐ {item['text']}")
        elif item["type"] == "ChecklistNote":
            font.setPointSize(12)
            formatted_item.setText(f"Note: {item['text']}")
            formatted_item.setForeground(Qt.GlobalColor.gray)

        formatted_item.setFont(font)
        self.editor_area.addItem(formatted_item)

    def remove_selected(self):
        """Remove the selected item."""
        selected_index = self.editor_area.currentRow()
        if selected_index >= 0:
            self.data["checklists"].pop(selected_index)
            self.editor_area.takeItem(selected_index)

    def show_context_menu(self, pos):
        """Show context menu to change the type of the selected item."""
        menu = QMenu(self)

        for item_type in ["MainTitle", "SubTitle", "Description", "Task", "ChecklistItem"]:
            action = QAction(f"Set as {item_type}", self)
            action.triggered.connect(lambda _, t=item_type: self.change_item_type(t))
            menu.addAction(action)

        menu.exec(self.editor_area.mapToGlobal(pos))

    def change_item_type(self, item_type):
        """Change the type of the selected item."""
        selected_index = self.editor_area.currentRow()
        if selected_index < 0:
            QMessageBox.warning(self, "Error", "No item selected.")
            return

        selected_item = self.data["checklists"][selected_index]
        text = selected_item["text"]
        selected_item["type"] = item_type
        self.editor_area.takeItem(selected_index)
        self.data["checklists"][selected_index] = {"type": item_type, "text": text}
        self.add_item_to_display({"type": item_type, "text": text})

    def update_data_order(self, source_parent, source_start, source_end, dest_parent, dest_row):
        """Update the underlying data order when items are reordered."""
        moved_items = self.data["checklists"][source_start:source_end + 1]
        del self.data["checklists"][source_start:source_end + 1]
        for index, item in enumerate(moved_items):
            self.data["checklists"].insert(dest_row + index, item)

    def save_checklist(self):
        """Save the checklist data to a properly structured JSON file."""
        structured_data = {"checklists": []}
        current_section = None

        for i in range(self.editor_area.count()):
            item_widget = self.editor_area.item(i)

            # Retrieve item data
            item_data = item_widget.data(Qt.ItemDataRole.UserRole)
            if not item_data:
                continue

            item_type = item_data.get("type")
            item_text = item_data.get("text")

            if item_type == "MainTitle":
                # Create a new section for a MainTitle
                current_section = {"MainTitle": item_text, "items": []}
                structured_data["checklists"].append(current_section)

            elif item_type == "SubTitle":
                # Add SubTitle to the current section
                if current_section is not None:
                    current_section.setdefault("items", []).append({"SubTitle": item_text})

            elif item_type == "Description":
                # Add Description to the current section
                if current_section is not None:
                    current_section.setdefault("items", []).append({"Description": item_text})

            elif item_type == "Task":
                # Add Task to the current section
                if current_section is not None:
                    current_section.setdefault("items", []).append({"Task": item_text})

            elif item_type == "Checklist":
                # Add Checklist to the current section
                if current_section is not None:
                    checklist_items = item_data.get("checklist", [])
                    current_section.setdefault("items", []).append({"Checklist": checklist_items})

            elif item_type == "Note":
                # Add Note to the current section
                if current_section is not None:
                    current_section.setdefault("items", []).append({"Note": item_text})

            elif item_type == "ChecklistNote":
                # Add ChecklistNote to the current section
                if current_section is not None:
                    current_section.setdefault("items", []).append({"ChecklistNote": item_text})

        # Write the structured data to the JSON file
        try:
            with open(self.checklist_path, "w", encoding="utf-8") as f:
                json.dump(structured_data, f, indent=4)
            QMessageBox.information(self, "Success", "Checklist saved successfully.")
            logger.info(f"Checklist saved successfully: {self.checklist_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save checklist.\n\n{str(e)}")
            logger.error(f"Failed to save checklist: {e}")

class CustomSplitterHandle(QSplitterHandle):
    """Custom splitter handle with a visual grip for user feedback."""
    
    def __init__(self, orientation, parent=None):
        """
        Initialize the custom splitter handle.

        Args:
            orientation (Qt.Orientation): The orientation of the splitter (vertical or horizontal).
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(orientation, parent)
        self.init_ui()

    def init_ui(self):
        """Set up the user interface for the custom splitter handle."""
        # Use a vertical layout for vertical splitters, horizontal layout otherwise
        layout = QVBoxLayout() if self.orientation() == Qt.Orientation.Vertical else QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)  # Add padding around the handle

        # Create a label to act as the visual grip
        grip_label = QLabel("|||", self)  # "|||" as a visual cue for grip
        grip_label.setFixedSize(QSize(40, 40))  # Set a fixed size for the grip
        grip_label.setStyleSheet(
            "background-color: #888; font-size: 14px; color: white;"  # Style for the grip
        )
        
        # Center the grip label in the handle
        layout.addWidget(grip_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

class CustomSplitter(QSplitter):
    """Custom splitter with enhanced handles for better user interaction."""
    
    def __init__(self, orientation, parent=None):
        """
        Initialize the custom splitter.

        Args:
            orientation (Qt.Orientation): The orientation of the splitter (vertical or horizontal).
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(orientation, parent)

    def createHandle(self):
        """
        Override the handle creation method to use the custom splitter handle.

        Returns:
            CustomSplitterHandle: An instance of the custom handle.
        """
        return CustomSplitterHandle(self.orientation(), self)

class SnippingOverlay(QWidget):
    """A semi-transparent overlay for selecting a region of the screen."""
    
    # Signal emitted when the snip is completed, providing the selected rectangle
    snipCompleteGlobal = pyqtSignal(QRect)

    def __init__(self, screen_rect, close_all_callback):
        """
        Initialize the snipping overlay.

        Args:
            screen_rect (QRect): The rectangle representing the screen area covered by the overlay.
            close_all_callback (callable): A function to call when the selection is completed.
        """
        super().__init__()
        # Set window flags to make the overlay stay on top and frameless
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # Enable transparency
        self.setGeometry(screen_rect)  # Set the overlay geometry to cover the screen
        self.setCursor(Qt.CursorShape.CrossCursor)  # Use a crosshair cursor for selection
        self.begin = QPoint()  # Starting point of the selection rectangle
        self.end = QPoint()  # Ending point of the selection rectangle
        self.close_all_callback = close_all_callback  # Callback to handle snipping completion

    def updateMask(self):
        """
        Update the mask to make the selected area transparent while keeping the rest of the screen darkened.
        """
        # Create a bitmap mask with the entire area filled in black
        mask = QBitmap(self.size())
        mask.fill(Qt.GlobalColor.black)

        # Define the selection rectangle and clear its area in the mask
        selection_rect = QRect(self.begin, self.end).normalized()
        painter = QPainter(mask)
        painter.setBrush(Qt.GlobalColor.white)  # Clear the selection area by painting it white
        painter.setPen(Qt.PenStyle.NoPen)  # No border for the cleared area
        painter.drawRect(selection_rect)
        painter.end()

        # Apply the updated mask to the overlay
        self.setMask(mask)

    def paintEvent(self, event):
        """
        Paint the semi-transparent overlay and the red border for the selection rectangle.
        """
        qp = QPainter(self)
        screen_rect = self.rect()

        # Draw a semi-transparent dark overlay over the entire screen
        qp.setBrush(QColor(0, 0, 0, 100))  # Dark gray with 40% opacity
        qp.setPen(Qt.PenStyle.NoPen)  # No border for the overlay
        qp.drawRect(screen_rect)

        # Draw a red border around the selection rectangle
        selection_rect = QRect(self.begin, self.end).normalized()
        if not selection_rect.isNull():  # Only draw if a valid rectangle exists
            qp.setPen(QPen(Qt.GlobalColor.red, 3))  # Red border with a thickness of 3
            qp.drawRect(selection_rect)

    def mousePressEvent(self, event):
        """
        Handle the mouse press event to start the selection rectangle.

        Args:
            event (QMouseEvent): The mouse press event.
        """
        self.begin = event.pos()  # Record the starting point
        self.end = self.begin  # Initialize the end point
        self.updateMask()  # Update the mask for visual feedback
        self.update()  # Repaint the overlay

    def mouseMoveEvent(self, event):
        """
        Handle the mouse move event to dynamically update the selection rectangle.

        Args:
            event (QMouseEvent): The mouse move event.
        """
        self.end = event.pos()  # Update the end point as the mouse moves
        self.updateMask()  # Update the mask for visual feedback
        self.update()  # Repaint the overlay

    def mouseReleaseEvent(self, event):
        """
        Handle the mouse release event to finalize the selection rectangle.

        Args:
            event (QMouseEvent): The mouse release event.
        """
        self.end = event.pos()  # Finalize the end point
        self.updateMask()  # Update the mask for visual feedback
        self.update()  # Repaint the overlay

        # Calculate the global coordinates of the selection rectangle
        snip_rect = QRect(self.mapToGlobal(self.begin), self.mapToGlobal(self.end)).normalized()
        
        # Emit the signal with the selected rectangle and invoke the callback
        self.snipCompleteGlobal.emit(snip_rect)
        self.close_all_callback(snip_rect)

        # Close the overlay
        self.close()

class CustomDictionaryDialog(QDialog):
    """Dialog for editing the custom dictionary used by the spell checker."""

    def __init__(self, parent=None):
        """
        Initialize the dialog with UI components for managing the custom dictionary.

        Args:
            parent (QWidget, optional): The parent widget for this dialog.
        """
        super().__init__(parent)
        self.setWindowTitle("Edit Custom Dictionary")
        
        # Main layout for the dialog
        layout = QVBoxLayout(self)

        # Search bar for filtering words
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search for a word...")  # Placeholder text
        self.search_bar.textChanged.connect(self.filter_words)  # Connect text change signal to filter
        layout.addWidget(self.search_bar)

        # Word list display
        self.word_list = QListWidget(self)
        self.word_list.setSortingEnabled(True)  # Enable sorting of displayed words
        layout.addWidget(self.word_list)

        # Internal list to store all words for filtering
        self.words = []  
        self.load_words()  # Load words from the dictionary file

        # Buttons for dialog actions
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.save_changes)  # Save changes when OK is clicked
        button_box.rejected.connect(self.reject)  # Close without saving when Cancel is clicked
        layout.addWidget(button_box)

        # Add button for adding new words
        add_button = QPushButton("Add Word")
        add_button.clicked.connect(self.add_word)  # Connect button to adding words
        layout.addWidget(add_button)

        # Remove button for deleting selected words
        remove_button = QPushButton("Remove Selected Word")
        remove_button.clicked.connect(self.remove_selected_word)  # Connect button to removing words
        layout.addWidget(remove_button)

    def load_words(self):
        """Load words from the custom dictionary file and display them in the word list."""
        if os.path.exists(CUSTOM_DICT_PATH):
            with open(CUSTOM_DICT_PATH, 'r') as f:
                self.words = sorted(json.load(f))  # Sort the words alphabetically
            self.word_list.addItems(self.words)  # Populate the word list with loaded words

    def filter_words(self):
        """Filter the displayed word list based on input from the search bar."""
        search_text = self.search_bar.text().lower()  # Get the search text in lowercase
        self.word_list.clear()  # Clear the current display

        # Add matching words to the list
        for word in self.words:
            if search_text in word.lower():
                self.word_list.addItem(word)

    def save_changes(self):
        """Save the current list of words to the custom dictionary file."""
        # Retrieve all words currently displayed in the list
        current_words = [self.word_list.item(i).text() for i in range(self.word_list.count())]

        # Save the words in alphabetical order to the dictionary file
        with open(CUSTOM_DICT_PATH, 'w') as f:
            json.dump(sorted(current_words), f, indent=4)
        
        # Update the spell checker with the new dictionary
        spell.word_frequency.load_words(current_words)
        
        # Close the dialog
        self.accept()

    def add_word(self):
        """Add a new word to the dictionary and update the display."""
        # Prompt the user to enter a new word
        text, ok = QInputDialog.getText(self, "Add Word", "Enter word to add:")
        if ok and text:  # Add the word if the user confirmed
            self.words.append(text)
            self.words.sort()  # Keep the list sorted alphabetically
            self.filter_words()  # Update the display to include the new word

    def remove_selected_word(self):
        """Remove the selected word(s) from the dictionary and update the display."""
        # Iterate over all selected items and remove them
        for item in self.word_list.selectedItems():
            self.words.remove(item.text())  # Remove the word from the internal list
            self.word_list.takeItem(self.word_list.row(item))  # Remove the item from the display

"""---------- Main Program Execution ----------""" 

if __name__ == "__main__":
    import logging

    # Configure logging to capture errors and debug information
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("application.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ]
    )

    try:
        # Log application start
        logging.info("Starting application...")

        # Initialize the QApplication
        app = QApplication(sys.argv)

        # Path to the application icon in the images folder
        icon_path = os.path.join(os.path.dirname(__file__), "images", "cano.ico")

        # Set the application icon or log a warning if the icon is missing
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            logging.info(f"Application icon set from: {icon_path}")
        else:
            logging.warning("Icon file not found. Using default icon settings.")

        # Create and display the main application window
        window = MainWindow()
        window.show()
        logging.info("Main window initialized and displayed successfully.")

        # Execute the application event loop
        sys.exit(app.exec())

    except FileNotFoundError as fnf_error:
        # Handle specific file-related errors
        logging.critical(f"File not found: {fnf_error}", exc_info=True)
        QMessageBox.critical(
            None,
            "File Not Found",
            f"A critical file is missing:\n\n{fnf_error}\n\n"
            "Please ensure all required files are present and try again."
        )
        sys.exit(1)

    except Exception as e:
        # Handle any other unexpected errors
        logging.critical("An unexpected error occurred during application execution.", exc_info=True)
        QMessageBox.critical(
            None,
            "Critical Error",
            f"An unexpected error occurred. The application will now exit.\n\nError Details:\n{str(e)}"
        )
        sys.exit(1)
